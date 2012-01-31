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

import web
import logging
from gettext import gettext as _
from pulp.server import async
from pulp.server.tasking.task import task_waiting as WAITING
from pulp.server.tasking.task import task_running as RUNNING
from pulp.server.tasking.task import task_suspended as SUSPENDED
from pulp.server.api import task_history
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.auth.authorization import READ, UPDATE
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler)

log = logging.getLogger('pulp')


# utils ----------------------------------------------------------------------



# jobs controller -------------------------------------------------------------


class JobController(JSONController):

    def active(self, id, states=[]):
        tasks = {}
        for task in async.find_async(job_id=id):
            if states and task.state not in states:
                continue
            task_dict = self._task_to_dict(task)
            tasks[task.id] = (task, task_dict)
        return tasks


class Jobs(JobController):

    @error_handler
    @auth_required(READ)
    def GET(self):
        jobs = {}
        for task in async.all_async():
            job_id = task.job_id
            if  job_id is None:
                continue
            job = jobs.get(job_id)
            if job is None:
                tasks = []
                job = dict(id=job_id, tasks=tasks)
                jobs[job_id] = job
                t = self._task_to_dict(task)
            tasks.append(t)
        return self.ok(jobs.values())


class Job(JobController):

    @error_handler
    @auth_required(READ)
    def GET(self, id):
        tasks = self.active(id)
        for task in task_history.job(id):
            tid = task['id']
            if tid in tasks:
                continue
            tasks[tid] = task
        tasks = self.active(id)
        if not tasks:
            return self.not_found(_('job %s, not-found') % id)
        job = {}
        job['id'] = id
        job['tasks'] = [t[1] for t in tasks.values()]
        return self.ok(job)


class Cancel(JobController):

    @error_handler
    @auth_required(UPDATE)
    def POST(self, id):
        history = []
        filter = (WAITING, RUNNING, SUSPENDED)
        active = self.active(id, filter)
        for task in task_history.job(id):
            if task['id'] in active:
                continue
            history.append(task)
        active = active.values()
        for task in active:
            async.cancel_async(task[0])
        if not history and not active:
            return self.not_found(_('job %s, not-found') % id)
        result = dict(id=id,
                      completed=history,
                      cancelled=[t[1] for t in active])
        return self.accepted(result)            

# web.py application -----------------------------------------------------------

_urls = (
    '/$', Jobs,
    '/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/$', Job,
    '/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/cancel/$', Cancel,
)

application = web.application(_urls, globals())
