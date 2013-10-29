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
from bson import ObjectId
import isodate
import time

from pulp.common import dateutils
from pulp.server import exceptions
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.dispatch import ScheduledCall


SCHEDULE_OPTIONS_FIELDS = ('failure_threshold', 'last_run', 'enabled')
SCHEDULE_MUTABLE_FIELDS = ('call_request', 'schedule', 'failure_threshold', 'remaining_runs', 'enabled')


def get(schedule_ids):
    object_ids = map(ObjectId, schedule_ids)
    criteria = Criteria(filters={'_id': {'$in': object_ids}})
    schedules = ScheduledCall.get_collection().query(criteria)
    return map(ScheduledCall.from_db, schedules)


def get_by_resource(resource):
    criteria = Criteria(filters={'resource': resource})
    schedules = ScheduledCall.get_collection().query(criteria)
    return map(ScheduledCall.from_db, schedules)


def delete(schedule_id):
    ScheduledCall.get_collection().remove({'_id': ObjectId(schedule_id)}, safe=True)


def update(schedule_id, delta):
    unknown_keys = set(delta.keys()) - ScheduledCall.USER_UPDATE_FIELDS
    if unknown_keys:
        raise exceptions.UnsupportedValue(list(unknown_keys))

    delta['last_updated'] = time.time()

    kwargs = delta.pop('kwargs', {})
    for key, value in kwargs.iteritems():
        delta['kwargs.%s' % key] = value

    spec = {'_id': ObjectId(schedule_id)}
    ScheduledCall.get_collection().update(spec, {'$set': delta}, safe=True)


def validate_keys(options, valid_keys, all_required=False):
    """
    Validate the keys of a dictionary using the list of valid keys.
    @param options: dictionary of options to validate
    @type options: dict
    @param valid_keys: list of keys that are valid
    @type valid_keys: list or tuple
    @param all_required: flag whether all the keys in valid_keys must be present
    @type all_required: bool
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


def validate_initial_schedule_options(options):
    """
    Validate the initial schedule and schedule options.

    :param options: options for the schedule
    :type  options: dict
    :raises: pulp.server.exceptions.UnsupportedValue if unsupported schedule options are passed in
    :raises: pulp.server.exceptions.InvalidValue if any of the options are invalid
    """

    options = options.copy()
    schedule = options.pop('schedule', None)

    unknown_options = _find_unknown_options(options, SCHEDULE_OPTIONS_FIELDS)

    if unknown_options:
        raise exceptions.UnsupportedValue(unknown_options)

    invalid_options = []

    if not _is_valid_schedule(schedule):
        invalid_options.append('schedule')

    if 'failure_threshold' in options and not _is_valid_failure_threshold(options['failure_threshold']):
        invalid_options.append('failure_threshold')

    if 'enabled' in options and not _is_valid_enabled_flag(options['enabled']):
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
