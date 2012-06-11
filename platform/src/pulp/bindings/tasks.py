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

import pulp.common.tags as tag_util
from pulp.bindings.base import PulpAPI
from pulp.bindings.responses import Task


class TasksAPI(PulpAPI):

    def __init__(self, pulp_connection):
        super(TasksAPI, self).__init__(pulp_connection)

    def cancel_task(self, task_id):
        """
        Cancels the given task. The task must either be an operation on the
        server that supports cancelling or it must not have begun to execute
        yet.

        @param task_id: ID retrieved
        @return:
        """
        path = '/v2/tasks/%s/' % task_id
        response = self.server.DELETE(path)
        return response

    def get_task(self, task_id):
        """
        Retrieves the status of the given task if it exists.

        @return: response with a Task object in the response_body
        @rtype:  Response

        @raise NotFoundException: if there is no task with the given ID
        """
        path = '/v2/tasks/%s/' % task_id
        response = self.server.GET(path)

        # Since it was a 200, the connection parsed the response body into a
        # Document. We know this will be task data, so convert the object here.
        response.response_body = Task(response.response_body)
        return response

    def get_all_tasks(self, tags=()):
        """
        Retrieves all tasks in the system. If tags are specified, only tasks
        that contain all of the given tags are returned. All tasks will be
        represented by Task objects in a list in the response's response_body
        attribute.

        @param tags: if specified, only tasks that contain all tags in the given
                     list are returned; None to return all tasks
        @type  tags: list

        @return: response with a list of Task objects; empty list for no matching tasks
        @rtype:  Response
        """
        path = '/v2/tasks/'
        tags = [('tag', t) for t in tags]

        response = self.server.GET(path, queries=tags)

        tasks = []
        for doc in response.response_body:
            tasks.append(Task(doc))

        response.response_body = tasks
        return response

    def get_repo_tasks(self, repo_id):
        """
        Retrieves all tasks for the given repository.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @return: response with a list of Task objects; empty list for no matching tasks
        @rtype:  Response
        """
        repo_tag = tag_util.resource_tag(tag_util.RESOURCE_REPOSITORY_TYPE, repo_id)
        return self.get_all_tasks(tags=[repo_tag])

    def get_repo_sync_tasks(self, repo_id):
        """
        Retrieves all sync tasks for the given repository.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @return: response with a list of Task objects; empty list for no matching tasks
        @rtype:  Response
        """
        repo_tag = tag_util.resource_tag(tag_util.RESOURCE_REPOSITORY_TYPE, repo_id)
        sync_tag = tag_util.action_tag(tag_util.ACTION_SYNC_TYPE)
        return self.get_all_tasks(tags=[repo_tag, sync_tag])

    def get_repo_publish_tasks(self, repo_id):
        """
        Retrieves all publish tasks for the given repository.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @return: response with a list of Task objects; empty list for no matching tasks
        @rtype:  Response
        """
        repo_tag = tag_util.resource_tag(tag_util.RESOURCE_REPOSITORY_TYPE, repo_id)
        publish_tag = tag_util.action_tag(tag_util.ACTION_PUBLISH_TYPE)
        return self.get_all_tasks(tags=[repo_tag, publish_tag])

