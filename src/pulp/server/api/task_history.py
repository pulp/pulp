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

import itertools

from pulp.common import dateutils
from pulp.server.api.repo_sync_task import RepoSyncTask
from pulp.server.db.model.persistence import TaskHistory


def _finish_time_cmp(one, two):
    """
    Utility function for comparing the finish time of two task history
    instances.
    """
    return cmp(dateutils.parse_iso8601_datetime(one['finish_time']),
               dateutils.parse_iso8601_datetime(two['finish_time']))


def all_repo_sync():
    """
    Return a list of all the finished repo syncs.
    Note: this does not include any waiting or currently running syncs.
    @rtype: list of R{TaskHistory} instances.
    @return: a list of the finished repo syncs.
    """
    history = []
    collection = TaskHistory.get_collection()
    history = collection.find({'task_type': RepoSyncTask.__name__})
    return sorted(history, cmp=_finish_time_cmp, reverse=True)

def repo_sync(id):
    """
    Return a list of all the finished repo syncs for the given repo id.
    Note: this does not include any waiting or currently running syncs.
    @type id: str
    @param id: repo id
    @rtype: list of R{TaskHistory} instances
    @return: a list of the finished repo syncs for the given repo id
    """
    history = []
    collection = TaskHistory.get_collection()
    # Filter the TaskHistory collection by task_type and by args.  A single
    # item list of the repo id should always be the value of args for repo
    # syncs.
    history = collection.find({'task_type': RepoSyncTask.__name__,
        'args': [id]})
    return sorted(history, cmp=_finish_time_cmp, reverse=True)


def cds_sync(hostname):
    """
    Return a list of all of the finished CDS syncs for the given CDS hostname.
    Note: this does not include any waiting or currently running syncs.
    @type hostname: str
    @param hostname: name of the CDS host
    @rtype: list of R{TaskHistory} instances
    @return: a list of the finished CDS syncs for the given CDS hostname
    """
    history = []
    collection = TaskHistory.get_collection()
    spec = {'class_name': 'CdsApi', 'method_name': 'cds_sync'}
    for task in collection.find(spec):
        if hostname not in task['args']:
            continue
        history.append(task)
    return sorted(history, cmp=_finish_time_cmp, reverse=True)


def task(id):
    """
    Find a task by id.
    @type id: str
    @param id: job id
    @rtype: dict
    @return: task
    """
    collection = TaskHistory.get_collection()
    return collection.find({'id':id})


def job(id):
    """
    Find tasks by job id.
    @type id: str
    @param id: job id
    @rtype: List of R{TaskHistory}
    @return: A list of tasks.
    """
    history = []
    collection = TaskHistory.get_collection()
    for task in collection.find({'job_id':id}):
        history.append(task)
    return history
