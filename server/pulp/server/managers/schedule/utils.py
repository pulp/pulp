# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from gettext import gettext as _
import itertools
import logging
import pickle
import time

from bson import ObjectId
from bson.errors import InvalidId
from celery.schedules import schedule as CelerySchedule
import isodate

from pulp.common import dateutils
from pulp.server import exceptions
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.dispatch import ScheduledCall


SCHEDULE_OPTIONS_FIELDS = ('failure_threshold', 'last_run', 'enabled')
SCHEDULE_MUTABLE_FIELDS = ('call_request', 'schedule', 'failure_threshold', 'remaining_runs', 'enabled')

_logger = logging.getLogger(__name__)


def get(schedule_ids):
    """
    Get schedules by ID

    :param schedule_ids:    a list of schedule IDs
    :type  schedule_ids:    list

    :return:    iterator of ScheduledCall instances
    :rtype:     iterator
    """
    try:
        object_ids = map(ObjectId, schedule_ids)
    except InvalidId:
        raise exceptions.InvalidValue(['schedule_ids'])
    criteria = Criteria(filters={'_id': {'$in': object_ids}})
    schedules = ScheduledCall.get_collection().query(criteria)
    return itertools.imap(ScheduledCall.from_db, schedules)


def get_by_resource(resource):
    """
    Get schedules by resource

    :param resource:    unique ID for a lockable resource
    :type  resource:    basestring

    :return:    iterator of ScheduledCall instances
    :rtype:     iterator
    """
    criteria = Criteria(filters={'resource': resource})
    schedules = ScheduledCall.get_collection().query(criteria)
    return itertools.imap(ScheduledCall.from_db, schedules)


def get_enabled():
    """
    Get schedules that are enabled, that is, their "enabled" attribute is True

    :return:    pymongo cursor of ScheduledCall database objects
    :rtype:     pymongo.cursor.Cursor
    """
    criteria = Criteria(filters={'enabled': True})
    return ScheduledCall.get_collection().query(criteria)


def get_updated_since(seconds):
    """
    Get schedules that are enabled, that is, their "enabled" attribute is True,
    and that have been updated since the timestamp represented by "seconds".

    :param seconds: seconds since the epoch
    :param seconds: float

    :return:    pymongo cursor of ScheduledCall database objects
    :rtype:     pymongo.cursor.Cursor
    """
    criteria = Criteria(filters={
        'enabled': True,
        'last_updated': {'$gt': seconds},
    })
    return ScheduledCall.get_collection().query(criteria)


def delete(schedule_id):
    """
    Deletes the schedule with unique ID schedule_id

    :param schedule_id: a unique ID for a schedule
    :type  schedule_id: basestring
    """
    try:
        ScheduledCall.get_collection().remove({'_id': ObjectId(schedule_id)}, safe=True)
    except InvalidId:
        raise exceptions.InvalidValue(['schedule_id'])


def delete_by_resource(resource):
    """
    Deletes all schedules for the specified resource

    :param resource:    string indicating a unique resource
    :type  resource:    basestring
    """
    ScheduledCall.get_collection().remove({'resource': resource}, safe=True)


def update(schedule_id, delta):
    """
    Updates the schedule with unique ID schedule_id. This only allows updating
    of fields in ScheduledCall.USER_UPDATE_FIELDS.

    :param schedule_id: a unique ID for a schedule
    :type  schedule_id: basestring
    :param delta:       a dictionary of keys with values that should be modified
                        on the schedule.
    :type  delta:       dict

    :return:    instance of ScheduledCall representing the post-update state
    :rtype      ScheduledCall

    :raise  exceptions.UnsupportedValue
    :raise  exceptions.MissingResource
    """
    unknown_keys = set(delta.keys()) - ScheduledCall.USER_UPDATE_FIELDS
    if unknown_keys:
        raise exceptions.UnsupportedValue(list(unknown_keys))

    delta['last_updated'] = time.time()


    # bz 1139703 - if we update iso_schedule, update the pickled object as well
    if delta.has_key('iso_schedule'):
        interval, start_time, occurrences = dateutils.parse_iso8601_interval(delta['iso_schedule'])
        delta['schedule'] = pickle.dumps(CelerySchedule(interval))

    try:
        spec = {'_id': ObjectId(schedule_id)}
    except InvalidId:
        raise exceptions.InvalidValue(['schedule_id'])
    schedule = ScheduledCall.get_collection().find_and_modify(
        query=spec, update={'$set': delta}, safe=True, new=True)
    if schedule is None:
        raise exceptions.MissingResource(schedule_id=schedule_id)
    return ScheduledCall.from_db(schedule)


def reset_failure_count(schedule_id):
    """
    Reset the consecutive failure count on a schedule to 0, presumably because
    it ran successfully.

    :param schedule_id: ID of the schedule whose count should be reset
    :type  schedule_id: str
    """
    try:
        spec = {'_id': ObjectId(schedule_id)}
    except InvalidId:
        raise exceptions.InvalidValue(['schedule_id'])
    delta = {'$set': {
        'consecutive_failures': 0,
        'last_updated': time.time(),
    }}
    ScheduledCall.get_collection().update(spec=spec, document=delta)


