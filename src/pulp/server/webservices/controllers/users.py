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

from pulp.server.api.user import UserApi
from pulp.server.api.auth import AuthApi
from pulp.server.auth.authorization import (
    is_last_super_user, revoke_all_permissions_from_user)
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.role_check import RoleCheck

# users api ---------------------------------------------------------------

api = UserApi()
auth_api = AuthApi()

# controllers -----------------------------------------------------------------

class Users(JSONController):

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self):
        """
        List all available users.
        @return: a list of all users
        """
        # implement filters
        return self.ok(api.users())

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def PUT(self):
        """
        Create a new user
        @return: user that was created
        """
        user_data = self.params()

        login = user_data['login']
        if api.user(login) is not None:
            return self.conflict('A user with the login, %s, already exists' % login)

        user = api.create(user_data['login'], user_data['password'],
                                   user_data['name'])
        return self.created(user['id'], user)

    def POST(self):
        # REST dictates POST to collection, and PUT to specific resource for
        # creation, this is the start of supporting both
        return self.PUT()

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def DELETE(self):
        """
        @return: True on successful deletion of all users
        """
        api.clean()
        return self.ok(True)


class User(JSONController):

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self, login):
        """
        Get a users information
        @param login: user login
        @return: user metadata
        """
        return self.ok(api.user(login))

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def PUT(self, login):
        """
        Update user
        @param login: The user's login
        """
        user = self.params()
        user = api.update(user)
        return self.ok(True)

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def DELETE(self, login):
        """
        Delete a user
        @param login: login of user to delete
        @return: True on successful deletion of user
        """
        user = api.user(login)
        if user is None:
            return self.not_found('No such user: %s' % login)
        # XXX this logic should be in the api layer, but because persistence
        # and logic is mashed together, it causes cyclic depenedencies
        if is_last_super_user(user):
            return self.bad_request(
                'Cannot delete %s, they are the last super user')
        revoke_all_permissions_from_user(user)
        api.delete(login=login)
        return self.ok(True)

class AdminAuthCertificates(JSONController):

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self):
        '''
        Creates and returns an authentication certificate for the currently
        logged in user.
        '''
        private_key, cert = auth_api.admin_certificate()
        certificate = {'certificate': cert, 'private_key': private_key}
        return self.ok(certificate)

    # web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Users',
    '/admin_certificate/$', 'AdminAuthCertificates',
    '/([^/]+)/$', 'User',
)

application = web.application(URLS, globals())
