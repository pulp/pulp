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
from pulp.server.auth.authorization import READ, CREATE, UPDATE, DELETE, operation_to_name
from pulp.server.webservices import execution
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices import serialization

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- controllers --------------------------------------------------------------

class RolesCollection(JSONController):
    
    # Scope: Collection
    # GET:   Retrieves all roles
    # POST:  Create a role

    @auth_required(READ)
    def GET(self):

        role_query_manager = managers.role_query_manager()
        roles = role_query_manager.find_all()
        role_names = [r['name'] for r in roles]
        return self.ok(role_names)

    @auth_required(CREATE)
    def POST(self):

        # Pull all the roles data
        role_data = self.params()
        name = role_data.get('name', None)

        # Creation
        manager = managers.role_manager()
        resources = {dispatch_constants.RESOURCE_ROLE_TYPE: {name: dispatch_constants.RESOURCE_CREATE_OPERATION}}
        args = [name]
        weight = pulp_config.config.getint('tasks', 'create_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, name),
                action_tag('create')]
        call_request = CallRequest(manager.create_role,
                                   args,
                                   resources=resources,
                                   weight=weight,
                                   tags=tags)
        return execution.execute_sync_created(self, call_request, name)


class RoleResource(JSONController):

    # Scope:   Resource
    # GET:     Get Role details
    # DELETE:  Deletes a role
    # PUT:     Role update

    @auth_required(READ)
    def GET(self, name):

        manager = managers.role_query_manager()()
        role = manager.find_by_name(name)
       
        role['users'] = [u['login'] for u in
                         managers.user_query_manager().find_users_belonging_to_role(role)]
        for resource, operations in role['permissions'].items():
            role['permissions'][resource] = [operation_to_name(o)
                                             for o in operations]
        return self.ok(role)


    @auth_required(DELETE)
    def DELETE(self, name):

        manager = managers.role_manager()
        
        resources = {dispatch_constants.RESOURCE_ROLE_TYPE: {name: dispatch_constants.RESOURCE_DELETE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, id),
                action_tag('delete')]
        call_request = CallRequest(manager.delete_role,
                                   [name],
                                   resources=resources,
                                   tags=tags)
        return self.ok(execution.execute(call_request))

    @auth_required(UPDATE)
    def PUT(self, name):

        # Pull all the role update data
        role_data = self.params()
        delta = role_data.get('delta', None)

        # Perform update        
        manager = managers.role_manager()
        resources = {dispatch_constants.RESOURCE_ROLE_TYPE: {name: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, name),
                action_tag('update')]
        call_request = CallRequest(manager.update_role,
                                   [name, delta],
                                   resources=resources,
                                   tags=tags)
        role = execution.execute(call_request)
        role.update(serialization.link.current_link_obj())
        return self.ok(role)
    

# -- role user controllers -----------------------------------------------------

class RoleUsers(JSONController):

    # Scope:  Sub-collection
    # GET:    List Users belonging to a role
    # POST:   Add user to a role

    @auth_required(READ)
    def GET(self, name):
        user_query_manager = managers.user_query_manager()

        role_users = user_query_manager.find_users_belonging_to_role()
        return self.ok(role_users)

    @auth_required(CREATE)
    def POST(self, name):

        # Params (validation will occur in the manager)
        params = self.params()
        login = params.get('login', None)

        role_manager = managers.role_manager()
        resources = {dispatch_constants.RESOURCE_USER_TYPE: {login: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, name),
                action_tag('add_user_to_role')]

        call_request = CallRequest(role_manager.add_user_to_role,
                                   [name, login],
                                   resources=resources,
                                   tags=tags)
        return execution.execute_sync_created(self, call_request, 'user')


class RoleUser(JSONController):

    # Scope:  Exclusive Sub-resource
    # DELETE: Remove user from a role

    @auth_required(UPDATE)
    def DELETE(self, name, login):

        role_manager = managers.role_manager()
        resources = {dispatch_constants.RESOURCE_USER_TYPE: {login: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, name),
                action_tag('remove_user_from_role')]
        call_request = CallRequest(role_manager.remove_user_from_role,
                                   [name],
                                   resources=resources,
                                   tags=tags,
                                   archive=True)
        return execution.execute_ok(self, call_request)



# -- web.py application -------------------------------------------------------


urls = (
    '/$', 'RolesCollection',
    '/([^/]+)/$', 'RoleResource',
    
    '/([^/]+)/users/$', 'RoleUsers', # sub-collection
    '/([^/]+)/users/([^/]+)/$', 'RoleUser', # exclusive sub-resource
)

application = web.application(urls, globals())