def increment_failure_count(schedule_id):
    """
    Increment the number of consecutive failures, and if it has met or exceeded
    the threshold, disable the schedule.

    :param schedule_id: ID of the schedule whose count should be incremented
    :type  schedule_id: str
    """
    try:
        spec = {'_id': ObjectId(schedule_id)}
    except InvalidId:
        raise exceptions.InvalidValue(['schedule_id'])
    delta = {
        '$inc': {'consecutive_failures': 1},
        '$set': {'last_updated': time.time()},
    }
    schedule = ScheduledCall.get_collection().find_and_modify(
        query=spec, update=delta, new=True)
    if schedule:
        scheduled_call = ScheduledCall.from_db(schedule)
        if scheduled_call.failure_threshold is None or not scheduled_call.enabled:
            return
        if scheduled_call.consecutive_failures >= scheduled_call.failure_threshold:
            _logger.info(_('disabling schedule %(id)s with %(count)d consecutive failures') % {
                'id': schedule_id, 'count': scheduled_call.consecutive_failures
            })
            delta = {'$set': {
                'enabled': False,
                'last_updated': time.time(),
            }}
            ScheduledCall.get_collection().update(spec, delta)


def validate_keys(options, valid_keys, all_required=False):
    """
    Validate the keys of a dictionary using the list of valid keys.
    :param options: dictionary of options to validate
    :type options: dict
    :param valid_keys: list of keys that are valid
    :type valid_keys: list or tuple
    :param all_required: flag whether all the keys in valid_keys must be present
    :type all_required: bool
    """
    invalid_keys = []
    for key in options:
        if key not in valid_keys:
            invalid_keys.append(key)
    if invalid_keys:
        raise exceptions.InvalidValue(invalid_keys)
    if not all_required:
        return
    missing_keys = []
    for key in valid_keys:
        if key not in options:
            missing_keys.append(key)
    if missing_keys:
        raise exceptions.MissingValue(missing_keys)


def validate_initial_schedule_options(schedule, failure_threshold, enabled):
    """
    Validate the initial schedule and schedule options.

    :param options: options for the schedule
    :type  options: dict
    :raises: pulp.server.exceptions.UnsupportedValue if unsupported schedule options are passed in
    :raises: pulp.server.exceptions.InvalidValue if any of the options are invalid
    """
    invalid_options = []

    if not _is_valid_schedule(schedule):
        invalid_options.append('schedule')

    if not _is_valid_failure_threshold(failure_threshold):
        invalid_options.append('failure_threshold')

    if not _is_valid_enabled_flag(enabled):
        invalid_options.append('enabled')

    if not invalid_options:
        return

    raise exceptions.InvalidValue(invalid_options)


def validate_updated_schedule_options(options):
    """
    Validate updated schedule options.

    :param options: updated options for a scheduled call
    :type  options: dict
    :raises: pulp.server.exceptions.UnsupportedValue if unsupported schedule options are passed in
    :raises: pulp.server.exceptions.InvalidValue if any of the options are invalid
    """

    unknown_options = _find_unknown_options(options, ScheduledCall.USER_UPDATE_FIELDS)

    if unknown_options:
        raise exceptions.UnsupportedValue(unknown_options)

    invalid_options = []

    if 'iso_schedule' in options and not _is_valid_schedule(options['iso_schedule']):
        invalid_options.append('iso_schedule')

    if 'failure_threshold' in options and not _is_valid_failure_threshold(options['failure_threshold']):
        invalid_options.append('failure_threshold')

    if 'remaining_runs' in options and not _is_valid_remaining_runs(options['remaining_runs']):
        invalid_options.append('remaining_runs')

    if 'enabled' in options and not _is_valid_enabled_flag(options['enabled']):
        invalid_options.append('enabled')

    if not invalid_options:
        return

    raise exceptions.InvalidValue(invalid_options)


def _find_unknown_options(options, known_options):
    """
    Search a dictionary of options for unknown keys using a list of known keys.

    :param options: options to search
    :type  options: dict
    :param known_options: list of known options
    :type known_options: iterable of str
    :return: (possibly empty) list of unknown keys from the options dictionary
    :rtype:  list of str
    """

    return [o for o in options if o not in known_options]


def _is_valid_schedule(schedule):
    """
    Test that a schedule string is in the ISO8601 interval format

    :param schedule: schedule string
    :type schedule: str
    :return: True if the schedule is in the ISO8601 format, False otherwise
    :rtype:  bool
    """

    if not isinstance(schedule, basestring):
        return False

    try:
        interval, start_time, runs = dateutils.parse_iso8601_interval(schedule)

    except isodate.ISO8601Error:
        return False

    if runs is not None and runs <= 0:
        return False

    return True


def _is_valid_failure_threshold(failure_threshold):
    """
    Test that a failure threshold is either None or a positive integer.

    :param failure_threshold: failure threshold to test
    :type  failure_threshold: int or None
    :return: True if the failure_threshold is valid, False otherwise
    :rtype:  bool
    """

    if failure_threshold is None:
        return True

    if isinstance(failure_threshold, int) and failure_threshold > 0:
        return True

    return False


def _is_valid_remaining_runs(remaining_runs):
    """
    Test that the remaining runs is either None or a positive integer.

    :param remaining_runs: remaining runs to test
    :type  remaining_runs: int or None
    :return: True if the remaining_runs is valid, False otherwise
    :rtype:  bool
    """

    if remaining_runs is None:
        return True

    if isinstance(remaining_runs, int) and remaining_runs >= 0:
        return True

    return False


def _is_valid_enabled_flag(enabled_flag):
    """
    Test that the enabled flag is a boolean.

    :param enabled_flag: enabled flag to test
    :return: True if the enabled flag is a boolean, False otherwise
    :rtype:  bool
    """

    return isinstance(enabled_flag, bool)
