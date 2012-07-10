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
from pulp.common.tags import action_tag, resource_tag
from pulp.server import config as pulp_config
import pulp.server.managers.factory as managers
from pulp.server.auth.authorization import READ, CREATE, UPDATE, DELETE
from pulp.server.webservices import execution
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices import serialization


# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- controllers --------------------------------------------------------------

class UsersCollection(JSONController):

    # Scope: Collection
    # GET:   Retrieves all users
    # POST:  Adds a user

    @auth_required(READ)
    def GET(self):

        manager = managers.user_manager()
        users = manager.find_all()

        return self.ok(users)

    @auth_required(CREATE)
    def POST(self):

        # Pull all the user data
        user_data = self.params()
        login = user_data.get('login', None)
        password = user_data.get('password', None)
        name = user_data.get('name', None)
        roles = user_data.get('roles', None)
        _LOG.info("$$$$$$$$$$$ %s : %s" % (login, name))

        # Creation
        manager = managers.user_manager()
        resources = {dispatch_constants.RESOURCE_USER_TYPE: {login: dispatch_constants.RESOURCE_CREATE_OPERATION}}
        args = [login, password, name, roles]
        weight = pulp_config.config.getint('tasks', 'create_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_USER_TYPE, login),
                action_tag('create')]
        call_request = CallRequest(manager.create_user,
                                   args,
                                   resources=resources,
                                   weight=weight,
                                   tags=tags)
        return execution.execute_sync_created(self, call_request, login)


class UserResource(JSONController):

    # Scope:   Resource
    # GET:     Get user details
    # DELETE:  Delete a user
    # PUT:     User update

    @auth_required(READ)
    def GET(self, login):

        manager = managers.user_manager()
        user = manager.find_by_login(login)

        return self.ok(user)


    @auth_required(DELETE)
    def DELETE(self, login):

        manager = managers.user_manager()

        resources = {dispatch_constants.RESOURCE_USER_TYPE: {login: dispatch_constants.RESOURCE_DELETE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_USER_TYPE, login),
                action_tag('delete')]
        call_request = CallRequest(manager.delete_user,
                                   [login],
                                   resources=resources,
                                   tags=tags)
        return execution.execute_ok(self, call_request)


    @auth_required(UPDATE)
    def PUT(self, login):

        # Pull all the user update data
        user_data = self.params()
        delta = user_data.get('delta', None)

        # Perform update
        manager = managers.user_manager()
        resources = {dispatch_constants.RESOURCE_USER_TYPE: {login: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_USER_TYPE, login),
                action_tag('update')]
        call_request = CallRequest(manager.update_user,
                                   [login, delta],
                                   resources=resources,
                                   tags=tags)
        return execution.execute_ok(self, call_request)


# -- web.py application -------------------------------------------------------


urls = (
    '/$', 'UsersCollection',
    '/([^/]+)/$', 'UserResource',
)

application = web.application(urls, globals())
