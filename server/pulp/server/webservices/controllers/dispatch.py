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

from pulp.server.async import tasks
from pulp.server.auth import authorization
from pulp.server.db.model.dispatch import QueuedCall
from pulp.server.dispatch import call, constants as dispatch_constants, factory as dispatch_factory
from pulp.server.dispatch import history as dispatch_history
from pulp.server.exceptions import MissingResource, PulpExecutionException
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required


class TaskNotFound(MissingResource):

    def __str__(self):
        return _('Task Not Found: %(id)s') % {'id': self.args[0]}


class TaskCancelNotImplemented(PulpExecutionException):

    http_status_code = httplib.NOT_IMPLEMENTED

    def __str__(self):
        return _('Cancel Not Implemented for Task: %(id)s') % {'id': self.args[0]}


class QueuedCallNotFound(MissingResource):

    def __str__(self):
        return _('Snapshot Not Found: %(id)s') % {'id': self.args[0]}


class TaskGroupNotFound(MissingResource):

    def __str__(self):
        return _('TaskGroup Not Found: %(id)s') % {'id': self.args[0]}


class TaskGroupCancelNotImplemented(PulpExecutionException):

    http_status_code = httplib.NOT_IMPLEMENTED

    def __str__(self):
        return _('Cancel Not Implemented for TaskGroup: %(id)s') % {'id': self.args[0]}

# task controllers -------------------------------------------------------------

class TaskCollection(JSONController):

    @auth_required(authorization.READ)
    def GET(self):
        valid_filters = ['tag', 'id']
        filters = self.filters(valid_filters)
        criteria = {'tags': filters.get('tag', [])}
        if 'id' in filters:
            criteria['call_request_id_list'] = filters['id']
        coordinator = dispatch_factory.coordinator()
        call_reports = coordinator.find_call_reports(**criteria)
        serialized_call_reports = [c.serialize() for c in call_reports]
        return self.ok(serialized_call_reports)


class TaskResource(JSONController):

    @auth_required(authorization.READ)
    def GET(self, call_request_id):
        link = serialization.link.link_obj('/pulp/api/v2/tasks/%s/' % call_request_id)
        coordinator = dispatch_factory.coordinator()
        call_reports = coordinator.find_call_reports(call_request_id=call_request_id)
        if call_reports:
            serialized_call_report = call_reports[0].serialize()
            serialized_call_report.update(link)
            return self.ok(serialized_call_report)
        archived_calls = dispatch_history.find_archived_calls(call_request_id=call_request_id)
        if archived_calls.count() > 0:
            serialized_call_report = archived_calls[0]['serialized_call_report']
            serialized_call_report.update(link)
            return self.ok(serialized_call_report)
        raise TaskNotFound(call_request_id)

    @auth_required(authorization.DELETE)
    def DELETE(self, call_request_id):
        coordinator = dispatch_factory.coordinator()
        result = coordinator.cancel_call(call_request_id)
        if result is None:
            # The coordinator doesn't know about the task, but Celery might. Let's tell Celery to
            # cancel it
            tasks.cancel(call_request_id)
            call_report = call.CallReport(call_request_id=call_request_id,
                                          state=dispatch_constants.CALL_CANCELED_STATE)
        elif result is False:
            raise TaskCancelNotImplemented(call_request_id)
        else:
            # if we've gotten here, the call request *should* exist
            call_report = coordinator.find_call_reports(call_request_id=call_request_id)[0]
        serialized_call_report = call_report.serialize()
        serialized_call_report.update(serialization.link.current_link_obj())
        return self.accepted(serialized_call_report)

# queued call controllers ------------------------------------------------------

class QueuedCallCollection(JSONController):

    @auth_required(authorization.READ)
    def GET(self):
        task_queue = dispatch_factory._task_queue()
        tasks = task_queue.all_tasks()
        queued_calls = []
        for t in tasks:
            data = {'task_id': t.id, 'queued_call_id': t.queued_call_id}
            data.update(serialization.link.child_link_obj(t.queued_call_id))
            queued_calls.append(data)
        return self.ok(queued_calls)


