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


import httplib
from gettext import gettext as _

import web

from pulp.common.error_codes import PLP0023
from pulp.server.async import tasks
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.auth import authorization
from pulp.server.db.model.criteria import Criteria
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.exceptions import MissingResource, PulpCodedException
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required

# task controllers -------------------------------------------------------------

class TaskCollection(JSONController):

    @auth_required(authorization.READ)
    def GET(self):
        valid_filters = ['tag']
        filters = self.filters(valid_filters)
        criteria_filters = {}
        tags = filters.get('tag', [])
        if tags:
            criteria_filters['tags'] = {'$all':  filters.get('tag', [])}
        criteria = Criteria.from_client_input({'filters': criteria_filters})
        serialized_task_statuses = []
        for task in TaskStatusManager.find_by_criteria(criteria):
            task.update(serialization.dispatch.spawned_tasks(task))
            serialized_task_statuses.append(task)
        return self.ok(serialized_task_statuses)


class TaskResource(JSONController):

    @auth_required(authorization.READ)
    def GET(self, task_id):
        task = TaskStatusManager.find_by_task_id(task_id)
        if task is None:
            raise MissingResource(task_id)
        else:
            link = serialization.link.link_obj('/pulp/api/v2/tasks/%s/' % task_id)
            task.update(link)
            task.update(serialization.dispatch.spawned_tasks(task))
            return self.ok(task)

    @auth_required(authorization.DELETE)
    def DELETE(self, task_id):
        """
        Cancel the task that is represented by the given task_id, unless it is already in a complete state.

        :param task_id: The ID of the task you wish to cancel
        :type  task_id: basestring
        """
        tasks.cancel(task_id)
        return self.ok(None)

# web.py applications ----------------------------------------------------------

# mapped to /v2/tasks/

TASK_URLS = (
    '/', TaskCollection,
    '/([^/]+)/', TaskResource,
)

task_application = web.application(TASK_URLS, globals())
