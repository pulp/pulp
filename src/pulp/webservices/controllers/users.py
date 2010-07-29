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

from pulp.api.user import UserApi
from pulp.webservices.controllers.base import JSONController
from pulp.webservices.role_check import RoleCheck

# users api ---------------------------------------------------------------

api = UserApi()

# controllers -----------------------------------------------------------------

class Users(JSONController):

    @JSONController.error_handler
    @RoleCheck()
    def GET(self):
        """
        List all available users.
        @return: a list of all users
        """
        # implement filters
        return self.ok(api.users())

    @JSONController.error_handler
    def PUT(self):
        """
        Create a new user
        @return: user that was created
        """
        user_data = self.params()
        user = api.create(user_data['login'], user_data['password'],
                                   user_data['name'])
        return self.created(user['id'], user)

    @JSONController.error_handler
    def DELETE(self):
        """
        @return: True on successful deletion of all users
        """
        api.clean()
        return self.ok(True)


class User(JSONController):

    @JSONController.error_handler
    def GET(self, login):
        """
        Get a users information
        @param login: user login
        @return: user metadata
        """
        return self.ok(api.user(login))

    @JSONController.error_handler
    def PUT(self, login):
        """
        Update user
        @param login: The user's login
        """
        user = self.params()
        user = api.update(user)
        return self.ok(True)

    @JSONController.error_handler
    def DELETE(self, login):
        """
        Delete a user
        @param login: login of user to delete
        @return: True on successful deletion of user
        """
        api.delete(login=login)
        return self.ok(True)
# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Users',
    '/([^/]+)/$', 'User',
)

application = web.application(URLS, globals())
