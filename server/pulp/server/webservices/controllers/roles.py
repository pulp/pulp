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
import web

from pulp.server.auth.authorization import READ, CREATE, UPDATE, DELETE
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
import pulp.server.exceptions as exceptions
import pulp.server.managers.factory as managers


class RolesCollection(JSONController):
    # Scope: Collection
    # GET:   Retrieves all roles
    # POST:  Create a role

    @auth_required(READ)
    def GET(self):

        role_query_manager = managers.role_query_manager()
        user_query_manager = managers.user_query_manager()
        permissions_manager = managers.permission_manager()
        roles = role_query_manager.find_all()
        for role in roles:
            role['users'] = [u['login'] for u in
                             user_query_manager.find_users_belonging_to_role(role['id'])]
            for resource, operations in role['permissions'].items():
                role['permissions'][resource] = [permissions_manager.operation_value_to_name(o)
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
        role = manager.create_role(role_id, display_name, description)
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

        role = managers.role_query_manager().find_by_id(role_id)
        if role is None:
            raise exceptions.MissingResource(role_id)

        role['users'] = [u['login'] for u in
                         managers.user_query_manager().find_users_belonging_to_role(role['id'])]
        permissions_manager = managers.permission_manager()
        for resource, operations in role['permissions'].items():
            role['permissions'][resource] = [permissions_manager.operation_value_to_name(o)
                                             for o in operations]

        role.update(serialization.link.current_link_obj())
        return self.ok(role)

    @auth_required(DELETE)
    def DELETE(self, role_id):

        manager = managers.role_manager()
        result = manager.delete_role(role_id)
        return self.ok(result)

    @auth_required(UPDATE)
    def PUT(self, role_id):

        # Pull all the role update data
        role_data = self.params()
        delta = role_data.get('delta', None)

        manager = managers.role_manager()
        role = manager.update_role(role_id, delta)

        role.update(serialization.link.current_link_obj())
        return self.ok(role)


class RoleUsers(JSONController):

    # Scope:  Sub-collection
    # GET:    List Users belonging to a role
    # POST:   Add user to a role

    @auth_required(READ)
    def GET(self, role_id):
        user_query_manager = managers.user_query_manager()

        role_users = user_query_manager.find_users_belonging_to_role(role_id)
        return self.ok(role_users)

    @auth_required(UPDATE)
    def POST(self, role_id):

        # Params (validation will occur in the manager)
        params = self.params()
        login = params.get('login', None)
        if login is None:
            raise exceptions.InvalidValue(login)

        role_manager = managers.role_manager()
        return self.ok(role_manager.add_user_to_role(role_id, login))


class RoleUser(JSONController):

    # Scope:  Exclusive Sub-resource
    # DELETE: Remove user from a role

    @auth_required(UPDATE)
    def DELETE(self, role_id, login):

        role_manager = managers.role_manager()
        return self.ok(role_manager.remove_user_from_role(role_id, login))


# -- web.py application -------------------------------------------------------


urls = (
    '/$', 'RolesCollection',
    '/([^/]+)/$', 'RoleResource',
    
    '/([^/]+)/users/$', 'RoleUsers', # sub-collection
    '/([^/]+)/users/([^/]+)/$', 'RoleUser', # exclusive sub-resource
)

application = web.application(urls, globals())


