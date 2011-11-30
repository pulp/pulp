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

from pulp.common import dateutils
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.dispatch import call
from pulp.server.util import Singleton


_LOG = logging.getLogger(__name__)

# tags -------------------------------------------------------------------------

SCHEDULED_TAG = 'scheduled'

# scheduler --------------------------------------------------------------------

class Scheduler(object):

    __metaclass__ = Singleton

    def __init__(self, dispatch_interval=30):

        self.dispatch_interval = dispatch_interval
        self.scheduled_call_collection = ScheduledCall.get_collection()

        self.__exit = False
        self.__lock = threading.RLock()
        self.__condition = threading.Condition(self.__lock)

        self.__dispatcher = threading.Thread(target=self.__dispatch)
        self.__dispatcher.setDaemon(True)
        self.__dispatcher.start()

    # scheduled calls dispatch -------------------------------------------------

    def __dispatch(self):
        self.__lock.acquire()
        while True:
            self.__condition.wait(timeout=self.dispatch_interval)
            if self.__exit:
                if self.__lock is not None:
                    self.__lock.release()
                return
            try:
                self.run_scheduled_calls()
            except Exception, e:
                _LOG.critical('Unhandled exception in scheduler dispatch: %s' % repr(e))
                _LOG.exception(e)

    def exit(self):
        self.__exit = True

    def run_scheduled_calls(self):
        now = datetime.datetime.utcnow()
        # TODO account for daylight savings time
        query = {'next_run': {'$lte': now}}
        for scheduled_call in self.scheduled_call_collection.find(query):
            if not scheduled_call['enabled']:
                continue
            serialized_call_request = scheduled_call['serialized_call_request']
            call_request = call.CallRequest.deserialize(serialized_call_request)
            self.run_via_legacy_tasking(call_request)
            self.update_scheduled_call(scheduled_call)

    def run_via_legacy_tasking(self, call_request):
        pass

    def run_via_taskqueue(self, call_request):
        raise NotImplementedError()

    def run_via_coordinator(self, call_request):
        raise NotImplementedError()

    def update_scheduled_call(self, scheduled_call):
        schedule_id = scheduled_call['_id']

        # update the last_run
        # use scheduled time instead of current to prevent schedule drift
        last_run = scheduled_call['next_run']
        scheduled_call['last_run'] = last_run
        if scheduled_call['runs'] is not None:
            scheduled_call['runs'] -= 1

        # update the next_run
        next_run = self.next_run(scheduled_call)
        if next_run is None:
            # remove the scheduled call if there are no more
            self.scheduled_call_collection.remove({'_id': schedule_id}, safe=True)
            return

        # update the persisted scheduled call
        update = {'$set': {'last_run': last_run, 'next_run': next_run}}
        self.scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

    # scheduling ---------------------------------------------------------------

    def next_run(self, scheduled_call):
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

    # schedule control ---------------------------------------------------------

    def add(self, call_request, schedule, last_run=None):
        call_request.tags.append(SCHEDULED_TAG)
        scheduled_call = ScheduledCall(call_request, schedule, last_run)
        next_run = self.next_run(scheduled_call)
        if next_run is None:
            return None
        self.scheduled_call_collection.insert(scheduled_call, safe=True)
        return scheduled_call['_id']

    def remove(self, schedule_id):
        self.scheduled_call_collection.remove({'_id': schedule_id}, safe=True)

    def enable(self, schedule_id):
        update = {'$set': {'enabled': True}}
        self.scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

    def disable(self, schedule_id):
        update = {'$set': {'enabled': False}}
        self.scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

    # query methods ------------------------------------------------------------

    def find(self, **criteria):
        pass

    def history(self, **criteria):
        pass

