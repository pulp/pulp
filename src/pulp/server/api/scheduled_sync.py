# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import datetime
from gettext import gettext as _
from types import NoneType

try:
    from bson import BSON, SON
except ImportError:
    from pymongo.bson import BSON
    from pymongo.son import SON

from pulp.common import dateutils
from pulp.server import async
from pulp.server.api.repo_sync import RepoSyncTask
from pulp.server.db.model.cds import CDS, CDSSyncSchedule
from pulp.server.db.model.resource import Repo, RepoSyncSchedule
from pulp.server.pexceptions import PulpException
from pulp.server.tasking.scheduler import IntervalScheduler
from pulp.server.tasking.task import task_complete_states, Task

# convenience methods for schedule reporting ----------------------------------

def task_scheduled_time_to_dict(task):
    """
    Convert a task's scheduled time field into a dictionary for easy reporting.
    @type task: L{pulp.server.tasking.task.Task}
    @param task: task to convert scheduled time of
    @rtype: None or dict
    @return: a dictionary representing the task's scheduled time,
             None if the task is not scheduled
    """
    if task.scheduled_time is None:
        return None
    return dict([(k, getattr(task.scheduled_time, k))
                  for k in ('year', 'month', 'day', 'hour', 'minute')
                  if getattr(task.scheduled_time, k)])

# schedule validation ---------------------------------------------------------

def _parse_repo_schedule(schedule_str):
    i, s, r = dateutils.parse_iso8601_interval(schedule_str)
    return RepoSyncSchedule(i, s, r)


def _parse_cds_schedule(schedule_str):
    i, s, r = dateutils.parse_iso8601_interval(schedule_str)
    return CDSSyncSchedule(i, s, r)

# sync task management ---------------------------------------------------

def schedule_to_scheduler(schedule):
    """
    Convenience function to turn a serialized task schedule into an interval
    scheduler appropriate for scheduling a sync task.
    @type schedule: L{pulp.server.db.model.resource.RepoSyncSchedule} or
                    L{pulp.server.db.model.cds.CDSSyncSchedule}
    @param schedule: sync schedule to turn into interval scheduler
    @rtype: L{IntervalScheduler}
    @return: interval scheduler for the tasking sub-system
    """
    interval = schedule['interval']
    interval = datetime.timedelta(weeks=interval.get('weeks', 0),
                                  days=interval.get('days', 0),
                                  hours=interval.get('hours', 0),
                                  minutes=interval.get('minutes', 0))
    start_time = schedule.get('start_time', None)
    if start_time is not None:
        now = datetime.datetime.now(dateutils.local_tz())
        year = max(now.year, start_time.get('year', 0))
        month = max(now.month, start_time.get('month', 0))
        day = max(now.day, start_time.get('day', 0))
        hour = start_time.get('hour', now.hour)
        minute = start_time.get('minute', now.minute)
        start_time = datetime.datetime(year, month, day, hour, minute, tzinfo=dateutils.local_tz())
    runs = schedule.get('runs', None)
    return IntervalScheduler(interval, start_time, runs)


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
        if task.args and id in task.args or \
                task.kwargs and id in task.kwargs.values():
            return task
    return None


def _add_repo_scheduled_sync_task(repo):
    """
    Add a new repo sync task for the given repo
    @type repo: L{pulp.server.db.model.resource.Repo}
    @param repo: repo to add sync task for
    """
    # hack to avoid circular import
    from pulp.server.api.repo import RepoApi
    api = RepoApi()
    task = RepoSyncTask(api._sync, [repo['id']])
    task.scheduler = schedule_to_scheduler(repo['sync_schedule'])
    synchronizer = api.get_synchronizer(repo['source']['type'])
    task.set_synchronizer(synchronizer)
    async.enqueue(task)


def _add_cds_scheduled_sync_task(cds):
    from pulp.server.api.cds import CdsApi
    api = CdsApi()
    task = Task(api.cds_sync, [cds['hostname']])
    task.scheduler = schedule_to_scheduler(cds['sync_schedule'])
    async.enqueue(task)


def _update_repo_scheduled_sync_task(repo, task):
    """
    Update and existing repo sync task's schedule
    @type repo: L{pulp.server.db.model.resource.Repo}
    @param repo: repo to update sync task for
    @type task: L{pulp.server.tasking.task.Task}
    @param task: task to update
    """
    task.scheduler = schedule_to_scheduler(repo['sync_schedule'])
    if task.state not in task_complete_states:
        return
    async.remove_async(task)
    async.enqueue(task)


def _update_cds_scheduled_sync_task(cds, task):
    task.scheduler = schedule_to_scheduler(cds['sync_schedule'])
    if task.state not in task_complete_states:
        return
    async.remove_async(task)
    async.enqueue(task)


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

# existing api ----------------------------------------------------------------

def update_repo_schedule(repo, new_schedule):
    """
    Change a repo's sync schedule.
    @type repo: L{pulp.server.db.model.resource.Repo}
    @param repo: repo to change
    @type new_schedule: dict
    @param new_schedule: dictionary representing new schedule
    """
    repo['sync_schedule'] = _parse_repo_schedule(new_schedule)
    collection = Repo.get_collection()
    collection.save(repo, safe=True)
    task = find_scheduled_task(repo['id'], '_sync')
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
    repo['sync_schedule'] = None
    collection = Repo.get_collection()
    collection.save(repo, safe=True)
    _remove_repo_scheduled_sync_task(repo)

def update_cds_schedule(cds, new_schedule):
    '''
    Change a CDS sync schedule.
    '''
    cds['sync_schedule'] = _parse_cds_schedule(new_schedule)
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

# startup initialization ------------------------------------------------------

def init_scheduled_syncs():
    """
    Iterate through all of the repos in the database and start sync tasks for
    those that have sync schedules associated with them.
    """
    _init_repo_scheduled_syncs()
    _init_cds_scheduled_syncs()

def _init_repo_scheduled_syncs():
    collection = Repo.get_collection()
    for repo in collection.find({}):
        if repo['sync_schedule'] is None:
            continue
        _add_repo_scheduled_sync_task(repo)

def _init_cds_scheduled_syncs():
    collection = CDS.get_collection()
    for cds in collection.find({}):
        if cds['sync_schedule'] is None:
            continue
        _add_cds_scheduled_sync_task(cds)
