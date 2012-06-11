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
import sys
from gettext import gettext as _
from types import NoneType

try:
    from bson import BSON, SON
except ImportError:
    from pymongo.bson import BSON
    from pymongo.son import SON

from isodate import ISO8601Error

from pulp.common import dateutils
from pulp.common.util import encode_unicode
from pulp.server import async, config
from pulp.server.api.repo_sync_task import RepoSyncTask
from pulp.server.db.model.cds import CDS
from pulp.server.db.model.resource import Repo
from pulp.server.exceptions import PulpException, PulpDataException
from pulp.server.tasking.exception import UnscheduledTaskException
from pulp.server.tasking.scheduler import IntervalScheduler
from pulp.server.tasking.task import task_complete_states, Task


class ScheduleValidationError(PulpDataException):
    pass

# schedule validation and manipulation -----------------------------------------

def validate_schedule(schedule):
    """
    Validate and standardize the format of an interval schedule specified in
    iso8601 format.
    @raise PulpException: when the schedule is not in iso8601 format
    @type schedule: str
    @param schedule: interval schedule in iso8601 format
    @rtype: str
    @return: interval schedule in pulp's standard iso8601 format
    """
    interval = start = runs = None
    try:
        interval, start, runs = dateutils.parse_iso8601_interval(schedule)
    except ISO8601Error:
        raise PulpException(_('Improperly formatted schedule: %s') % schedule), None, sys.exc_info()[2]
    if not isinstance(interval, datetime.timedelta):
        raise PulpException(_('Invalid type for interval: %s') % str(type(interval)))
    # convert the start time to the local timezone
    if isinstance(start, datetime.datetime):
        start = dateutils.to_local_datetime(start)
    # re-format the schedule into pulp's standard format
    return dateutils.format_iso8601_interval(interval, start, runs)


def parse_and_validate_repo_sync_options(options):
    """
    Parse, validate, and return a normalized version of the options, ready to
    use by the scheduled sync.
    @param options: repo sync options
    @type options: dict
    @return: normalized, valid options to be used a kwargs to the sync task
    @rtype: dict
    """
    def _parse_int(k, i):
        try:
            return int(i)
        except TypeError:
            raise ScheduleValidationError(_('Invalid value for option %(o)s: %(v)s') %
                                      {'o': k, 'v': i}), None, sys.exc_info()[2]

    def _parse_timeout(t):
        if not t:
            return None
        try:
            timeout = dateutils.parse_iso8601_duration(t)
            if not isinstance(timeout, datetime.timedelta):
                raise ScheduleValidationError()
            return timeout
        except (ISO8601Error, ScheduleValidationError):
            raise ScheduleValidationError(_('Invalid value for option timeout: %(v)s') %
                                      {'v': t}), None, sys.exc_info()[2]

    def _parse_skip(s):
        valid_skips = ('packages', 'errata', 'distribution')
        skip_dict = {}
        for skip, value in s.items():
            if skip not in valid_skips:
                raise ScheduleValidationError(_('Invalid skip specification: %(s)s') % {'s': skip})
            try:
                skip_dict[skip] = int(bool(value))
            except TypeError:
                raise ScheduleValidationError(_('Invalid skip value for %(s)s: %(v)s') %
                                          {'s': skip, 'v': value}), None, sys.exc_info()[2]
        return skip_dict


    if not options:
        return {}
    new_options = {}
    valid_keys = ('max_speed', 'threads', 'timeout', 'skip')
    for key, value in options.items():
        if key not in valid_keys:
            raise ScheduleValidationError(_('Unknown sync option: %(o)s') % {'o': key})
        if key in valid_keys[:2]:
            new_options[key] = _parse_int(key, value)
        elif key == valid_keys[2]:
            new_options[key] = _parse_timeout(value)
        elif key == valid_keys[3]:
            new_options[key] = _parse_skip(value)
    return new_options

# sync task management ---------------------------------------------------------

def schedule_to_scheduler(schedule):
    """
    Convenience function to turn a serialized task schedule into an interval
    scheduler appropriate for scheduling a sync task.
    @type schedule: basestring
    @param schedule: sync schedule to turn into interval scheduler in iso8601 format
    @rtype: L{IntervalScheduler}
    @return: interval scheduler for the tasking sub-system
    """
    i, s, r = dateutils.parse_iso8601_interval(schedule)
    if s is not None:
        s = dateutils.to_local_datetime(s)
    return IntervalScheduler(i, s, r)


def find_scheduled_task(id, method_name):
    """
    Look up a schedule task in the task sub-system for a given method
    @type id: str
    @param id: argument to the task
    @rtype: None or L{pulp.server.tasking.task.Task}
    @return: the sync task, None if no task is found
    """
    # NOTE this is very inefficient in the worst case: DO NOT CALL OFTEN!!
    # the number of sync tasks * (mean # arguments + mean # keyword arguments)
    for task in async.find_async(method_name=method_name):
        if task.args and encode_unicode(id) in task.args or \
                task.kwargs and encode_unicode(id) in task.kwargs.values():
            return task
    return None


