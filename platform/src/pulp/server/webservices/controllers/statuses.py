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

from pulp.server.async import find_async
from pulp.server.api.repo import RepoApi
from pulp.server.auth.authorization import CREATE, READ, UPDATE, DELETE, EXECUTE
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler, collection_query)

api = RepoApi()

class StatusesCollection(JSONController):
    @error_handler
    @auth_required(READ)
    def GET(self):
        statuses_controller = Statuses()

        statuses = []
        for resource_type in statuses_controller.resource_types:
            _statuses = getattr(statuses_controller, resource_type)()
            if _statuses:
                statuses += _statuses

        return self.ok(statuses)

class Statuses(JSONController):
    resource_types = [ "repository" ]

    @error_handler
    @auth_required(READ)
    def GET(self, resource_type):
        response = self.ok(getattr(self, resource_type)())
        return response

    def repository(self):
        repository_statuses_controller = RepositoryStatuses()

        statuses = []
        for status_type in repository_statuses_controller.status_types:
            _statuses = getattr(repository_statuses_controller, status_type)()
            if _statuses:
                statuses += _statuses

        return statuses

class RepositoryStatuses(JSONController):

    status_types = [ "syncs", "clones" ]

    @error_handler
    @auth_required(READ)
    @collection_query("repoid", "state")
    def GET(self, status_type, spec={}):
        status_method = getattr(self, status_type)
        response = self.ok(status_method(spec))
        return response

    def clones(self, spec={}):
        pass

    def syncs(self, spec={}):
        """
        [[wiki]]
        title: Bulk List Repository Sync Status
        description: Get a list of the repository sync status for all
        repositories managed by Pulp.
        method: GET
        path: /statuses/repository/syncs/
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

        if "repoid" in spec:
            repos = api.repositories(dict(id=spec["repoid"]))
            repoids = [r["id"] for r in repos]
            repo_statuses = api.get_sync_status_for_repos(repos)

        if "state" in spec:
            states = spec["state"]
            if type(states) != type([]):
                states = [states]
            tasks = set()
            if 'all' in states:
                tasks.update(find_async(method_name="_sync"))
            if 'waiting' in states:
                tasks.update([t for t in find_async(method_name="_sync")
                    if t.state=='waiting'])
            if 'running' in states:
                tasks.update([t for t in find_async(method_name="_sync")
                    if t.state=='running'])
            if 'complete' in states:
                tasks.update([t for t in find_async(method_name="_sync")
                    if t.state=='complete'])
            if 'incomplete' in states:
                tasks.update([t for t in find_async(method_name="_sync")
                    if t.state=='incomplete'])
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

        statuses = [s for s in statuses if s["state"] is not None]

        return statuses
   
urls = (
    '/$', 'StatusesCollection',
    '/(%s)/' % '|'.join(Statuses.resource_types), 'Statuses',
    '/repository/(%s)/' % '|'.join(RepositoryStatuses.status_types),
        'RepositoryStatuses',
)

application = web.application(urls, globals())
