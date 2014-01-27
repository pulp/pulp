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
from pulp.server.db.model.auth import Permission
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.controllers.search import SearchController
from pulp.server.webservices import serialization
import pulp.server.exceptions as exceptions
import pulp.server.managers.factory as managers


USER_WHITELIST = [u'login', u'name', u'roles']


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
            user.update(serialization.link.search_safe_link_obj(user['login']))
            JSONController.process_dictionary_against_whitelist(user, USER_WHITELIST)
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

        user = manager.create_user(*args, **kwargs)

        # Add the link to the user
        user_link = serialization.link.child_link_obj(login)
        user.update(user_link)

        # Grant permissions
        user_link = serialization.link.child_link_obj(login)
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

        self.process_dictionary_against_whitelist(user, USER_WHITELIST)
        return self.ok(user)

    @auth_required(DELETE)
    def DELETE(self, login):
        """
        Delete a given user object
        :param login: the login id of the user to delete
        :type login: str
        """

        manager = managers.user_manager()
        result = manager.delete_user(login)

        # Delete any existing user permissions given to the creator of the user
        user_link = serialization.link.current_link_obj()['_href']
        if Permission.get_collection().find_one({'resource': user_link}):
            Permission.get_collection().remove({'resource': user_link}, safe=True)

        return self.ok(result)

    @auth_required(UPDATE)
    def PUT(self, login):
        """
        Update a user

        :param login: the login id of the user to update
        :type login: str
        """

        # Pull all the user update data
        user_data = self.params()
        delta = user_data.get('delta', None)

        # Perform update
        manager = managers.user_manager()
        result = manager.update_user(login, delta)
        self.process_dictionary_against_whitelist(result, USER_WHITELIST)
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
