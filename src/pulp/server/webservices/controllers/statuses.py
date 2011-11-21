# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
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

from pulp.server import async
from pulp.server.api.repo import RepoApi
from pulp.server.auth.authorization import CREATE, READ, UPDATE, DELETE, EXECUTE
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler, collection_query)

api = RepoApi()

class StatusesCollection(JSONController):
    pass

class Statuses(JSONController):
    resource_types = {"repositories" : "repositories"}

    @error_handler
    @auth_required(READ)
    def GET(self, resource_type):
        response = self.ok(getattr(self,
            self.resource_types[resource_type])()) 
        return response

    def repositories(self):
        repository_statuses_controller = RepositoryStatuses()

        status_methods = [getattr(repository_statuses_controller, st)
            for st in repository_statuses_controller.status_types]

        statuses = []
        for status_method in status_methods:
            _statuses = status_method()
            if _statuses:
                statuses.append(_statuses)

        return statuses

class RepositoryStatuses(JSONController):

    status_types = { "sync" : "sync",
                     "clone" : "clone" }

    @error_handler
    @auth_required(READ)
    @collection_query("id", "state")
    def GET(self, status_type, spec={}):
        status_method = getattr(self, self.status_types[status_type], None)

        if status_method:
            response = self.ok(status_method(spec))
        else:
            response = self.not_found(_("Invalid status type %s.") %
                status_type)

        return response

    def clone(self, spec={}):
        pass

    def sync(self, spec={}):
        """
        [[wiki]]
        title: Bulk List Repository Sync Status
        description: Get a list of the repository sync status for all
        repositories managed by Pulp.
        method: GET
        path: /repo_sync_status/
        permission: READ
        success response: 200 OK
        failure response: None
        return list of Repo Sync Status objects, possibly empty
        filters:
         * id, str, repository id
         * state, str, sync status state, such as running, waiting, or error
        """
        repo_statuses = []
        task_statuses = []
        repoids = []
        states = []

        if "id" in spec:
            repos = api.repositories(dict(id=spec["id"]))
            repoids = [r["id"] for r in repos]
            repo_statuses = api.get_sync_status_for_repos(repos)

        if "state" in spec:
            states = spec["state"]
            if type(states) != type([]):
                states = [states]
            tasks = set()
            if not states or 'all' in states:
                tasks.update(async.all_async())
            if 'waiting' in states:
                tasks.update(async.waiting_async())
            if 'running' in states:
                tasks.update(async.running_async())
            if 'complete' in states:
                tasks.update(async.complete_async())
            if 'incomplete' in states:
                tasks.update(async.incomplete_async())
            if 'error' in states:
                pass

            task_statuses = api.get_sync_status_by_tasks(tasks)

        if repoids and states:
            statuses = [rs for rs in repo_statuses if rs["state"] in states]
        elif repoids or states:
            statuses = repo_statuses or task_statuses
        else:
            repos = api.repositories()
            statuses = api.get_sync_status_for_repos(repos)

        return statuses
   
urls = (
    '/$', 'StatusesCollection',
    '/(%s)/' % '|'.join(Statuses.resource_types.keys()), 'Statuses',
    '/repositories/(%s)/' % '|'.join(RepositoryStatuses.status_types.keys()),
        'RepositoryStatuses',
)

application = web.application(urls, globals())
