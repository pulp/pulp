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

from gettext import gettext as _
from types import NoneType

from pulp.server import async
from pulp.server.api.repo_sync import RepoSyncTask
from pulp.server.db.model.resource import Repo, RepoSyncSchedule
from pulp.server.pexceptions import PulpException
from pulp.server.tasking.scheduler import ImmediateScheduler
from pulp.server.tasking.task import task_running, task_complete_states

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
    def __init__(self, msg, *args):
        msg += _explaination
        super(InvalidScheduleError, self).__init__(msg, *args)


def _validate_schedule(schedule):
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

def _find_repo_scheduled_task(repo):
    # NOTE this is very inefficient in the worst case: DO NOT CALL OFTEN!!
    # the number of sync tasks * (mean # arguments + mean # keyword arguments)
    id = repo['id']
    for task in async.find_async(method_name='_sync'):
        if task.args and id in task.args or \
                task.kwargs and id in task.kwargs.values():
            return task
    return None


def _add_repo_scheduled_sync_task(repo):
    # hack to avoid circular import
    import pulp.server.api.repo.RepoApi as RepoApi
    api = RepoApi()
    task = RepoSyncTask(api._sync, [repo['id']])
    task.scheduler = RepoSyncSchedule.to_scheduler(repo['sync_schedule'])
    synchronizer = api.get_synchronizer(repo['source']['type'])
    task.set_synchronizer(synchronizer)
    async.enqueue(task)


def _update_repo_scheduled_sync_task(repo, task):
    task.scheduler = RepoSyncSchedule.to_scheduler(repo['sync_schedule'])
    if task.state not in task_complete_states:
        return
    async.remove_async(task)
    async.enqueue(task)


def _remove_repo_scheduled_sync_task(repo):
    task = _find_repo_scheduled_task(repo)
    if task is None:
        return
    async.remove_async(task)

# existing api ----------------------------------------------------------------

def update_schedule(repo, new_schedule):
    _validate_schedule(new_schedule)
    repo['sync_schedule'] = new_schedule
    collection = Repo.get_collection()
    collection.save(repo, safe=True)
    task = _find_repo_scheduled_task(repo)
    if task is None:
        _add_repo_scheduled_sync_task(repo)
    else:
        _update_repo_scheduled_sync_task(repo, task)


def delete_schedule(repo):
    if repo['sync_schedule'] is None:
        return
    repo['sync_schedule'] = None
    collection = Repo.get_collection()
    collection.save(repo, safe=True)
    _remove_repo_scheduled_sync_task(repo)

# startup initialization ------------------------------------------------------

def init_scheduled_syncs():
    collection = Repo.get_collection()
    for repo in collection.find({}):
        if repo['sync_schedule'] is None:
            continue
        _add_repo_scheduled_sync_task(repo)
