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

from pulp.gc_client.api.base import PulpAPI
from pulp.gc_client.api.responses import Task

class TasksAPI(PulpAPI):

    def __init__(self, pulp_connection):
        super(TasksAPI, self).__init__(pulp_connection)

    def get_task(self, task_id):
        """

        """
        path = '/v2/tasks/%s/' % task_id
        response = self.server.GET(path)

        # Since it was a 200, the connection parsed the response body into a
        # Document. We know this will be task data, so convert the object here.
        response.response_body = Task(response.response_body)
        return response

    def get_all_tasks(self):
        """
        Returns a list of all queued tasks in the server. Each task is described

        """
        path = '/v2/tasks/'
        response = self.server.GET(path)

        tasks = []
        for doc in response.response_body:
            tasks.append(Task(doc))

        response.response_body = tasks
        return response

    def get_repo_tasks(self, repo_id):
        """

        """
        pass