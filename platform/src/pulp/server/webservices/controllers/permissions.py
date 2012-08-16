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
import pulp.server.exceptions as exceptions


# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- controllers --------------------------------------------------------------

class PermissionCollection(JSONController):

    # Scope:   Resource
    # GET:     Get permissions for a particular resource

    @auth_required(READ)
    def GET(self):
        query_params = web.input()
        resource = query_params.get('resource', None)
        if resource is None:
            raise exceptions.InvalidValue(resource)

        permission = managers.permission_query_manager().find_by_resource(resource)
        if permission is None:
            permission = {}
        else:
            users = permission['users']
            for user, ops in users.items():
                users[user] = [operation_to_name(o) for o in ops]
        
        return self.ok(permission)


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
        
        _check_invalid_params({'login':login,
                               'resource':resource,
                               'operation_names':operation_names})
            
        operations = _get_operations(operation_names)
        
        # Grant permission synchronously
        permission_manager = managers.permission_manager()
        tags = [resource_tag(dispatch_constants.RESOURCE_PERMISSION_TYPE, resource),
                resource_tag(dispatch_constants.RESOURCE_USER_TYPE, login),
                action_tag('grant_permission_to_user')]

        call_request = CallRequest(permission_manager.grant,
                                   [resource, login, operations],
                                   tags=tags)
        call_request.reads_resource(dispatch_constants.RESOURCE_USER_TYPE, login)
        call_request.updates_resource(dispatch_constants.RESOURCE_PERMISSION_TYPE, resource)
        
        return self.ok(execution.execute_sync(call_request))
        

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
        
        _check_invalid_params({'login':login,
                               'resource':resource,
                               'operation_names':operation_names})
        
        operations = _get_operations(operation_names)
        
        # Grant permission synchronously
        permission_manager = managers.permission_manager()
        
        tags = [resource_tag(dispatch_constants.RESOURCE_PERMISSION_TYPE, resource),
                resource_tag(dispatch_constants.RESOURCE_USER_TYPE, login),
                action_tag('revoke_permission_from_user')]

        call_request = CallRequest(permission_manager.revoke,
                                   [resource, login, operations],
                                   tags=tags)
        call_request.reads_resource(dispatch_constants.RESOURCE_USER_TYPE, login)
        call_request.updates_resource(dispatch_constants.RESOURCE_PERMISSION_TYPE, resource)
        
        return self.ok(execution.execute_sync(call_request))

class GrantToRole(JSONController):

    # Scope: Action
    # POST:  Grant permission to a role

    @auth_required(EXECUTE)
    def POST(self):

        # Params
        params = self.params()
        role_id = params.get('role_id', None)
        resource = params.get('resource', None)
        operation_names = params.get('operations', None)
        
        _check_invalid_params({'role_id':role_id,
                               'resource':resource,
                               'operation_names':operation_names})

        operations = _get_operations(operation_names)
        
        # Grant permission synchronously
        role_manager = managers.role_manager()
        
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, role_id),
                action_tag('grant_permission_to_role')]

        call_request = CallRequest(role_manager.add_permissions_to_role,
                                   [role_id, resource, operations],
                                   tags=tags)
        call_request.updates_resource(dispatch_constants.RESOURCE_ROLE_TYPE, role_id)

        return self.ok(execution.execute_sync(call_request))

class RevokeFromRole(JSONController):

    # Scope: Action
    # POST:  Revoke permission from a role

    @auth_required(EXECUTE)
    def POST(self):

        # Params
        params = self.params()
        role_id = params.get('role_id', None)
        resource = params.get('resource', None)
        operation_names = params.get('operations', None)
        
        _check_invalid_params({'role_id':role_id,
                               'resource':resource,
                               'operation_names':operation_names})

        operations = _get_operations(operation_names)
        
        # Grant permission synchronously
        role_manager = managers.role_manager()
        
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, role_id),
                action_tag('remove_permission_from_role')]

        call_request = CallRequest(role_manager.remove_permissions_from_role,
                                   [role_id, resource, operations],
                                   tags=tags)
        call_request.updates_resource(dispatch_constants.RESOURCE_ROLE_TYPE, role_id)
        
        return self.ok(execution.execute_sync(call_request))


def _check_invalid_params(params):
    # Raise InvalidValue if any of the params are None
    
    invalid_values = []
    for key, value in params:
        if value is None:
            invalid_values.append(key)

    if invalid_values:
        raise exceptions.InvalidValue(invalid_values)

# -- web.py application -------------------------------------------------------


urls = (
    '/$', 'PermissionCollection',
    
    '/user/grant/$', 'GrantToUser',
    '/user/revoke/$', 'RevokeFromUser',
    
    '/role/grant/$', 'GrantToRole',
    '/role/revoke/$', 'RevokeFromRole',
    
)

application = web.application(urls, globals())


