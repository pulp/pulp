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

from pulp.client.api.base import PulpAPI


class UserAPI(PulpAPI):
    """
    Connection class to access consumer group related calls
    """
    def create(self, login, password=None, name=None):
        user_data = {"login": login,
                     "password": password,
                     "name": name}
        path = "/users/"
        return self.server.PUT(path, user_data)[1]

    def update(self, id, delta):
        path = "/users/%s/" % id
        return self.server.PUT(path, delta)[1]

    def delete(self, **kwargs):
        login = kwargs['login']
        path = "/users/%s/" % login
        return self.server.DELETE(path)[1]

    def clean(self):
        path = "/users/"
        return self.server.DELETE(path)[1]

    def users(self):
        path = "/users/"
        return self.server.GET(path)[1]

    def user(self, login):
        path = "/users/%s/" % str(login)
        return self.server.GET(path)[1]

    def admin_certificate(self):
        path = '/users/admin_certificate/'
        return self.server.GET(path)[1]
