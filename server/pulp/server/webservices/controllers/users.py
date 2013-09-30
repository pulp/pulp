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

import logging

import web

from pulp.common.tags import action_tag, resource_tag
from pulp.server import config as pulp_config
from pulp.server.auth.authorization import READ, CREATE, UPDATE, DELETE
from pulp.server.db.model.auth import Permission
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.webservices import execution
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.controllers.search import SearchController
from pulp.server.webservices import serialization
import pulp.server.exceptions as exceptions
import pulp.server.managers.factory as managers


_LOG = logging.getLogger(__name__)


class UsersCollection(JSONController):

    # Scope: Collection
    # GET:   Retrieves all users
    # POST:  Adds a user

    @staticmethod
    def _process_users(users):
        """
        Apply standard processing to a collection of users being returned
        to a client.  Adds the object link and removes user password.

        @param users: collection of users
        @type  users: list, tuple

        @return the same list that was passed in, just for convenience. The list
                itself is not modified- only its members are modified in-place.
        @rtype  list of User instances
        """
        for user in users:
            user.pop('password', None)
            user.update(serialization.link.search_safe_link_obj(user['login']))

        return users


    @auth_required(READ)
    def GET(self):

        query_manager = managers.user_query_manager()
        users = query_manager.find_all()
        self._process_users(users)

        return self.ok(users)

    @auth_required(CREATE)
    def POST(self):

        # Pull all the user data
        user_data = self.params()
        login = user_data.get('login', None)
        password = user_data.get('password', None)
        name = user_data.get('name', None)

        # Creation
        manager = managers.user_manager()
        args = [login]
        kwargs = {'password': password,
                  'name': name}
        weight = pulp_config.config.getint('tasks', 'create_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_USER_TYPE, login),
                action_tag('create')]
        call_request = CallRequest(manager.create_user, # rbarlow_converted
                                   args,
                                   kwargs,
                                   weight=weight,
                                   tags=tags,
                                   kwarg_blacklist=['password'])
        call_request.creates_resource(dispatch_constants.RESOURCE_USER_TYPE, login)
        user = execution.execute_sync(call_request)
        user_link = serialization.link.child_link_obj(login)
        user.update(user_link)

        # Grant permissions
        permission_manager = managers.permission_manager()
        permission_manager.grant_automatic_permissions_for_resource(user_link['_href'])

        return self.created(login, user)


class UserResource(JSONController):

    # Scope:   Resource
    # GET:     Get user details
    # DELETE:  Delete a user
    # PUT:     User update

    @auth_required(READ)
    def GET(self, login):

        user = managers.user_query_manager().find_by_login(login)
        if user is None:
            raise exceptions.MissingResource(login)

        user.update(serialization.link.current_link_obj())

        return self.ok(user)


    @auth_required(DELETE)
    def DELETE(self, login):

        manager = managers.user_manager()

        tags = [resource_tag(dispatch_constants.RESOURCE_USER_TYPE, login),
                action_tag('delete')]
        call_request = CallRequest(manager.delete_user, # rbarlow_converted
                                   [login],
                                   tags=tags)
        call_request.deletes_resource(dispatch_constants.RESOURCE_USER_TYPE, login)
        result = execution.execute(call_request)

        # Delete any existing user permissions given to the creator of the user
        user_link = serialization.link.current_link_obj()['_href']
        if Permission.get_collection().find_one({'resource' : user_link}):
            Permission.get_collection().remove({'resource' : user_link}, safe=True)

        return self.ok(result)


    @auth_required(UPDATE)
    def PUT(self, login):

        # Pull all the user update data
        user_data = self.params()
        delta = user_data.get('delta', None)

        # Perform update
        manager = managers.user_manager()
        tags = [resource_tag(dispatch_constants.RESOURCE_USER_TYPE, login),
                action_tag('update')]
        call_request = CallRequest(manager.update_user, # rbarlow_converted
                                   [login, delta],
                                   tags=tags)
        call_request.updates_resource(dispatch_constants.RESOURCE_USER_TYPE, login)
        result = execution.execute(call_request)
        result.update(serialization.link.current_link_obj())
        return self.ok(result)


class UserSearch(SearchController):
    def __init__(self):
        super(UserSearch, self).__init__(
            managers.user_query_manager().find_by_criteria)

    @auth_required(READ)
    def GET(self):
        users = self._get_query_results_from_get(is_user_search=True)
        UsersCollection._process_users(users)

        return self.ok(users)


    @auth_required(READ)
    def POST(self):
        """
        Searches based on a Criteria object. Requires a posted parameter
        'criteria' which has a data structure that can be turned into a
        Criteria instance.

        @param criteria:    Required. data structure that can be turned into
                            an instance of the Criteria model.
        @type  criteria:    dict

        @return:    list of matching users
        @rtype:     list
        """
        users = self._get_query_results_from_post(is_user_search=True)
        UsersCollection._process_users(users)

        return self.ok(users)


urls = (
    '/$', 'UsersCollection',
    '/search/$', 'UserSearch',
    '/([^/]+)/$', 'UserResource',
)
application = web.application(urls, globals())