def _add_repo_scheduled_sync_task(repo):
    """
    Add a new repo sync task for the given repo
    @type repo: L{pulp.server.db.model.resource.Repo}
    @param repo: repo to add sync task for
    """
    # hack to avoid circular imports
    from repo_sync import (_sync, get_synchronizer,
                           local_progress_callback, yum_rhn_progress_callback)
    # make sure the keys for the kwargs dict are strings!
    kwargs = dict((str(k), v) for k, v in repo['sync_options'].items())
    task = RepoSyncTask(_sync, [repo['id']], kwargs=kwargs)
    task.scheduler = schedule_to_scheduler(repo['sync_schedule'])
    # if no start time is provided, fallback to the last successful sync
    # otherwise start immediately
    if task.scheduler.start_time is None and repo.get('last_sync') is not None:
        task.scheduler.start_time = dateutils.parse_iso8601_datetime(repo['last_sync'])
    content_type = repo['content_types']
    synchronizer = get_synchronizer(content_type)
    task.set_synchronizer(synchronizer)
    source_type = repo['source']['type']
    if content_type == 'yum':
        task.weight = config.config.getint('yum', 'task_weight')
    if source_type == 'remote':
        task.set_progress('progress_callback', yum_rhn_progress_callback)
    elif source_type == 'local':
        task.set_progress('progress_callback', local_progress_callback)
    return async.enqueue(task)


def _add_cds_scheduled_sync_task(cds):
    from pulp.server.api.cds import CdsApi
    api = CdsApi()
    task = Task(api.cds_sync, [cds['hostname']])
    task.scheduler = schedule_to_scheduler(cds['sync_schedule'])
    return async.enqueue(task)


def _update_repo_scheduled_sync_task(repo, task):
    """
    Update and existing repo sync task's schedule
    @type repo: L{pulp.server.db.model.resource.Repo}
    @param repo: repo to update sync task for
    @type task: L{pulp.server.tasking.task.Task}
    @param task: task to update
    """
    new_scheduler = schedule_to_scheduler(repo['sync_schedule'])
    task.kwargs = repo['sync_options'] or {}
    return async.reschedule_async(task, new_scheduler)


def _update_cds_scheduled_sync_task(cds, task):
    new_scheduler = schedule_to_scheduler(cds['sync_schedule'])
    return async.reschedule_async(task, new_scheduler)


def _remove_repo_scheduled_sync_task(repo):
    """
    Remove the repo sync task from the tasking sub-system for the given repo
    @type repo: L{pulp.server.db.model.resource.Repo}
    @param repo: repo to remove task for
    """
    task = find_scheduled_task(repo['id'], '_sync')
    if task is None:
        return
    async.remove_async(task)


def _remove_cds_scheduled_sync_task(cds):
    task = find_scheduled_task(cds['hostname'], 'cds_sync')
    if task is None:
        return
    async.remove_async(task)

# existing api -----------------------------------------------------------------

def update_repo_schedule(repo, new_schedule, new_options):
    """
    Change a repo's sync schedule.
    @type repo: L{pulp.server.db.model.resource.Repo}
    @param repo: repo to change
    @type new_schedule: str
    @param new_schedule: new schedule in iso8601 format
    @type new_options: dict
    @param new_options: new sync options
    """
    if repo['source'] is None:
        raise PulpException(_('Cannot add schedule to repository without sync source'))
    sync_schedule = validate_schedule(new_schedule)
    sync_options = parse_and_validate_repo_sync_options(new_options)
    collection = Repo.get_collection()
    collection.update({'_id': repo['_id']},
                      {'$set': {'sync_schedule': sync_schedule,
                                'sync_options': sync_options}},
                      safe=True)
    task = find_scheduled_task(repo['id'], '_sync')
    repo['sync_schedule'] = sync_schedule
    repo['sync_options'] = sync_options
    if task is None:
        _add_repo_scheduled_sync_task(repo)
    else:
        _update_repo_scheduled_sync_task(repo, task)


def delete_repo_schedule(repo):
    """
    Remove a repo's sync schedule
    @type repo: L{pulp.server.db.model.resource.Repo}
    @param repo: repo to change
    """
    if repo['sync_schedule'] is None:
        return
    collection = Repo.get_collection()
    collection.update({'_id': repo['_id']},
                      {'$set': {'sync_schedule': None,
                                'sync_options': {}}},
                      safe=True)
    repo['sync_schedule'] = None
    _remove_repo_scheduled_sync_task(repo)


def update_cds_schedule(cds, new_schedule):
    '''
    Change a CDS sync schedule.
    '''
    cds['sync_schedule'] = validate_schedule(new_schedule)
    collection = CDS.get_collection()
    collection.save(cds, safe=True)
    task = find_scheduled_task(cds['hostname'], 'cds_sync')
    if task is None:
        _add_cds_scheduled_sync_task(cds)
    else:
        _update_cds_scheduled_sync_task(cds, task)


def delete_cds_schedule(cds):
    if cds['sync_schedule'] is None:
        return
    cds['sync_schedule'] = None
    collection = CDS.get_collection()
    collection.save(cds, safe=True)
    _remove_cds_scheduled_sync_task(cds)

# startup initialization -------------------------------------------------------

def init_scheduled_syncs():
    """
    Iterate through all of the repos in the database and start sync tasks for
    those that have sync schedules associated with them.
    """
    _init_repo_scheduled_syncs()
    _init_cds_scheduled_syncs()


def _init_repo_scheduled_syncs():
    collection = Repo.get_collection()
    log = logging.getLogger('pulp')
    for repo in collection.find({}):
        if repo['sync_schedule'] is None:
            continue
        if _add_repo_scheduled_sync_task(repo) is None:
            log.info(_('Scheduled sync for %s already in task queue') % repo['id'])
        else:
            log.info(_('Added scheduled sync for %s to task queue') % repo['id'])


def _init_cds_scheduled_syncs():
    collection = CDS.get_collection()
    log = logging.getLogger('pulp')
    for cds in collection.find({}):
        if cds['sync_schedule'] is None:
            continue
        if _add_cds_scheduled_sync_task(cds) is None:
            log.info(_('Scheduled sync for %s already in task queue') % cds['id'])
        else:
            log.info(_('Added sync for %s to task queue') % cds['id'])
