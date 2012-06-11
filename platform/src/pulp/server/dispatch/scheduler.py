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

import isodate

from pulp.common import dateutils
from pulp.common.tags import resource_tag
from pulp.server import exceptions as pulp_exceptions
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.dispatch import call
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.util import subdict


_LOG = logging.getLogger(__name__)

SCHEDULE_OPTIONS_FIELDS = ('failure_threshold', 'last_run', 'enabled')
SCHEDULE_MUTABLE_FIELDS = ('call_request', 'schedule', 'failure_threshold',
                           'remaining_runs', 'enabled')
SCHEDULE_REPORT_FIELDS = ('schedule', 'consecutive_failures', 'failure_threshold',
                          'first_run', 'last_run', 'next_run', 'remaining_runs',
                          'enabled')
# scheduler --------------------------------------------------------------------

class Scheduler(object):
    """
    Scheduler class
    Manager and dispatcher of scheduled call requests
    @ivar dispatch_interval: time, in seconds, between schedule checks
    @type dispatch_interval: int
    """

    def __init__(self, dispatch_interval=30):
        self.dispatch_interval = dispatch_interval

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
        coordinator = dispatch_factory.coordinator()
        scheduled_call_collection = ScheduledCall.get_collection()
        now = datetime.datetime.utcnow()
        query = {'next_run': {'$lte': now}}
        for scheduled_call in scheduled_call_collection.find(query):
            if not scheduled_call['enabled']:
                # update the next run information for disabled calls
                self.update_next_run(scheduled_call)
                continue
            serialized_call_request = scheduled_call['serialized_call_request']
            call_request = call.CallRequest.deserialize(serialized_call_request)
            call_request.add_life_cycle_callback(dispatch_constants.CALL_COMPLETE_LIFE_CYCLE_CALLBACK, scheduler_complete_callback)
            call_report = call.CallReport(schedule_id=str(scheduled_call['_id']))
            call_report = coordinator.execute_call_asynchronously(call_request, call_report)
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
        scheduled_call_collection = ScheduledCall.get_collection()
        scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

    def update_next_run(self, scheduled_call):
        """
        Update the metadata for a scheduled call that will be run again
        @param scheduled_call: scheduled call to be updated
        @type  scheduled_call: dict
        """
        scheduled_call_collection = ScheduledCall.get_collection()
        schedule_id = scheduled_call['_id']
        next_run = self.calculate_next_run(scheduled_call)
        if next_run is None:
            # remove the scheduled call if there are no more
            scheduled_call_collection.remove({'_id': schedule_id}, safe=True)
            return
        update = {'$set': {'next_run': next_run}}
        scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

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

        last_run = scheduled_call['last_run']
        if last_run is None:
            return scheduled_call['first_run']

        now = datetime.datetime.utcnow()
        interval = dateutils.parse_iso8601_interval(scheduled_call['schedule'])[0]
        next_run = last_run
        while next_run < now:
            next_run += interval
        return next_run

    # schedule control methods -------------------------------------------------

    def add(self, call_request, schedule, **schedule_options):
        """
        Add a scheduled call request
        Valid schedule options:
         * failure_threshold: max number of consecutive failures, before scheduled call is disabled, None means no max
         * last_run: datetime of the last run of the call request or None if no last run
         * enabled: boolean flag if the scheduled call is enabled or not
        @param call_request: call request to schedule
        @type  call_request: pulp.server.dispatch.call.CallRequest
        @param schedule: iso8601 formatted interval schedule
        @type  schedule: str
        @param schedule_options: keyword options for this schedule
        @type  schedule_options: dict
        @return: schedule id if successfully scheduled or None otherwise
        @rtype:  str or None
        """
        validate_schedule_options(schedule, schedule_options)
        scheduled_call = ScheduledCall(call_request, schedule, **schedule_options)
        next_run = self.calculate_next_run(scheduled_call)
        if next_run is None:
            return None
        scheduled_call_collection = ScheduledCall.get_collection()
        scheduled_call['next_run'] = next_run
        scheduled_call_collection.insert(scheduled_call, safe=True)
        return str(scheduled_call['_id'])

    def update(self, schedule_id, **schedule_updates):
        """
        Update a scheduled call request
        Valid schedule updates:
         * call_request
         * schedule
         * failure_threshold
         * remaining_runs
         * enabled
        @param schedule_id: id of the schedule for the call request
        @type  schedule_id: str
        @param schedule_updates: updates for scheduled call
        @type  schedule_updates: dict
        """
        if isinstance(schedule_id, basestring):
            schedule_id = ObjectId(schedule_id)
        scheduled_call_collection = ScheduledCall.get_collection()
        if scheduled_call_collection.find_one(schedule_id) is None:
            raise pulp_exceptions.MissingResource(schedule=str(schedule_id))
        validate_schedule_updates(schedule_updates)
        call_request = schedule_updates.pop('call_request', None)
        if call_request is not None:
            schedule_updates['serialized_call_request'] = call_request.serialize()
        scheduled_call_collection.update({'_id': schedule_id}, {'$set': schedule_updates}, safe=True)

    def remove(self, schedule_id):
        """
        Remove a scheduled call request
        @param schedule_id: id of the schedule for the call request
        @type  schedule_id: str
        """
        if isinstance(schedule_id, basestring):
            schedule_id = ObjectId(schedule_id)
        scheduled_call_collection = ScheduledCall.get_collection()
        scheduled_call_collection.remove({'_id': schedule_id}, safe=True)

    def enable(self, schedule_id):
        """
        Enable a previously disabled scheduled call request
        @param schedule_id: id of the schedule for the call request
        @type  schedule_id: str
        """
        if isinstance(schedule_id, basestring):
            schedule_id = ObjectId(schedule_id)
        scheduled_call_collection = ScheduledCall.get_collection()
        update = {'$set': {'enabled': True}}
        scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

    def disable(self, schedule_id):
        """
        Disable a scheduled call request without removing it
        @param schedule_id: id of the schedule for the call request
        @type  schedule_id: str
        """
        if isinstance(schedule_id, basestring):
            schedule_id = ObjectId(schedule_id)
        scheduled_call_collection = ScheduledCall.get_collection()
        update = {'$set': {'enabled': False}}
        scheduled_call_collection.update({'_id': schedule_id}, update, safe=True)

    # query methods ------------------------------------------------------------

    def get(self, schedule_id):
        """
        Get the call request and the schedule for the given schedule id
        @param schedule_id: id of the schedule for the call request
        @type  schedule_id: str
        @return: scheduled call report dictionary
        @rtype:  dict
        """
        if isinstance(schedule_id, basestring):
            schedule_id = ObjectId(schedule_id)
        scheduled_call_collection = ScheduledCall.get_collection()
        scheduled_call = scheduled_call_collection.find_one({'_id': schedule_id})
        if scheduled_call is None:
            raise pulp_exceptions.MissingResource(schedule=str(schedule_id))
        report = scheduled_call_to_report_dict(scheduled_call)
        return report

    def find(self, *tags):
        """
        Find the scheduled call requests for the given call request tags
        @param tags: call request tags
        @type  tags: list
        @return: possibly empty list of scheduled call report dictionaries
        @rtype:  list
        """
        scheduled_call_collection = ScheduledCall.get_collection()
        query = {'serialized_call_request.tags': {'$all': tags}}
        scheduled_calls = scheduled_call_collection.find(query)
        reports = [scheduled_call_to_report_dict(s) for s in scheduled_calls]
        return reports

