# -*- coding: utf-8 -*-
#
# Copyright © 2011-2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software;
# if not, see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import datetime
import logging
import threading
from pprint import pformat

import isodate

from pulp.common import dateutils
from pulp.server import exceptions as pulp_exceptions
from pulp.server.compat import ObjectId
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.dispatch import call
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.util import subdict

# -- constants -----------------------------------------------------------------

DEFAULT_DISPATCH_INTERVAL = 30 # time between checks for running scheduled calls, in seconds

ZERO_TIME = datetime.timedelta(seconds=0)

SCHEDULE_OPTIONS_FIELDS = ('failure_threshold', 'last_run', 'enabled')

SCHEDULE_MUTABLE_FIELDS = ('call_request', 'schedule', 'failure_threshold', 'remaining_runs', 'enabled')

SCHEDULE_REPORT_FIELDS = ('schedule', 'consecutive_failures', 'failure_threshold', 'first_run',
                          'last_run', 'next_run', 'remaining_runs', 'enabled')

_LOG = logging.getLogger(__name__)

# -- scheduler class -----------------------------------------------------------

class Scheduler(object):

    def __init__(self, dispatch_interval=DEFAULT_DISPATCH_INTERVAL):

        self.dispatch_interval = dispatch_interval
        self.scheduled_call_collection = ScheduledCall.get_collection()

        self.__exit = False
        self.__lock = threading.RLock()
        self.__condition = threading.Condition(self.__lock)
        self.__dispatch_thread = None

    # -- dispatch thread methods -----------------------------------------------

    def __dispatch(self):

        self.__lock.acquire()

        while True:

            self.__condition.wait(timeout=self.dispatch_interval)

            if self.__exit:
                return self.__lock is not None and self.__lock.release()

            try:
                self._run_scheduled_calls()

            except Exception, e:
                _LOG.critical('Unhandled exception in scheduler dispatch thread: %s' % repr(e))
                _LOG.exception(e)

    def _run_scheduled_calls(self):

        coordinator = dispatch_factory.coordinator()

        for call_request_group in self._get_call_request_groups_for_scheduled_itineraries():

            # dispatch the itinerary
            call_report_list = coordinator.execute_multiple_calls(call_request_group)

            # log the scheduled itinerary's dispatch
            for call_request, call_report in zip(call_request_group, call_report_list):
                _LOG.info('Scheduled %s: %s [reasons: %s]' %
                          (str(call_request), call_report.response, pformat(call_report.reasons)))

    def _get_call_request_groups_for_scheduled_itineraries(self):

        coordinator = dispatch_factory.coordinator()

        query = {'next_run': {'$lte': datetime.datetime.utcnow()}}

        for scheduled_call in self.scheduled_call_collection.find(query):

            # skip this call if it is disabled, but update the next run in case
            # the call is re-enabled
            if not scheduled_call['enabled']:
                self.update_next_run(scheduled_call)
                continue

            # look for incomplete calls from this schedule to determine if the
            # last calls from this schedule are still running, and skip if they are
            scheduled_call_reports = coordinator.find_call_reports(schedule_id=scheduled_call['id'])

            if any(r.state not in dispatch_constants.CALL_COMPLETE_STATES for r in scheduled_call_reports):

                _LOG.info('Schedule %s skipped: last scheduled call still running' % scheduled_call['id'])
                self.update_next_run(scheduled_call)
                continue

            # set the last run to now, and update the next run to prevent the
            # scheduler from trying to run the call again if it takes longer
            # than self.dispatch_interval to run
            # NOTE: these are order sensitive!
            self.update_last_run(scheduled_call)
            self.update_next_run(scheduled_call)

            call_request_group = self._execute_itinerary(scheduled_call)

            self._reset_call_group_metadata(scheduled_call, call_request_group)

            yield call_request_group

    def _execute_itinerary(self, scheduled_call):

        coordinator = dispatch_factory.coordinator()

        # scheduled calls are always itinerary calls
        itinerary_call_request = call.CallRequest.deserialize(scheduled_call['serialized_call_request'])
        itinerary_call_request.archive = False # don't keep a history of these calls

        itinerary_call_report = call.CallReport.from_call_request(itinerary_call_request)
        itinerary_call_report.serialize_result = False # don't try to serialize the result

        # use the coordinator to execute the itinerary call, it already has all
        # the machinery to handle the call request and report instances
        itinerary_call_report = coordinator.execute_call_synchronously(itinerary_call_request,
                                                                       itinerary_call_report)

        # the call request group is the result of the itinerary call
        call_request_group = itinerary_call_report.result

        self._set_call_group_scheduler_hooks(scheduled_call, call_request_group)

        return call_request_group

    # -- dispatch thread utility methods ---------------------------------------

    def _reset_call_group_metadata(self, scheduled_call, call_request_group):

        # record the total number of call requests in this call group and
        # reset the exit state of the call
        update = {'call_count': len(call_request_group),
                  'call_exit_states': []}
        self.scheduled_call_collection.update({'_id': scheduled_call['_id']}, {'$set': update}, safe=True)

    def _set_call_group_scheduler_hooks(self, scheduled_call, call_request_group):

        # set the schedule_id on the call requests and add scheduler-specific life cycle callbacks
        for call_request in call_request_group:
            call_request.schedule_id = str(scheduled_call['_id'])
            call_request.add_life_cycle_callback(dispatch_constants.CALL_COMPLETE_LIFE_CYCLE_CALLBACK,
                                                 scheduler_complete_callback)

    # -- dispatch thread lifecycle methods -------------------------------------

    def start(self):
        assert self.__dispatch_thread is None

        with self.__lock:

            self.__exit = False # needed for re-starts

            self.__dispatch_thread = threading.Thread(target=self.__dispatch)
            self.__dispatch_thread.setDaemon(True)
            self.__dispatch_thread.start()

    def stop(self):
        assert self.__dispatch_thread is not None

        with self.__lock:

            self.__exit = True
            self.__condition.notify()

        self.__dispatch_thread.join()
        self.__dispatch_thread = None

    # -- scheduling helper methods ---------------------------------------------

    @staticmethod
    def calculate_first_run(schedule):

        now = datetime.datetime.utcnow()
        interval, start = dateutils.parse_iso8601_interval(schedule)[0:2]

        first_run = start or now

        while interval != ZERO_TIME and first_run <= now:
            first_run = dateutils.add_interval_to_datetime(interval, first_run)

        return first_run

    @staticmethod
    def calculate_next_run(scheduled_call):

        if scheduled_call['remaining_runs'] == 0:
            return None

        last_run = scheduled_call['last_run']

        if last_run is None:
            return scheduled_call['first_run']

        now = datetime.datetime.utcnow()
        interval = dateutils.parse_iso8601_interval(scheduled_call['schedule'])[0]

        next_run = last_run

        while next_run < now:
            next_run = dateutils.add_interval_to_datetime(interval, next_run)

        return next_run

    def update_last_run(self, scheduled_call):

        # use the old next_run as the last_run to prevent schedule drift
        update = {'$set': {'last_run': scheduled_call['next_run']}}

        if scheduled_call['remaining_runs'] is not None:
            update['$inc'] = {'remaining_runs': -1}

        schedule_id = scheduled_call['_id']
        self.scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

    def update_next_run(self, scheduled_call):

        schedule_id = scheduled_call['_id']
        next_run = self.calculate_next_run(scheduled_call)

        if next_run is None:
            self.scheduled_call_collection.remove({'_id': schedule_id}, safe=True)

        else:
            update = {'$set': {'next_run': next_run}}
            self.scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

    def update_consecutive_failures_and_runs(self, scheduled_call):

        update = {}

        # increment the consecutive failures if any of the calls failed
        if dispatch_constants.CALL_ERROR_STATE in scheduled_call['call_exit_states']:
            inc = update.setdefault('$inc', {})
            inc['consecutive_failures'] = 1

            failure_threshold = scheduled_call['failure_threshold']
            consecutive_failures = scheduled_call['consecutive_failures'] + 1

            # disable the schedule if the consecutive failures surpasses the failure threshold
            if failure_threshold is not None and failure_threshold <= consecutive_failures:
                delta = update.setdefault('$set', {})
                delta['enabled'] = False
                msg = 'Schedule [%s] disabled after %d consecutive failures'
                _LOG.error(msg % (str(scheduled_call['_id']), consecutive_failures))

        # all calls in call group completed successfully, so reset the consecutive_failures to 0
        elif all(s == dispatch_constants.CALL_FINISHED_STATE for s in scheduled_call['call_exit_states']):
            delta = update.setdefault('$set', {})
            delta['consecutive_failures'] = 0

        # decrement the remaining runs, if they're being tracked
        if scheduled_call['remaining_runs'] is not None:
            inc = update.setdefault('$inc', {})
            inc['remaining_runs'] = -1

        self.scheduled_call_collection.update({'_id': scheduled_call['_id']}, update, safe=True)

    # -- schedule management methods -------------------------------------------

    def add(self, itinerary_call_request, schedule, **schedule_options):

        validate_initial_schedule_options(schedule, schedule_options)

        scheduled_call = ScheduledCall(itinerary_call_request, schedule, **schedule_options)

        scheduled_call['first_run'] = self.calculate_first_run(schedule)
        scheduled_call['next_run'] = self.calculate_next_run(scheduled_call)

        if scheduled_call['next_run'] is None:
            return None

        self.scheduled_call_collection.insert(scheduled_call, safe=True)

        return str(scheduled_call['_id'])

    def update(self, schedule_id, **updated_schedule_options):

        if isinstance(schedule_id, basestring):
            schedule_id = ObjectId(schedule_id)

        if self.scheduled_call_collection.find_one(schedule_id) is None:
            raise pulp_exceptions.MissingResource(schedule=str(schedule_id))

        validate_updated_schedule_options(updated_schedule_options)

        call_request = updated_schedule_options.pop('call_request', None)

        if isinstance(call_request, call.CallRequest):
            updated_schedule_options['serialized_call_request'] = call_request.serialize()

        schedule = updated_schedule_options.pop('schedule', None)

        if schedule is not None:
            runs = dateutils.parse_iso8601_interval(schedule)[2]
            updated_schedule_options.setdefault('remaining_runs', runs) # honor explicit update
            updated_schedule_options['next_run'] = self.calculate_first_run(schedule)

        self.scheduled_call_collection.update({'_id': schedule_id}, {'$set': updated_schedule_options}, safe=True)

    def remove(self, schedule_id):
        if isinstance(schedule_id, basestring):
            schedule_id = ObjectId(schedule_id)

        if self.scheduled_call_collection.find_one({'_id': schedule_id}) is None:
            raise pulp_exceptions.MissingResource(schedule=str(schedule_id))

        self.scheduled_call_collection.remove({'_id': schedule_id}, safe=True)

    # -- schedule query methods ------------------------------------------------

    def get(self, schedule_id):

        if isinstance(schedule_id, basestring):
            schedule_id = ObjectId(schedule_id)

        scheduled_call = self.scheduled_call_collection.find_one({'_id': schedule_id})

        if scheduled_call is None:
            raise pulp_exceptions.MissingResource(schedule=str(schedule_id))

        return scheduled_call_to_report_dict(scheduled_call)

    def find(self, *tags):

        query = {'serialized_call_request.tags': {'$all': tags}}
        scheduled_calls = self.scheduled_call_collection.find(query)

        return [scheduled_call_to_report_dict(c) for c in scheduled_calls]

    # -- scheduled call completion ---------------------------------------------

    def call_group_call_completed(self, schedule_id, state):

        if isinstance(schedule_id, basestring):
            schedule_id = ObjectId(schedule_id)

        update = {'$inc': {'call_count': -1},
                  '$push': {'call_exit_states': state}}

        # update and return the updated scheduled_call
        # returns None if the scheduled_call doesn't exist
        scheduled_call = self.scheduled_call_collection.find_and_modify({'id': schedule_id}, update, new=True)

        # schedule was deleted while call was running
        if scheduled_call is None:
            return

        if scheduled_call['call_count'] > 0:
            return

        self.update_consecutive_failures_and_runs(scheduled_call)

