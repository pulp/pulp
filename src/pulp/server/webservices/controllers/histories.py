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

from pulp.server.api.repo import RepoApi
from pulp.server.api import task_history
from pulp.server.auth.authorization import CREATE, READ, UPDATE, DELETE, EXECUTE
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler, collection_query)

api = RepoApi()

class HistoriesCollection(JSONController):
    @error_handler
    @auth_required(READ)
    def GET(self):
        history = History()

        histories = []
        for resource_type in history.resource_types:
            _histories = getattr(history, resource_type)()
            if _histories:
                histories += _histories

        return self.ok(histories)


class History(JSONController):
    resource_types = [ "repository" ]

    @error_handler
    @auth_required(READ)
    def GET(self, resource_type):
        response = self.ok(getattr(self, resource_type)())
        return response

    def repository(self):
        repository_history = RepositoryHistory()
        
        history_methods = [getattr(repository_history, ht)
            for ht in repository_history.history_types]

        histories = []
        for history_method in history_methods:
            _histories = history_method()
            if _histories:
                histories += _histories

        return histories


class RepositoryHistory(JSONController):

    history_types = [ "syncs", "clones" ]

    @error_handler
    @auth_required(READ)
    @collection_query("repoid")
    def GET(self, history_type, spec={}):
        history_method = getattr(self, history_type)
        histories = history_method(spec)
        return self.ok(histories)

    def syncs(self, spec={}):
        sync_histories = task_history.all_repo_sync() 
        
        if spec:
            repoid = spec.get("repoid", [])
            if repoid:
                if type(repoid) == type({}):
                    repoid = repoid.get("$in", [])
                sync_histories = [sh for sh in sync_histories
                    if sh["args"][0] in repoid]

        return sync_histories

    def clones(self):
        pass


urls = (
    '/$', 'HistoriesCollection',
    '/(%s)/' % '|'.join(History.resource_types), 'History',
    '/repository/(%s)/' % '|'.join(RepositoryHistory.history_types),
        'RepositoryHistory',
)

application = web.application(urls, globals())
