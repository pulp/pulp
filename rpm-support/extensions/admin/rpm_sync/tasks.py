# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Functions for working with sync/publish tasks in the server.
"""

from pulp.common import tags


def relevant_existing_task_id(existing_sync_tasks):
    """
    Analyzes the list of existing sync tasks to determine which should be
    tracked by the CLI.

    @param existing_sync_tasks: list of task instances retrieved from the server
    @type  existing_sync_tasks: list

    @return: ID of the task that should be displayed
    @rtype:  str
    """

    # At this point, we have at least one sync task but that doesn't
    # mean it's running yet. It shouldn't, however, be completed as
    # it wouldn't come back in the lookup. That should leave two
    # possibilities: waiting or running.
    #
    # There will only be one running, so that case is easy: if we find
    # a running task start displaying it.
    #
    # If there are no running tasks, the waiting ones are ordered such
    # that the first one will execute next, so use that task ID and
    # start the display process (it will handle waiting accordingly.

    running_tasks = [t for t in existing_sync_tasks if t.is_running()]
    waiting_tasks = [t for t in existing_sync_tasks if t.is_waiting()]

    if running_tasks:
        return running_tasks[0].task_id
    elif waiting_tasks:
        return waiting_tasks[0].task_id

    return None


def relevant_existing_task_group_id(existing_sync_tasks):
    """
    Grok through a list of existing sync tasks and look for the task_group_id
    for the highest priority sync.

    @param existing_sync_tasks:
    @return:
    """
    running_tasks = [t for t in existing_sync_tasks if t.is_running()]
    waiting_tasks = [t for t in existing_sync_tasks if t.is_waiting()]

    if running_tasks:
        return running_tasks[0].task_group_id
    elif waiting_tasks:
        return waiting_tasks[0].task_group_id

    return None


def sync_task_in_sync_task_group(task_list):
    """
    Grok through the tasks returned from the server's repo sync call and find
    the task that pertains to the sync itself.

    @param task_list: list of tasks
    @type task_list: list
    @return: task for the sync
    @rtype: Task
    """
    sync_tag = tags.action_tag(tags.ACTION_SYNC_TYPE)
    for t in task_list:
        if sync_tag in t.tags:
            return t
    return None


def publish_task_in_sync_task_group(task_list):
    """
    Grok through the tasks returned from the server's repo sync call and find
    the task that pertains to the auto publish.

    @param task_list: list of tasks
    @type task_list: list
    @return: task for the publish
    @rtype: Task
    """
    publish_tag = tags.action_tag(tags.ACTION_AUTO_PUBLISH_TYPE)
    for t in task_list:
        if publish_tag in t.tags:
            return t
    return None


