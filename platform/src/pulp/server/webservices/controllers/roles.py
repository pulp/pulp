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
import pulp.server.exceptions as exceptions


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
        for role in roles:
            role['users'] = [u['login'] for u in
                             managers.user_query_manager().find_users_belonging_to_role(role['id'])]
            for resource, operations in role['permissions'].items():
                role['permissions'][resource] = [operation_to_name(o)
                                                 for o in operations]
                
        for role in roles:
            role.update(serialization.link.child_link_obj(role['id']))

        return self.ok(roles)

    @auth_required(CREATE)
    def POST(self):

        # Pull all the roles data
        role_data = self.params()
        role_id = role_data.get('role_id', None)
        display_name = role_data.get('display_name', None)
        description = role_data.get('description', None)

        # Creation
        manager = managers.role_manager()
        resources = {dispatch_constants.RESOURCE_ROLE_TYPE: {role_id: dispatch_constants.RESOURCE_CREATE_OPERATION}}
        args = [role_id, display_name, description]
        weight = pulp_config.config.getint('tasks', 'create_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, role_id),
                action_tag('create')]
        call_request = CallRequest(manager.create_role,
                                   args,
                                   resources=resources,
                                   weight=weight,
                                   tags=tags)
        
        role = execution.execute_sync(call_request)
        role_link = serialization.link.child_link_obj(role_id)
        role.update(role_link)
        
        return self.created(role_id, role)


class RoleResource(JSONController):

    # Scope:   Resource
    # GET:     Get Role details
    # DELETE:  Deletes a role
    # PUT:     Role update

    @auth_required(READ)
    def GET(self, role_id):

        manager = managers.role_query_manager()
        role = manager.find_by_id(role_id)
        if role is None:
            raise exceptions.MissingResource(role_id)
        
        role['users'] = [u['login'] for u in
                         managers.user_query_manager().find_users_belonging_to_role(role['id'])]
        for resource, operations in role['permissions'].items():
            role['permissions'][resource] = [operation_to_name(o)
                                             for o in operations]

        role.update(serialization.link.current_link_obj())

        return self.ok(role)


    @auth_required(DELETE)
    def DELETE(self, role_id):

        manager = managers.role_manager()
        
        resources = {dispatch_constants.RESOURCE_ROLE_TYPE: {role_id: dispatch_constants.RESOURCE_DELETE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, role_id),
                action_tag('delete')]
        call_request = CallRequest(manager.delete_role,
                                   [role_id],
                                   resources=resources,
                                   tags=tags)
        return self.ok(execution.execute(call_request))

    @auth_required(UPDATE)
    def PUT(self, role_id):

        # Pull all the role update data
        role_data = self.params()
        delta = role_data.get('delta', None)

        # Perform update        
        manager = managers.role_manager()
        resources = {dispatch_constants.RESOURCE_ROLE_TYPE: {role_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, role_id),
                action_tag('update')]
        call_request = CallRequest(manager.update_role,
                                   [role_id, delta],
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
    def GET(self, role_id):
        user_query_manager = managers.user_query_manager()

        role_users = user_query_manager.find_users_belonging_to_role(role_id)
        return self.ok(role_users)

    @auth_required(CREATE)
    def POST(self, role_id):

        # Params (validation will occur in the manager)
        params = self.params()
        login = params.get('login', None)
        if login is None:
            raise exceptions.InvalidValue(login)

        role_manager = managers.role_manager()
        resources = {dispatch_constants.RESOURCE_USER_TYPE: {login: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, role_id),
                action_tag('add_user_to_role')]

        call_request = CallRequest(role_manager.add_user_to_role,
                                   [role_id, login],
                                   resources=resources,
                                   tags=tags)
        return execution.execute_sync_created(self, call_request, 'user')


class RoleUser(JSONController):

    # Scope:  Exclusive Sub-resource
    # DELETE: Remove user from a role

    @auth_required(UPDATE)
    def DELETE(self, role_id, login):

        role_manager = managers.role_manager()
        resources = {dispatch_constants.RESOURCE_USER_TYPE: {login: dispatch_constants.RESOURCE_UPDATE_OPERATION},
                     dispatch_constants.RESOURCE_ROLE_TYPE: {role_id: dispatch_constants.RESOURCE_READ_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, role_id),
                action_tag('remove_user_from_role')]
        call_request = CallRequest(role_manager.remove_user_from_role,
                                   [role_id, login],
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


