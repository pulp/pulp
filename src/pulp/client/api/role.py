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
from pulp.client.api.server import ServerRequestError


class RoleAPI(PulpAPI):

    def list(self):
        path = '/roles/'
        return self.server.GET(path)[1]

    def info(self, rolename):
        path = '/roles/%s/' % rolename
        return self.server.GET(path)[1]

    def create(self, rolename):
        path = '/roles/'
        params = {'rolename': rolename}
        try:
            return self.server.PUT(path, params)[1]
        except ServerRequestError, e:
            print e.args[1]
            return False

    def delete(self, rolename):
        path = '/roles/%s/' % rolename
        try:
            return self.server.DELETE(path)[1]
        except ServerRequestError, e:
            print e.args[1]
            return False

    def add_user(self, rolename, username):
        path = '/roles/%s/add/' % rolename
        params = {'username': username}
        try:
            return self.server.POST(path, params)[1]
        except ServerRequestError, e:
            print e.args[1]
            return False

    def remove_user(self, rolename, username):
        path = '/roles/%s/remove/' % rolename
        params = {'username': username}
        try:
            return self.server.POST(path, params)[1]
        except ServerRequestError, e:
            print e.args[1]
            return False
