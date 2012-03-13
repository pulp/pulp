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
from pulp.gc_client.api.server import AsyncResponse

class TasksAPI(PulpAPI):

    def __init__(self, pulp_connection):
        super(TasksAPI, self).__init__(pulp_connection)

    def lookup_async_task(self, task_id):
        """
        Unlike other retrieval calls, instead of returning a Response object,
        an AsyncResponse object is returned instead. This is to facilitate
        a single block of code that handles both the original async response
        from a call that returns it and subsequent calls to this method to
        poll the task.

        @rtype: AsyncResponse
        """
        path = '/v2/tasks/%s/' % task_id
        normal_response = self.server.GET(path)
        async_response = AsyncResponse(normal_response.response_code, normal_response.response_body)
        return async_response
