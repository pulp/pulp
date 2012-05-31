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
import logging
from gettext import gettext as _

import web

from pulp.server.auth import authorization
from pulp.server.db.model.dispatch import QueuedCall
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.dispatch import history as dispatch_history
from pulp.server.exceptions import MissingResource, PulpExecutionException
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required

# globals ----------------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# exceptions -------------------------------------------------------------------

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


class JobNotFound(MissingResource):

    def __str__(self):
        return _('Job Not Found: %(id)s') % {'id': self.args[0]}


class JobCancelNotImplemented(PulpExecutionException):

    http_status_code = httplib.NOT_IMPLEMENTED

    def __str__(self):
        return _('Cancel Not Implemented for Job: %(id)s') % {'id': self.args[0]}

# task controllers -------------------------------------------------------------

class TaskCollection(JSONController):

    @auth_required(authorization.READ)
    def GET(self):
        valid_filters = ['tag']
        filters = self.filters(valid_filters)
        criteria = {'tags': filters.get('tag', [])}
        coordinator = dispatch_factory.coordinator()
        call_reports = coordinator.find_call_reports(**criteria)
        serialized_call_reports = [c.serialize() for c in call_reports]
        return self.ok(serialized_call_reports)


class TaskResource(JSONController):

    @auth_required(authorization.READ)
    def GET(self, task_id):
        link = serialization.link.link_obj('/pulp/api/v2/tasks/%s/' % task_id)
        coordinator = dispatch_factory.coordinator()
        call_reports = coordinator.find_call_reports(task_id=task_id)
        if call_reports:
            serialized_call_report = call_reports[0].serialize()
            serialized_call_report.update(link)
            return self.ok(serialized_call_report)
        archived_calls = dispatch_history.find_archived_calls(task_id=task_id)
        if archived_calls.count() > 0:
            serialized_call_report = archived_calls[0]['serialized_call_report']
            serialized_call_report.update(link)
            return self.ok(serialized_call_report)
        raise TaskNotFound(task_id)

    @auth_required(authorization.DELETE)
    def DELETE(self, task_id):
        coordinator = dispatch_factory.coordinator()
        result = coordinator.cancel_call(task_id)
        if result is None:
            raise MissingResource(task_id)
        if result is False:
            raise TaskCancelNotImplemented(task_id)
        link = serialization.link.current_link_obj()
        return self.accepted(link)

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
    def GET(self, task_id):
        coordinator = dispatch_factory.coordinator()
        tasks = coordinator.find_tasks(task_id=task_id)
        if not tasks:
            raise QueuedCallNotFound(task_id)
        return self.ok(tasks[0].queued_call_id)

    @auth_required(authorization.DELETE)
    def DELETE(self, task_id):
        coordinator = dispatch_factory.coordinator()
        tasks = coordinator.find_tasks(task_id=task_id)
        if not tasks:
            raise QueuedCallNotFound(task_id)
        collection = QueuedCall.get_collection()
        collection.remove({'_id': tasks[0].queued_call_id}, safe=True)
        link = serialization.link.current_link_obj()
        return self.accepted(link)

# job controllers --------------------------------------------------------------

class JobCollection(JSONController):

    @auth_required(authorization.READ)
    def GET(self):
        job_ids = set()
        task_queue = dispatch_factory._task_queue()
        for task in task_queue.all_tasks():
            job_id = task.call_report.job_id
            if job_id is None:
                continue
            job_ids.add(job_id)
        job_links = []
        for id in job_ids:
            link = {'job_id': id}
            link.update(serialization.link.child_link_obj(id))
            job_links.append(link)
        return self.ok(job_links)


class JobResource(JSONController):

    @auth_required(authorization.READ)
    def GET(self, job_id):
        coordinator = dispatch_factory.coordinator()
        call_reports = coordinator.find_call_reports(job_id=job_id)
        serialized_call_reports = [c.serialize() for c in call_reports]
        archived_calls = dispatch_history.find_archived_calls(job_id=job_id)
        serialized_call_reports.extend(c['serialized_call_report'] for c in archived_calls)
        if not serialized_call_reports:
            raise JobNotFound(job_id)
        return self.ok(serialized_call_reports)


    @auth_required(authorization.DELETE)
    def DELETE(self, job_id):
        coordinator = dispatch_factory.coordinator()
        results = coordinator.cancel_multiple_calls(job_id)
        if not results:
            raise JobNotFound(job_id)
        if None in results.values():
            raise JobCancelNotImplemented(job_id)
        return self.accepted(results)

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

# mapped to /v2/jobs/

JOB_URLS = (
    '/', JobCollection,
    '/([^/]+)/', JobResource,
)

job_application = web.application(JOB_URLS, globals())

