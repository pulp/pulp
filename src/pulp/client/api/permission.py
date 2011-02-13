# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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

from pulp.client.api.base import PulpAPI
from pulp.client.server.base import ServerRequestError


class PermissionAPI(PulpAPI):

    def show_permissions(self, resource):
        path = '/permissions/show/'
        params = {'resource': resource}
        try:
            return self.server.POST(path, params)
        except ServerRequestError, e:
            print e.args[1]
            return None

    def grant_permission_to_user(self, resource, username, operations):
        path = '/permissions/user/grant/'
        params = {'username': username,
                  'resource': resource,
                  'operations': operations}
        try:
            return self.server.POST(path, params)
        except ServerRequestError, e:
            print e.args[1]
            return False

    def revoke_permission_from_user(self, resource, username, operations):
        path = '/permissions/user/revoke/'
        params = {'username': username,
                  'resource': resource,
                  'operations': operations}
        try:
            return self.server.POST(path, params)
        except ServerRequestError, e:
            print e.args[1]
            return False

    def grant_permission_to_role(self, resource, rolename, operations):
        path = '/permissions/role/grant/'
        params = {'rolename': rolename,
                  'resource': resource,
                  'operations': operations}
        try:
            return self.server.POST(path, params)
        except ServerRequestError, e:
            print e.args[1]
            return False

    def revoke_permission_from_role(self, resource, rolename, operations):
        path = '/permissions/role/revoke/'
        params = {'rolename': rolename,
                  'resource': resource,
                  'operations': operations}
        try:
            return self.server.POST(path, params)
        except ServerRequestError, e:
            print e.args[1]
            return False

