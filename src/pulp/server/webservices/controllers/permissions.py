# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _

import web

from pulp.server.auth import authorization
from pulp.server.db.model import Permission
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler)

# permissions controller ------------------------------------------------------

class Permissions(JSONController):

    @error_handler
    @auth_required(super_user_only=True)
    def POST(self):
        """
        [[wiki]]
        title: Show Permissions
        description: Show the permissions for a given resource
        method: POST
        path: /permissions/show/
        permission: super user only
        success response: 200 OK
        failure response: 400 Bad Request if the required parameters are not present
        return: permissions for given resource
        example:
        {{{
        #!js
        {"id": "78daa991-ec1f-4908-9b59-5c1010bde7a6",
         "resource": "/",
         "users": {"admin": ["CREATE", "READ", "UPDATE", "DELETE", "EXECUTE"]}
        }
        }}}
        parameters:
         * resource!, str, resource path
        """

        try:
            resource = self.params()['resource']
        except KeyError:
            msg = _('expected parameter: resource')
            return self.bad_request(msg)
        perms = authorization.show_permissions(resource)
        if perms is None:
            perms = Permission(resource)
        else:
            users = perms['users']
            for user, ops in users.items():
                users[user] = [authorization.operation_to_name(o) for o in ops]
        return self.ok(perms)


class PermissionActions(JSONController):

    user_target = 'user'
    role_target = 'role'

    grant_action = 'grant'
    revoke_action = 'revoke'

    def _grant_to_user(self, data):
        """
        [[wiki]]
        title: Grant User Permissions
        description: Grant permissions for a resource to a user
        method: POST
        path: /permissions/user/grant/
        permission: READ
        success response: 200 OK
        failure response: 400 Bad Request if the required parameters are not present
        return: true
        parameters:
         * username!, str, login of user to grant permissions to
         * resource!, str, uri path of resource to grant permissions on
         * operations!, list of strings, valid operations are: CREATE, READ, UPDATE, DELETE, EXECUTE
        """

        try:
            user = data['username']
            resource = data['resource']
            ops = data['operations']
        except KeyError:
            msg = _('expected parameters: username, resource, operations')
            return self.bad_request(msg)
        val = authorization.grant_permission_to_user(resource, user, ops)
        return self.ok(val)

    def _revoke_from_user(self, data):
        """
        [[wiki]]
        title: Revoke User Permissions
        description: Revoke permissions for a resource from a user
        method: POST
        path: /permissions/user/revoke/
        permission: READ
        success response: 200 OK
        failure response: 400 Bad Request if the required parameters are not present
        return: true
        parameters:
         * username!, str, login of user to revoke permissions from
         * resource!, str, uri path of resource to revoke permissions on
         * operations!, list of strings, valid operations are: CREATE, READ, UPDATE, DELETE, EXECUTE
        """

        try:
            user = data['username']
            resource = data['resource']
            ops = data['operations']
        except KeyError:
            msg = _('expected parameters: username, resource, operations')
            return self.bad_request(msg)
        val = authorization.revoke_permission_from_user(resource, user, ops)
        return self.ok(val)

    def _grant_to_role(self, data):
        """
        [[wiki]]
        title: Grant Role Permissions
        description: Grant permissions for a resource to a role
        method: POST
        path: /permissions/role/grant/
        permission: READ
        success response: 200 OK
        failure response: 400 Bad Request if the required parameters are not present
        return: true
        parameters:
         * rolename!, str, name of role to grant permissions to
         * resource!, str, uri path of resource to grant permissions on
         * operations!, list of strings, valid operations are: CREATE, READ, UPDATE, DELETE, EXECUTE
        """

        try:
            role = data['rolename']
            resource = data['resource']
            ops = data['operations']
        except KeyError:
            msg = _('expected parameters: rolename, resource, operations')
            return self.bad_request(msg)
        val = authorization.grant_permission_to_role(resource, role, ops)
        return self.ok(val)

    def _revoke_from_role(self, data):
        """
        [[wiki]]
        title: Revoke Role Permissions
        description: Revoke permissions for a resource from a role
        method: POST
        path: /permissions/role/revoke/
        permission: READ
        success response: 200 OK
        failure response: 400 Bad Request if the required parameters are not present
        return: true
        parameters:
         * rolename!, str, name of role to revoke permissions from
         * resource!, str, uri path of resource to revoke permissions on
         * operations!, list of strings, valid operations are: CREATE, READ, UPDATE, DELETE, EXECUTE
        """

        try:
            role = data['rolename']
            resource = data['resource']
            ops = data['operations']
        except KeyError:
            msg = _('expected parameters: rolename, resource, operations')
            return self.bad_request(msg)
        val = authorization.revoke_permission_from_role(resource, role, ops)
        return self.ok(val)

    @error_handler
    @auth_required(super_user_only=True)
    def POST(self, target, action):
        try:
            return {
                (self.user_target, self.grant_action): self._grant_to_user,
                (self.user_target, self.revoke_action): self._revoke_from_user,
                (self.role_target, self.grant_action): self._grant_to_role,
                (self.role_target, self.revoke_action): self._revoke_from_role,
            }[(target, action)](self.params())
        except KeyError:
            msg = _('no permissions handler for target: %s; action: %s')
            return self.internal_server_error(msg % (target, action))
        except authorization.PulpAuthorizationError, e:
            return self.bad_request(e.args[0])

# web.py application ----------------------------------------------------------

urls = (
    '/show/', Permissions,
    '/(user|role)/(grant|revoke)/$', PermissionActions,
)

application = web.application(urls, globals())
