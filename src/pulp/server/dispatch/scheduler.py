# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Red Hat, Inc.
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
from pprint import pformat

try:
    from bson.objectid import ObjectId
except ImportError:
    from pymongo.objectid import ObjectId

from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.dispatch import call
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.coordinator import Coordinator


_LOG = logging.getLogger(__name__)

# tags -------------------------------------------------------------------------

SCHEDULED_TAG = 'scheduled'

# scheduler --------------------------------------------------------------------

class Scheduler(object):
    """
    Scheduler class
    Manager and dispatcher of scheduled call requests
    @ivar coordinator: Pulp dispatch coordinator
    @type coordinator: pulp.server.dispatch.coordinator.Coordinator instance
    @ivar dispatch_interval: time, in seconds, between schedule checks
    @type dispatch_interval: int
    @ivar scheduled_call_collection: db collection of scheduled call requests
    @type scheduled_call_collection: pymongo.collection.Collection
    """

    def __init__(self, coordinator, dispatch_interval=30):
        assert isinstance(coordinator, Coordinator)
        self.coordinator = coordinator

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
            call_request.add_life_cycle_callback(dispatch_constants.CALL_DEQUEUE_LIFE_CYCLE_CALLBACK, self.call_finished_callback)
            call_report = self.coordinator.execute_call_asynchronously(call_request)
            log_msg = _('Scheduled %s: %s [reasons: %s]') % \
                      (str(call_request), call_report.response, pformat(call_report.reasons))
            if call_report.response is dispatch_constants.CALL_REJECTED_RESPONSE:
                _LOG.error(log_msg)
            else:
                _LOG.info(log_msg)

    def start(self):
        """
        Start the scheduler
        """
        assert self.__dispatcher is None
        self.__lock.acquire()
        self.__exit = False # needed for re-start
        try:
            self.__dispatcher = threading.Thread(target=self.__dispatch)
            self.__dispatcher.setDaemon(True)
            self.__dispatcher.start()
        finally:
            self.__lock.release()

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
            if failure_threshold and failure_threshold <= consecutive_failures:
                delta = update.setdefault('$set', {})
                delta['enabled'] = False
                msg = _('Scheduled task [%s] disabled after %d consecutive failures')
                _LOG.error(msg % (schedule_id, consecutive_failures))
        else:
            delta = update.setdefault('$set', {})
            delta['consecutive_failures'] = 0
        # decrement the remaining runs, if we're tracking that
        if scheduled_call['remaining_runs'] is not None:
            inc = update.setdefault('$inc', {})
            inc['remaining_runs'] = -1
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
        if scheduled_call['remaining_runs'] == 0:
            return None

        now = datetime.datetime.utcnow()
        last_run = scheduled_call['last_run']
        if last_run is None:
            return scheduled_call['start_date']

        next_run = last_run
        interval = datetime.timedelta(seconds=scheduled_call['interval_in_seconds'])
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

    def add(self, scheduled_call_request):
        """
        Add a scheduled call request
        @param scheduled_call_request: scheduled call request
        @type  scheduled_call_request: pulp.server.dispatch.call.ScheduledCallRequest
        @return: schedule id if successfully scheduled or None otherwise
        @rtype:  str or None
        """
        scheduled_call_request.call_request.tags.append(SCHEDULED_TAG)
        scheduled_call = ScheduledCall(scheduled_call_request.call_request,
                                       scheduled_call_request.schedule,
                                       scheduled_call_request.failure_threshold,
                                       scheduled_call_request.last_run)
        next_run = self.calculate_next_run(scheduled_call)
        if next_run is None:
            return None
        scheduled_call['next_run'] = next_run
        self.scheduled_call_collection.insert(scheduled_call, safe=True)
        return str(scheduled_call['_id'])

    def remove(self, schedule_id):
        """
        Remove a scheduled call request
        @param schedule_id: id of the schedule for the call request
        @type  schedule_id: str
        """
        if isinstance(schedule_id, basestring):
            schedule_id = ObjectId(schedule_id)
        self.scheduled_call_collection.remove({'_id': schedule_id}, safe=True)

    def enable(self, schedule_id):
        """
        Enable a previously disabled scheduled call request
        @param schedule_id: id of the schedule for the call request
        @type  schedule_id: str
        """
        if isinstance(schedule_id, basestring):
            schedule_id = ObjectId(schedule_id)
        update = {'$set': {'enabled': True}}
        self.scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

    def disable(self, schedule_id):
        """
        Disable a scheduled call request without removing it
        @param schedule_id: id of the schedule for the call request
        @type  schedule_id: str
        """
        if isinstance(schedule_id, basestring):
            schedule_id = ObjectId(schedule_id)
        update = {'$set': {'enabled': False}}
        self.scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

    # query methods ------------------------------------------------------------

    def get(self, schedule_id):
        """
        Get the scheduled call request for the given schedule id
        @param schedule_id: id of the schedule for the call request
        @type  schedule_id: str
        @return: scheduled call request corresponding to the schedule_id
        @rtype:  call.ScheduledCall or None
        """
        if isinstance(schedule_id, basestring):
            schedule_id = ObjectId(schedule_id)
        scheduled_call = self.scheduled_call_collection.find_one({'_id': schedule_id})
        if scheduled_call is None:
            return None
        return scheduled_call_to_request(scheduled_call)

    def find(self, *tags):
        """
        Find the scheduled call requests for the given call request tags
        @param tags: arbitrary tags to search on
        @type  tags: list of str
        @return: (possibly empty) list of call.ScheduleCallRequest
        @rtype:  list
        """
        query = {'serialized_call_request.tags': {'$all': tags}}
        scheduled_calls = self.scheduled_call_collection.find(query)
        return [scheduled_call_to_request(s) for s in scheduled_calls]

# utility functions ------------------------------------------------------------

def scheduled_call_to_request(scheduled_call):
    """
    Convert a scheduled call into a corresponding scheduled call request.
    @param scheduled_call: scheduled call to convert
    @type  scheduled_call: document from scheduled_calls mongodb collection
    @return: scheduled call request
    @rtype:  call.ScheduledCallRequest
    """
    call_request = call.CallRequest.deserialize(scheduled_call['serialized_call_request'])
    schedule = scheduled_call['schedule']
    failure_threshold = scheduled_call['failure_threshold']
    last_run = scheduled_call['last_run']
    enabled = scheduled_call['enabled']
    request = call.ScheduledCallRequest(call_request, schedule, failure_threshold, last_run, enabled)
    request.schedule_id = str(scheduled_call['_id'])
    return request


