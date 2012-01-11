# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import datetime
import logging
import threading
from gettext import gettext as _

from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.dispatch import call
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.util import Singleton


_LOG = logging.getLogger(__name__)

# tags -------------------------------------------------------------------------

SCHEDULED_TAG = 'scheduled'

# scheduler --------------------------------------------------------------------

class Scheduler(object):
    """
    Scheduler class
    Manager and dispatcher of scheduled call requests
    @ivar dispatch_interval: time, in seconds, between schedule checks
    @type dispatch_interval: int
    @ivar scheduled_call_collection: db collection of scheduled call requests
    @type scheduled_call_collection: pymongo.collection.Collection
    """

    __metaclass__ = Singleton

    def __init__(self, dispatch_interval=30):

        self.dispatch_interval = dispatch_interval
        self.scheduled_call_collection = ScheduledCall.get_collection()

        self.__exit = False
        self.__lock = threading.RLock()
        self.__condition = threading.Condition(self.__lock)
        self.__dispatcher = None

    # scheduled calls dispatch methods -----------------------------------------

    def __dispatch(self):
        """
        Dispatcher thread loop
        """
        self.__lock.acquire()
        while True:
            self.__condition.wait(timeout=self.dispatch_interval)
            if self.__exit:
                if self.__lock is not None:
                    self.__lock.release()
                return
            try:
                self._run_scheduled_calls()
            except Exception, e:
                _LOG.critical('Unhandled exception in scheduler dispatch: %s' % repr(e))
                _LOG.exception(e)

    def _run_scheduled_calls(self):
        """
        Find call requests that are currently scheduled to run
        """
        now = datetime.datetime.utcnow()
        query = {'next_run': {'$lte': now}}
        for scheduled_call in self.scheduled_call_collection.find(query):
            if not scheduled_call['enabled']:
            # update the next run information for disabled calls
                self.update_next_run(scheduled_call)
                continue
            serialized_call_request = scheduled_call['serialized_call_request']
            call_request = call.CallRequest.deserialize(serialized_call_request)
            self._run_via_task_queue(call_request)

    def _run_via_task_queue(self, call_request):
        """
        Run the call request directly in the task queue
        """
        from pulp.server import config
        from pulp.server.dispatch.task import Task
        from pulp.server.dispatch.taskqueue import TaskQueue
        concurrency_threshold = config.config.getint('tasking', 'concurrency_threshold')
        task_queue = TaskQueue(concurrency_threshold)
        task = Task(call_request)
        task_queue.enqueue(task)

    def _run_via_coordinator(self, call_request):
        """
        Run the call request through the coordinator
        """
        raise NotImplementedError()

    def start(self):
        """
        Start the scheduler
        """
        assert self.__dispatcher is None
        self.__dispatcher = threading.Thread(target=self.__dispatch)
        self.__dispatcher.setDaemon(True)
        self.__dispatcher.start()

    def stop(self):
        """
        Stop the scheduler
        """
        assert self.__dispatcher is not None
        self.__lock.acquire()
        self.__exit = True
        self.__condition.notify()
        self.__lock.release()
        self.__dispatcher.join()
        self.__dispatcher = None

    # scheduling methods -------------------------------------------------------

    def update_last_run(self, scheduled_call, call_report=None):
        """
        Update the metadata for a scheduled call that has been run
        @param scheduled_call: scheduled call to be updated
        @type  scheduled_call: dict
        @param call_report: call report from last run, if available
        @type  call_report: CallReport instance or None
        """
        schedule_id = scheduled_call['_id']
        update = {}
        # use scheduled time instead of current to prevent schedule drift
        delta = update.setdefault('$set', {})
        delta['last_run'] = scheduled_call['next_run']
        # if we finished in an error state, make sure we haven't crossed the threshold
        state = getattr(call_report, 'state', None)
        if state == dispatch_constants.CALL_ERROR_STATE:
            inc = update.setdefault('$inc', {})
            inc['consecutive_failures'] = 1
            failure_threshold = scheduled_call['failure_threshold']
            consecutive_failures = scheduled_call['consecutive_failures'] + 1
            if failure_threshold >= consecutive_failures: # valid for failure_threshold of None
                delta = update.setdefault('$set', {})
                delta['enabled'] = False
                msg = _('Scheduled task [%s] disabled after %d consecutive failures')
                _LOG.error(msg % (schedule_id, consecutive_failures))
        else:
            delta = update.setdefault('$set', {})
            delta['consecutive_failures'] = 0
        # decrement the remaining runs, if we're tracking that
        if scheduled_call['runs'] is not None:
            inc = update.setdefault('$inc', {})
            inc['runs'] = -1
        self.scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

    def update_next_run(self, scheduled_call):
        """
        Update the metadata for a scheduled call that will be run again
        @param scheduled_call: scheduled call to be updated
        @type  scheduled_call: dict
        """
        schedule_id = scheduled_call['_id']
        next_run = self.calculate_next_run(scheduled_call)
        if next_run is None:
            # remove the scheduled call if there are no more
            self.scheduled_call_collection.remove({'_id': schedule_id}, safe=True)
            return
        update = {'$set': {'next_run': next_run}}
        self.scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

    def calculate_next_run(self, scheduled_call):
        """
        Calculate the next run datetime of a scheduled call
        @param scheduled_call: scheduled call to schedule
        @type  scheduled_call: dict
        @return: datetime of scheduled call's next run or None if there is no next run
        @rtype:  datetime.datetime or None
        """
        if scheduled_call['runs'] == 0:
            return None

        now = datetime.datetime.utcnow()
        last_run = scheduled_call['last_run']
        if last_run is None:
            return scheduled_call['start_date']

        next_run = last_run
        interval = scheduled_call['interval']
        while next_run < now:
            next_run += interval
        return next_run

    def call_finished_callback(self, call_request, call_report):
        """
        Call back for task (call_request) results and rescheduling
        """
        index = call_request.tags.index(SCHEDULED_TAG)
        schedule_id = call_request.tags[index + 1]
        scheduled_call = self.scheduled_call_collection.find_one({'_id': schedule_id})
        self.update_last_run(scheduled_call, call_report)
        self.update_next_run(scheduled_call)

    # schedule control methods -------------------------------------------------

    def add(self, call_request, schedule, last_run=None):
        """
        Add a scheduled call request
        @param call_request: call request to schedule
        @type  call_request: pulp.server.dispatch.call.CallRequest
        @param schedule: iso8601 formatted interval schedule
        @type  schedule: str
        @param last_run: datetime of the last run of the call request or None if no last run
        @type  last_run: datetime.datetime or None
        @return: schedule id if successfully scheduled or None otherwise
        @rtype:  str or None
        """
        call_request.tags.append(SCHEDULED_TAG)
        call_request.add_execution_hook(dispatch_constants.CALL_DEQUEUE_EXECUTION_HOOK, self.call_finished_callback)
        scheduled_call = ScheduledCall(call_request, schedule, last_run)
        next_run = self.calculate_next_run(scheduled_call)
        if next_run is None:
            return None
        self.scheduled_call_collection.insert(scheduled_call, safe=True)
        return scheduled_call['_id']

    def remove(self, schedule_id):
        """
        Remove a scheduled call reqeust
        @param schedule_id: id of the schedule for the call request
        @type  schedule_id: str
        """
        self.scheduled_call_collection.remove({'_id': schedule_id}, safe=True)

    def enable(self, schedule_id):
        """
        Enable a previously disabled scheduled call request
        @param schedule_id: id of the schedule for the call request
        @type  schedule_id: str
        """
        update = {'$set': {'enabled': True}}
        self.scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

    def disable(self, schedule_id):
        """
        Disable a scheduled call request without removing it
        @param schedule_id: id of the schedule for the call request
        @type  schedule_id: str
        """
        update = {'$set': {'enabled': False}}
        self.scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

    # query methods ------------------------------------------------------------

    def get(self, schedule_id):
        """
        Get the call request and the schedule for the given schedule id
        @param schedule_id: id of the schedule for the call request
        @type  schedule_id: str
        @return: tuple of (call request, schedule) if found, (None, None) otherwise
        @rtype:  tuple (CallRequest, str) or tupe(None, None)
        """
        scheduled_call = self.scheduled_call_collection.find_one({'_id': schedule_id})
        if scheduled_call is None:
            return (None, None)
        serialized_call_request = scheduled_call['serialized_call_request']
        call_request = call.CallRequest.deserialize(serialized_call_request)
        schedule = scheduled_call['schedule']
        return (call_request, schedule)

    def find(self, *tags):
        """
        Find the scheduled call requests for the given call request tags
        @return: list of tuples (scheduled id, call request, schedule)
        """
        query = {'serialized_call_request.tags': {'$all': tags}}
        scheduled_calls = self.scheduled_call_collection.find(query)
        return [(s['_id'],
                 call.CallRequest.deserialize(s['serialized_call_request']),
                 s['schedule'])
                for s in scheduled_calls]
