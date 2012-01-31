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


class PermissionAPI(PulpAPI):

    def show_permissions(self, resource):
        path = '/permissions/show/'
        params = {'resource': resource}
        try:
            return self.server.POST(path, params)[1]
        except ServerRequestError, e:
            print e.args[1]
            return None

    def grant_permission_to_user(self, resource, username, operations):
        path = '/permissions/user/grant/'
        params = {'username': username,
                  'resource': resource,
                  'operations': operations}
        try:
            return self.server.POST(path, params)[1]
        except ServerRequestError, e:
            print e.args[1]
            return False

    def revoke_permission_from_user(self, resource, username, operations):
        path = '/permissions/user/revoke/'
        params = {'username': username,
                  'resource': resource,
                  'operations': operations}
        try:
            return self.server.POST(path, params)[1]
        except ServerRequestError, e:
            print e.args[1]
            return False

    def grant_permission_to_role(self, resource, rolename, operations):
        path = '/permissions/role/grant/'
        params = {'rolename': rolename,
                  'resource': resource,
                  'operations': operations}
        try:
            return self.server.POST(path, params)[1]
        except ServerRequestError, e:
            print e.args[1]
            return False

    def revoke_permission_from_role(self, resource, rolename, operations):
        path = '/permissions/role/revoke/'
        params = {'rolename': rolename,
                  'resource': resource,
                  'operations': operations}
        try:
            return self.server.POST(path, params)[1]
        except ServerRequestError, e:
            print e.args[1]
            return False

