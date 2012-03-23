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

# Python
import logging

# 3rd Party
import web

# Pulp
import pulp.server.managers.factory as managers
from pulp.server.auth.authorization import READ, CREATE, UPDATE, DELETE
from pulp.server.webservices import execution
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- controllers --------------------------------------------------------------

class Consumers(JSONController):

    @auth_required(READ)
    def GET(self):
        return self.ok([])

    @auth_required(CREATE)
    def POST(self):
        return self.ok()


class Consumer(JSONController):

    @auth_required(READ)
    def GET(self, id):
        return self.ok({})

    @auth_required(UPDATE)
    def PUT(self, id):
        return self.ok()

    @auth_required(DELETE)
    def DELETE(self, id):
        return self.ok()


class Bindings(JSONController):

    @auth_required(READ)
    def GET(self, consumer_id):
        manager = managers.consumer_bind_manager()
        bindings = manager.find_by_consumer(consumer_id)
        return self.ok(bindings)

    @auth_required(CREATE)
    def POST(self, consumer_id):
        body = self.params()
        repo_id = body.get('repo_id')
        distributor_id = body.get('distributor_id')
        resources = {
            dispatch_constants.RESOURCE_CONSUMER_TYPE:
                {consumer_id:dispatch_constants.RESOURCE_READ_OPERATION},
            dispatch_constants.RESOURCE_REPOSITORY_TYPE:
                {repo_id:dispatch_constants.RESOURCE_READ_OPERATION},
            dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE:
                {distributor_id:dispatch_constants.RESOURCE_READ_OPERATION},
        }
        args = [
            consumer_id,
            repo_id,
            distributor_id,
        ]
        manager = managers.consumer_bind_manager()
        call_request = CallRequest(
            manger.bind,
            args,
            resources=resources,
            weight=0)
        return execution.execute_sync_created(self, call_request, id)
        return self.ok()


class Binding(JSONController):

    @auth_required(READ)
    def GET(self, consumer_id, repo_id, distributor_id):
        return self.ok({})

    @auth_required(UPDATE)
    def PUT(self, consumer_id, repo_id, distributor_id):
        return self.ok()

    @auth_required(DELETE)
    def DELETE(self, consumer_id, repo_id, distributor_id):
        return self.ok()


# -- web.py application -------------------------------------------------------

urls = (
    '/$', 'Consumers',
    '/([^/]+)/$', 'Consumer',
    '/([^/]+)/bindings/$', 'Bindings',
    '/([^/]+)/bindings/([^/]+)/([^/]+)/$', 'Binding',
)

application = web.application(urls, globals())