# utility functions ------------------------------------------------------------

def validate_schedule_options(schedule, options):
    """
    Validate the options for a new schedule.
    @param schedule: new schedule
    @type  schedule: basestring
    @param options: new schedule options
    @type  options: dict
    @raise: L{pulp_exceptions.UnsupportedValue}
    @raise: L{pulp_exceptions.InvalidValue}
    """
    invalid_keys = get_invalid_keys(options, SCHEDULE_OPTIONS_FIELDS)
    if invalid_keys:
        raise pulp_exceptions.UnsupportedValue(invalid_keys)
    invalid_values = []
    if not is_valid_schedule(schedule):
        invalid_values.append('schedule')
    if 'failure_threshold' in options and not is_valid_failure_threshold(options['failure_threshold']):
        invalid_values.append('failure_threshold')
    if 'enabled' in options and not is_valid_enabled(options['enabled']):
        invalid_values.append('enabled')
    if invalid_values:
        raise pulp_exceptions.InvalidValue(invalid_values)


def validate_schedule_updates(updates):
    """
    Validate the updates to an existing schedule
    @param updates:
    @return:
    """
    invalid_keys = get_invalid_keys(updates, SCHEDULE_MUTABLE_FIELDS)
    if invalid_keys:
        raise pulp_exceptions.UnsupportedValue(invalid_keys)
    invalid_values = []
    if 'schedule' in updates and not is_valid_schedule(updates['schedule']):
        invalid_values.append('schedule')
    if 'failure_threshold' in updates and not is_valid_failure_threshold(updates['failure_threshold']):
        invalid_values.append('failure_threshold')
    if 'remaining_runs' in updates and not is_valid_remaining_runs(updates['remaining_runs']):
        invalid_values.append('remaining_runs')
    if 'enabled' in updates and not is_valid_enabled(updates['enabled']):
        invalid_values.append('enabled')
    if invalid_values:
        raise pulp_exceptions.InvalidValue(invalid_values)


