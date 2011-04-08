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

from pulp.server import async
from pulp.server.api.repo_sync import RepoSyncTask
from pulp.server.db.model.resource import Repo
from pulp.server.pexceptions import PulpException
from pulp.server.tasking.scheduler import IntervalScheduler
from pulp.server.tasking.task import task_complete_states

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

_explaination = _('''
Pulp repo schedules are maps or objects made up of the following three fields:
interval - map representing the time interval to perform the syncs on
start_time (optional) - map representing the date and time of the first sync
runs (optional) - integer representing the number of runs to perform, when omitted, schedule runs ad infinitum

interval allows the following fields, not all are required, but at least one must be present
weeks, days, hours, minutes

start_time requires the following fields:
year, month, day, hour, minute
''')

class InvalidScheduleError(PulpException):
    """
    Error raised on improperly formated schedules.
    Supplies an extensive explanation.
    """
    # XXX python 2.4 super() call is failing...
    pass
    #def __init__(self, msg, *args):
    #    msg += _explaination
    #    super(InvalidScheduleError, self).__init__(msg, *args)


def _validate_schedule(schedule):
    """
    Validate a passed in interval schedule.
    The schedule consists of a dictionary with and interval value, also a
    dictionary, and optional start_time and run fields. The start_time field
    is also a dictionary and runs is an integer. There's no return value, but
    an exception is raised if the schedule fails validation.
    @type schedule: dict
    @param schedule: dictionary representing an interval schedule
    @raise InvalidScheduleError: if the schedule fails validation
    """
    if not isinstance(schedule, (dict, BSON, SON)):
        raise InvalidScheduleError(_('Schedule must be an object'))
    interval = schedule.get('interval', None)
    if not interval:
        raise InvalidScheduleError(_('No interval present in schedule'))
    interval_keys = ('weeks', 'days', 'hours', 'minutes')
    for key, value in interval.items():
        if key not in interval_keys:
            raise InvalidScheduleError(_('Unknown interval field: %s') % key)
        if not isinstance(value, int):
            raise InvalidScheduleError(_('Value for %s must be an integer') % key)
    start_time = schedule.get('start_time', None)
    if start_time is not None:
        start_time_keys = ('year', 'month', 'day', 'hour', 'minute')
        for key in start_time_keys:
            if key not in start_time:
                raise InvalidScheduleError(_('Field %s is required for start_time') % key)
            if not isinstance(start_time[key], int):
                raise InvalidScheduleError(_('Value for %s must be an integer') % key)
        if len(start_time) != len(start_time_keys):
            raise InvalidScheduleError(_('Only fields: year, month, day, hour, and minute allowed'))
    runs = schedule.get('runs', None)
    if not isinstance(runs, (NoneType, int)):
        raise InvalidScheduleError(_('Value for runs must be an integer'))

# repo sync task management ---------------------------------------------------

def repo_schedule_to_scheduler(repo_schedule):
    """
    Convenience function to turn a serialized task schedule into an interval
    scheduler appropriate for scheduling a repo sync task.
    @type repo_schedule: L{pulp.server.db.model.resource.RepoSyncSchedule}
    @param repo_schedule: repo sync schedule to turn into interval scheduler
    @rtype: L{IntervalScheduler}
    @return: interval scheduler for the tasking sub-system
    """
    interval = repo_schedule['interval']
    interval = datetime.timedelta(weeks=interval.get('weeks', 0),
                                  days=interval.get('days', 0),
                                  hours=interval.get('hours', 0),
                                  minutes=interval.get('minutes', 0))
    start_time = repo_schedule.get('start_time', None)
    if start_time is not None:
        now = datetime.datetime.now()
        year = max(now.year, start_time.get('year', 0))
        month = max(now.month, start_time.get('month', 0))
        day = max(now.day, start_time.get('day', 0))
        hour = start_time.get('hour', now.hour)
        minute = start_time.get('minute', now.minute)
        start_time = datetime.datetime(year, month, day, hour, minute)
    runs = repo_schedule.get('runs', None)
    return IntervalScheduler(interval, start_time, runs)


def find_repo_scheduled_task(repo):
    """
    Look up a repo schedule task in the task sub-system for a given repo
    @type repo: L{pulp.server.db.model.resource.Repo}
    @param repo: repo to look up sync task for
    @rtype: None or L{pulp.server.tasking.task.Task}
    @return: the repo sync task associated the repo, None if no task is found
    """
    # NOTE this is very inefficient in the worst case: DO NOT CALL OFTEN!!
    # the number of sync tasks * (mean # arguments + mean # keyword arguments)
    id = repo['id']
    for task in async.find_async(method_name='_sync'):
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
    task.scheduler = repo_schedule_to_scheduler(repo['sync_schedule'])
    synchronizer = api.get_synchronizer(repo['source']['type'])
    task.set_synchronizer(synchronizer)
    async.enqueue(task)


def _update_repo_scheduled_sync_task(repo, task):
    """
    Update and existing repo sync task's schedule
    @type repo: L{pulp.server.db.model.resource.Repo}
    @param repo: repo to update sync task for
    @type task: L{pulp.server.tasking.task.Task}
    @param task: task to update
    """
    task.scheduler = repo_schedule_to_scheduler(repo['sync_schedule'])
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
    task = find_repo_scheduled_task(repo)
    if task is None:
        return
    async.remove_async(task)

# existing api ----------------------------------------------------------------

def update_schedule(repo, new_schedule):
    """
    Change a repo's sync schedule.
    @type repo: L{pulp.server.db.model.resource.Repo}
    @param repo: repo to change
    @type new_schedule: dict
    @param new_schedule: dictionary representing new schedule
    """
    _validate_schedule(new_schedule)
    repo['sync_schedule'] = new_schedule
    collection = Repo.get_collection()
    collection.save(repo, safe=True)
    task = find_repo_scheduled_task(repo)
    if task is None:
        _add_repo_scheduled_sync_task(repo)
    else:
        _update_repo_scheduled_sync_task(repo, task)


def delete_schedule(repo):
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

# startup initialization ------------------------------------------------------

def init_scheduled_syncs():
    """
    Iterate through all of the repos in the database and start sync tasks for
    those that have sync schedules associated with them.
    """
    collection = Repo.get_collection()
    for repo in collection.find({}):
        if repo['sync_schedule'] is None:
            continue
        _add_repo_scheduled_sync_task(repo)