# -- scheduler call request lifecycle callbacks --------------------------------

def scheduler_complete_callback(call_request, call_report):

    scheduler = dispatch_factory.scheduler()
    scheduler.call_group_call_completed(call_request.schedule_id, call_report.state)

# -- schedule validation methods -----------------------------------------------

def validate_initial_schedule_options(schedule, options):

    unknown_options = _find_unknown_options(options, SCHEDULE_OPTIONS_FIELDS)

    if unknown_options:
        raise pulp_exceptions.UnsupportedValue(unknown_options)

    invalid_options = []

    if not _is_valid_schedule(schedule):
        invalid_options.append('schedule')

    if 'failure_threshold' in options and not _is_valid_failure_threshold(options['failure_threshold']):
        invalid_options.append('failure_threshold')

    if 'enabled' in options and not _is_valid_enabled_flag(options['enabled']):
        invalid_options.append('enabled')

    if not invalid_options:
        return

    raise pulp_exceptions.InvalidValue(invalid_options)


def validate_updated_schedule_options(options):

    unknown_options = _find_unknown_options(options, SCHEDULE_MUTABLE_FIELDS)

    if unknown_options:
        raise pulp_exceptions.UnsupportedValue(unknown_options)

    invalid_options = []

    if 'schedule' in options and not _is_valid_schedule(options['schedule']):
        invalid_options.append('schedule')

    if 'failure_threshold' in options and not _is_valid_failure_threshold(options['failure_threshold']):
        invalid_options.append('failure_threshold')

    if 'remaining_runs' in options and not _is_valid_remaining_runs(options['remaining_runs']):
        invalid_options.append('remaining_runs')

    if 'enabled' in options and not _is_valid_enabled_flag(options['enabled']):
        invalid_options.append('enabled')

    if not invalid_options:
        return

    raise pulp_exceptions.InvalidValue(invalid_options)


def _find_unknown_options(options, known_options):

    return [o for o in options if o not in known_options]


def _is_valid_schedule(schedule):

    if not isinstance(schedule, basestring):
        return False

    try:
        dateutils.parse_iso8601_interval(schedule)

    except isodate.ISO8601Error:
        return False

    return True


def _is_valid_failure_threshold(failure_threshold):

    if failure_threshold is None:
        return True

    if isinstance(failure_threshold, int) and failure_threshold > 0:
        return True

    return False


def _is_valid_remaining_runs(remaining_runs):

    if remaining_runs is None:
        return True

    if isinstance(remaining_runs, int) and remaining_runs >= 0:
        return True

    return False


def _is_valid_enabled_flag(enabled_flag):

    return isinstance(enabled_flag, bool)

# -- schedule reporting utility methods ----------------------------------------

def scheduled_call_to_report_dict(scheduled_call):

    report = subdict(scheduled_call, SCHEDULE_REPORT_FIELDS)
    report['_id'] = str(scheduled_call['_id'])
    report['call_request'] = call.CallRequest.deserialize(scheduled_call['serialized_call_request'])

    return report