class QueuedCallResource(JSONController):

    @auth_required(authorization.READ)
    def GET(self, call_request_id):
        coordinator = dispatch_factory.coordinator()
        tasks = coordinator._find_tasks(call_request_id=call_request_id)
        if not tasks:
            raise QueuedCallNotFound(call_request_id)
        return self.ok(tasks[0].queued_call_id)

    @auth_required(authorization.DELETE)
    def DELETE(self, call_request_id):
        coordinator = dispatch_factory.coordinator()
        tasks = coordinator._find_tasks(call_request_id=call_request_id)
        if not tasks:
            raise QueuedCallNotFound(call_request_id)
        collection = QueuedCall.get_collection()
        collection.remove({'_id': tasks[0].queued_call_id}, safe=True)
        link = serialization.link.current_link_obj()
        return self.accepted(link)

# task_group controllers --------------------------------------------------------------

class TaskGroupCollection(JSONController):

    @auth_required(authorization.READ)
    def GET(self):
        call_request_group_ids = set()
        task_queue = dispatch_factory._task_queue()
        for task in task_queue.all_tasks():
            call_request_group_id = task.call_request.id
            if call_request_group_id is None:
                continue
            call_request_group_ids.add(call_request_group_id)
        task_group_links = []
        for id in call_request_group_ids:
            # continue to support legacy task ids
            link = {'task_group_id': id,
                    'call_request_group_id': id}
            link.update(serialization.link.child_link_obj(id))
            task_group_links.append(link)
        return self.ok(task_group_links)


class TaskGroupResource(JSONController):

    @auth_required(authorization.READ)
    def GET(self, call_request_group_id):
        link = serialization.link.link_obj('/pulp/api/v2/task_groups/%s/' % call_request_group_id)
        coordinator = dispatch_factory.coordinator()
        call_reports = coordinator.find_call_reports(call_request_group_id=call_request_group_id)
        found_call_request_ids = set(c.call_request_id for c in call_reports)
        serialized_call_reports = [c.serialize() for c in call_reports]
        archived_calls = dispatch_history.find_archived_calls(call_request_group_id=call_request_group_id)
        serialized_call_reports.extend(c['serialized_call_report'] for c in archived_calls
                                       if c['serialized_call_report']['call_request_id'] not in found_call_request_ids)
        if not serialized_call_reports:
            raise TaskGroupNotFound(call_request_group_id)
        map(lambda r: r.update(link), serialized_call_reports)
        return self.ok(serialized_call_reports)


    @auth_required(authorization.DELETE)
    def DELETE(self, call_request_group_id):
        coordinator = dispatch_factory.coordinator()
        results = coordinator.cancel_multiple_calls(call_request_group_id)
        if not results:
            raise TaskGroupNotFound(call_request_group_id)
        if reduce(lambda p, v: p and (v is None), results.values(), True):
            # in other words, all results values are None
            raise TaskGroupCancelNotImplemented(call_request_group_id)
        # if we've gotten this far, the call requests exist and have been cancelled
        call_reports = coordinator.find_call_reports(call_request_group_id=call_request_group_id)
        serialized_call_reports = [c.serialize() for c in call_reports]
        link = serialization.link.current_link_obj()
        for s in serialized_call_reports:
            s.update(link)
        return self.accepted(serialized_call_reports)

# web.py applications ----------------------------------------------------------

# mapped to /v2/tasks/

TASK_URLS = (
    '/', TaskCollection,
    '/([^/]+)/', TaskResource,
)

task_application = web.application(TASK_URLS, globals())

# mapped to /v2/queued_calls/

QUEUED_CALL_URLS = (
    '/', QueuedCallCollection,
    '/([^/]+)/', QueuedCallResource,
)

queued_call_application = web.application(QUEUED_CALL_URLS, globals())

# mapped to /v2/task_groups/

TASK_GROUP_URLS = (
    '/', TaskGroupCollection,
    '/([^/]+)/', TaskGroupResource,
)

task_group_application = web.application(TASK_GROUP_URLS, globals())