def get_invalid_keys(dictionary, valid_keys):
    """
    Check that the key of a passed in dictionary are valid and return any
    invalid keys.
    @param dictionary: dictionary to validate
    @type  dictionary: dict
    @param valid_keys: valid dictionary keys
    @type  valid_keys: iterable
    @return: (possibly empty) list of invalid keys
    @rtype:  list
    """
    invalid_keys = []
    for key in dictionary:
        if key not in valid_keys:
            invalid_keys.append(key)
    return invalid_keys


def is_valid_schedule(schedule):
    """
    Validate an iso8601 interval schedule.
    @param schedule: schedule string to validate
    @return: True if the schedule is valid, False otherwise
    @rtype:  bool
    """
    if not isinstance(schedule, basestring):
        return False
    try:
        dateutils.parse_iso8601_interval(schedule)
    except isodate.ISO8601Error:
        return False
    return True


def is_valid_failure_threshold(failure_threshold):
    """
    Validate the failure threshold parameter.
    @param failure_threshold: parameter to validate
    @return: True if the parameter is valid, False otherwise
    @rtype:  bool
    """
    if failure_threshold is None:
        return True
    if isinstance(failure_threshold, int) and failure_threshold > 0:
        return True
    return False


def is_valid_remaining_runs(remaining_runs):
    """
    Validate the remaining runs parameter.
    @param remaining_runs: parameter to validate
    @return: True if the parameter is valid, False otherwise
    @rtype:  bool
    """
    if remaining_runs is None:
        return True
    if isinstance(remaining_runs, int) and remaining_runs >= 0:
        return True
    return False


def is_valid_enabled(enabled):
    """
    Validate the enabled flag.
    @param enabled: flag to validate
    @return: True if the flag is valid, False otherwise
    @rtype:  bool
    """
    return isinstance(enabled, bool)


def scheduled_call_to_report_dict(scheduled_call):
    """
    Build a report dict from a scheduled call.
    @param scheduled_call: scheduled call to build report for
    @type  scheduled_call: BSON
    @return: report dict
    @rtype:  dict
    """
    report = subdict(scheduled_call, SCHEDULE_REPORT_FIELDS)
    call_request = call.CallRequest.deserialize(scheduled_call['serialized_call_request'])
    report['call_request'] = call_request
    report['_id'] = str(scheduled_call['_id'])
    return report


def scheduler_complete_callback(call_request, call_report):
    """
    Call back for task (call_request) results and rescheduling
    """
    scheduler = dispatch_factory.scheduler()
    tag_prefix = resource_tag(dispatch_constants.RESOURCE_SCHEDULE_TYPE, '')
    index = 0
    for i, tag in enumerate(call_request.tags):
        if not tag.startswith(tag_prefix):
            continue
        index = i
        break
    schedule_id = call_request.tags[index][len(tag_prefix):]
    scheduled_call_collection = ScheduledCall.get_collection()
    scheduled_call = scheduled_call_collection.find_one({'_id': ObjectId(schedule_id)})
    scheduler.update_last_run(scheduled_call, call_report)
    scheduler.update_next_run(scheduled_call)

