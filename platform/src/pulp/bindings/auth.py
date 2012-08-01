# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.bindings.base import PulpAPI


class UserAPI(PulpAPI):
    """
    Connection class to access user specific calls
    """
    def __init__(self, pulp_connection):
        super(UserAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/users/"

    def users(self):
        path = self.base_path
        return self.server.GET(path)

    def create(self, login, password, name=None, roles=None):
        path = self.base_path
        userdata = {"login": login,
                    "password": password,
                    "name": name,
                    "roles": roles,}
        return self.server.POST(path, userdata)

    def user(self, login):
        path = self.base_path + ("%s/" % login)
        return self.server.GET(path)

    def delete(self, login):
        path = self.base_path + "%s/" % login
        return self.server.DELETE(path)

    def update(self, login, delta):
        path = self.base_path + "%s/" % login
        body = {'delta' : delta}
        return self.server.PUT(path, body)

class RoleAPI(PulpAPI):
    """
    Connection class to access role specific calls
    """
    def __init__(self, pulp_connection):
        super(RoleAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/roles/"

    def roles(self):
        path = self.base_path
        return self.server.GET(path)

    def create(self, name):
        path = self.base_path
        roledata = {"name": name}
        return self.server.POST(path, roledata)

    def role(self, name):
        path = self.base_path + ("%s/" % name)
        return self.server.GET(path)

    def delete(self, name):
        path = self.base_path + "%s/" % name
        return self.server.DELETE(path)

    def update(self, name, delta):
        path = self.base_path + "%s/" % name
        body = {'delta' : delta}
        return self.server.PUT(path, body)
    
    def add_user(self, name, login):
        path = self.base_path + "%s/" % name + 'users/'
        data = {"login": login}
        return self.server.POST(path, data)
    
    def remove_user(self, name, login):
        path = self.base_path + "%s/" % name + 'users/' +  "%s/" % login
        return self.server.DELETE(path)

