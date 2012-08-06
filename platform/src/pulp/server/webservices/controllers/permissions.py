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
import pulp.server.managers.factory as managers
from pulp.server.auth.authorization import READ, CREATE, UPDATE, DELETE, EXECUTE, operation_to_name, _get_operations
from pulp.server.webservices import execution
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices import serialization

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- controllers --------------------------------------------------------------

class PermissionCollection(JSONController):

    # Scope:   Resource
    # GET:     Get permissions for a particular resource

    @auth_required(READ)
    def GET(self):
        query_params = web.input()
        resource = query_params.get('resource')
        permissions = managers.permission_query_manager().find_by_resource(resource)
        if permissions is None:
            permissions = managers.permission_manager().create_permission(resource)
        else:
            users = permissions['users']
            for user, ops in users.items():
                users[user] = [operation_to_name(o) for o in ops]
        
        return self.ok(permissions)


class GrantToUser(JSONController):

    # Scope: Action
    # POST:  Grant permission to user

    @auth_required(EXECUTE)
    def POST(self):

        # Params
        params = self.params()
        login = params.get('login', None)
        resource = params.get('resource', None)
        operation_names = params.get('operations', None)
        operations = _get_operations(operation_names)
        
        # Grant permission synchronously
        permission_manager = managers.permission_manager()
        
        resources = {dispatch_constants.RESOURCE_USER_TYPE: {login: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_PERMISSION_TYPE: {resource: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_PERMISSION_TYPE, resource),
                resource_tag(dispatch_constants.RESOURCE_USER_TYPE, login),
                action_tag('grant_permission_to_user')]

        call_request = CallRequest(permission_manager.grant,
                                   [resource, login, operations],
                                   resources=resources,
                                   tags=tags)
        return execution.execute_sync_created(self, call_request, 'resource')


class RevokeFromUser(JSONController):

    # Scope: Action
    # POST:  Revoke permission from user

    @auth_required(EXECUTE)
    def POST(self):

        # Params
        params = self.params()
        login = params.get('login', None)
        resource = params.get('resource', None)
        operation_names = params.get('operations', None)
        operations = _get_operations(operation_names)
        
        # Grant permission synchronously
        permission_manager = managers.permission_manager()
        
        resources = {dispatch_constants.RESOURCE_USER_TYPE: {login: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_PERMISSION_TYPE: {resource: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_PERMISSION_TYPE, resource),
                resource_tag(dispatch_constants.RESOURCE_USER_TYPE, login),
                action_tag('revoke_permission_from_user')]

        call_request = CallRequest(permission_manager.revoke,
                                   [resource, login, operations],
                                   resources=resources,
                                   tags=tags)
        return execution.execute_sync_created(self, call_request, 'resource')


class GrantToRole(JSONController):

    # Scope: Action
    # POST:  Grant permission to a role

    @auth_required(EXECUTE)
    def POST(self):

        # Params
        params = self.params()
        name = params.get('name', None)
        resource = params.get('resource', None)
        operation_names = params.get('operations', None)
        operations = _get_operations(operation_names)
        
        # Grant permission synchronously
        role_manager = managers.role_manager()
        
        resources = {dispatch_constants.RESOURCE_ROLE_TYPE: {name: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, name),
                action_tag('grant_permission_to_role')]

        call_request = CallRequest(role_manager.add_permissions_to_role,
                                   [name, resource, operations],
                                   resources=resources,
                                   tags=tags)
        return execution.execute_sync_created(self, call_request, 'resource')


class RevokeFromRole(JSONController):

    # Scope: Action
    # POST:  Revoke permission from a role

    @auth_required(EXECUTE)
    def POST(self):

        # Params
        params = self.params()
        name = params.get('name', None)
        resource = params.get('resource', None)
        operation_names = params.get('operations', None)
        operations = _get_operations(operation_names)
        
        # Grant permission synchronously
        role_manager = managers.role_manager()
        
        resources = {dispatch_constants.RESOURCE_ROLE_TYPE: {name: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, name),
                action_tag('remove_permission_from_role')]

        call_request = CallRequest(role_manager.remove_permissions_from_role,
                                   [name, resource, operations],
                                   resources=resources,
                                   tags=tags)
        return execution.execute_sync_created(self, call_request, 'resource')



# -- web.py application -------------------------------------------------------


urls = (
    '/$', 'PermissionCollection',
    
    '/user/grant/$', 'GrantToUser',
    '/user/revoke/$', 'RevokeFromUser',
    
    '/role/grant/$', 'GrantToRole',
    '/role/revoke/$', 'RevokeFromRole',
    
)

application = web.application(urls, globals())


