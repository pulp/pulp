# -*- coding: utf-8 -*-

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

from gettext import gettext as _

import web

from pulp.server.auth import authorization
from pulp.server.db.model import Permission
from pulp.server.webservices.controllers.base import JSONController

# permissions controller ------------------------------------------------------

class Permissions(JSONController):

    def POST(self):
        try:
            resource = self.params()['resource']
        except KeyError:
            msg = _('expected parameter: resource')
            return self.bad_request(msg)
        perms = authorization.show_permissions(resource)
        if perms is None:
            perms = Permission(resource)
        else:
            users = perms['users']
            for user, ops in users.items():
                users[user] = [authorization.operation_to_name(o) for o in ops]
        return self.ok(perms)


class PermissionActions(JSONController):

    user_target = 'user'
    role_target = 'role'

    grant_action = 'grant'
    revoke_action = 'revoke'

    def _grant_to_user(self, data):
        try:
            user = data['username']
            resource = data['resource']
            ops = data['operations']
        except KeyError:
            msg = _('expected parameters: username, resource, operations')
            return self.bad_request(msg)
        val = authorization.grant_permission_to_user(resource, user, ops)
        return self.ok(val)

    def _revoke_from_user(self, data):
        try:
            user = data['username']
            resource = data['resource']
            ops = data['operations']
        except KeyError:
            msg = _('expected parameters: username, resource, operations')
            return self.bad_request(msg)
        val = authorization.revoke_permission_from_user(resource, user, ops)
        return self.ok(val)

    def _grant_to_role(self, data):
        try:
            role = data['rolename']
            resource = data['resource']
            ops = data['operations']
        except KeyError:
            msg = _('expected parameters: rolename, resource, operations')
            return self.bad_request(msg)
        val = authorization.grant_permission_to_role(resource, role, ops)
        return self.ok(val)

    def _revoke_from_role(self, data):
        try:
            role = data['rolename']
            resource = data['resource']
            ops = data['operations']
        except KeyError:
            msg = _('expected parameters: rolename, resource, operations')
            return self.bad_request(msg)
        val = authorization.revoke_permission_from_role(resource, role, ops)
        return self.ok(val)

    @JSONController.error_handler
    @JSONController.auth_required(super_user_only=True)
    def POST(self, target, action):
        try:
            return {
                (self.user_target, self.grant_action): self._grant_to_user,
                (self.user_target, self.revoke_action): self._revoke_from_user,
                (self.role_target, self.grant_action): self._grant_to_role,
                (self.role_target, self.revoke_action): self._revoke_from_role,
            }[(target, action)](self.params())
        except KeyError:
            msg = _('no permissions handler for target: %s; action: %s')
            return self.internal_server_error(msg % (target, action))
        except authorization.PulpAuthorizationError, e:
            return self.bad_request(e.args[0])

# web.py application ----------------------------------------------------------

urls = (
    '/show/', Permissions,
    '/(user|role)/(grant|revoke)/$', PermissionActions,
)

application = web.application(urls, globals())
