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
from celery import task
import web

from pulp.common.tags import action_tag, resource_tag
from pulp.server import config as pulp_config
from pulp.server.async.tasks import Task
from pulp.server.auth.authorization import READ, CREATE, UPDATE, DELETE, operation_to_name
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.webservices import execution, serialization
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
        args = [role_id, display_name, description]
        weight = pulp_config.config.getint('tasks', 'create_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, role_id),
                action_tag('create')]
        call_request = CallRequest(manager.create_role, # rbarlow_converted
                                   args,
                                   weight=weight,
                                   tags=tags)
        call_request.creates_resource(dispatch_constants.RESOURCE_ROLE_TYPE, role_id)

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

        tags = [resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, role_id),
                action_tag('delete')]
        call_request = CallRequest(manager.delete_role, # rbarlow_converted
                                   [role_id],
                                   tags=tags)
        call_request.deletes_resource(dispatch_constants.RESOURCE_ROLE_TYPE, role_id)

        return self.ok(execution.execute(call_request))

    @auth_required(UPDATE)
    def PUT(self, role_id):

        # Pull all the role update data
        role_data = self.params()
        delta = role_data.get('delta', None)

        # Perform update        
        manager = managers.role_manager()
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, role_id),
                action_tag('update')]
        call_request = CallRequest(manager.update_role, # rbarlow_converted
                                   [role_id, delta],
                                   tags=tags)
        call_request.updates_resource(dispatch_constants.RESOURCE_ROLE_TYPE, role_id)

        role = execution.execute(call_request)
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
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, role_id),
                action_tag('add_user_to_role')]

        call_request = CallRequest(role_manager.add_user_to_role, # rbarlow_converted
                                   [role_id, login],
                                   tags=tags)
        call_request.updates_resource(dispatch_constants.RESOURCE_USER_TYPE, login)
        return self.ok(execution.execute_sync(call_request))


class RoleUser(JSONController):

    # Scope:  Exclusive Sub-resource
    # DELETE: Remove user from a role

    @auth_required(UPDATE)
    def DELETE(self, role_id, login):

        role_manager = managers.role_manager()
        tags = [resource_tag(dispatch_constants.RESOURCE_ROLE_TYPE, role_id),
                action_tag('remove_user_from_role')]
        call_request = CallRequest(role_manager.remove_user_from_role, # rbarlow_converted
                                   [role_id, login],
                                   tags=tags,
                                   archive=True)
        call_request.updates_resource(dispatch_constants.RESOURCE_USER_TYPE, login)
        call_request.reads_resource(dispatch_constants.RESOURCE_ROLE_TYPE, role_id)
        return  self.ok(execution.execute_sync(call_request))



# -- web.py application -------------------------------------------------------


urls = (
    '/$', 'RolesCollection',
    '/([^/]+)/$', 'RoleResource',
    
    '/([^/]+)/users/$', 'RoleUsers', # sub-collection
    '/([^/]+)/users/([^/]+)/$', 'RoleUser', # exclusive sub-resource
)

application = web.application(urls, globals())


