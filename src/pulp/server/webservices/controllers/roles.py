#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import web

from pulp.server.api.role import RoleApi
from pulp.server.api.role import PermissionApi
from pulp.server.api.user import UserApi
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.role_check import RoleCheck

# users api ---------------------------------------------------------------

api = RoleApi()
perm_api = PermissionApi()
userapi = UserApi()

# controllers -----------------------------------------------------------------

class Roles(JSONController):

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self):
        """
        List all available Roles.
        @return: a list of all Roles
        """
        # implement filters
        return self.ok(api.roles())

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def PUT(self):
        """
        Create a new Role
        @return: role that was created
        """
        role_data = self.params()

        name = role_data['name']
        if api.user(name) is not None:
            return self.conflict('A role with the name, %s, already exists' % login)

        # action_type = [RoleActionType.CREATE, RoleActionType.WRITE, RoleActionType.READ]
        # resource_type = RoleResourceType.REPO
        # role = self.roleapi.create(name, desc, action_type, resource_type)
        role = api.create(role_data['name'], role_data['description'],
                                   role_data['action_type'], role_data['resource_type'])
        return self.created(role['name'], role)

    def POST(self):
        # REST dictates POST to collection, and PUT to specific resource for
        # creation, this is the start of supporting both
        return self.PUT()

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def DELETE(self):
        """
        @return: True on successful deletion of all roles
        """
        api.clean()
        return self.ok(True)


class Role(JSONController):

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self, name):
        """
        Get Role information
        @param name: role name
        @return: role metadata
        """
        return self.ok(api.role(name))

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def PUT(self, name):
        """
        Update Role
        @param login: The user's login
        """
        role = self.params()
        role = api.update(role)
        return self.ok(True)

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def DELETE(self, name):
        """
        Delete a Role
        @param name: name of Role to delete
        @return: True on successful deletion of Role
        """
        api.delete(name)
        return self.ok(True)

class RoleActions(JSONController):
    exposed_actions = (
        'add_user',
        'add_instance',
    )

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def add_user(self, role_name, login):
        """
        @param role_name: name of role you want to add a user to
        @param login: login of user you want to add to a Role
        @return: True on successful addition of User to Role
        """
        data = self.params()
        role = api.role(role_name)
        user = userapi.user(login)
        api.add_user(role, user)
        return self.ok(True)

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def add_instance(self, instance_id, role_name):
        """
        @param role_name: name of role you want to add a user to
        @param instance_id: unique ID of the instance you want to add to this role
        @return: True on successful addition of Instance to Role
        """
        data = self.params()
        role = api.add_instance(instance_id, role_name)
        return self.ok(True)


    # web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Roles',
    '/([^/]+)/$', 'Role',
)

application = web.application(URLS, globals())
