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

import os
from gettext import gettext as _

from pulp.client.api.permission import PermissionAPI
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit

# base permission action class ------------------------------------------------

class PermissionAction(Action):

    def __init__(self):
        super(PermissionAction, self).__init__()
        self.permission_api = PermissionAPI()

    def setup_parser(self):
        self.parser.add_option('--resource', dest='resource',
                               help=_('pulp resource'))
        self.parser.add_option('--user', action='append', dest='users',
                               default=[], help=_('pulp user'))
        self.parser.add_option('--role', action='append', dest='roles',
                               default=[], help=_('pulp user role'))
        self.parser.add_option('-o', '--operation', action='append',
                               dest='operations', default=[],
                               help=_('operations for resource'))

# permission actions ----------------------------------------------------------

class Show(PermissionAction):

    description = _('show permissions for a resource')

    def setup_parser(self):
        self.parser.add_option('--resource', dest='resource',
                               help=_('pulp resource'))

    def run(self):
        resource = self.get_required_option('resource')
        perms = self.permission_api.show_permissions(resource)
        if perms is None:
            system_exit(os.EX_SOFTWARE)
        print_header(_('Permissions for %s') % resource)
        for user, operations in perms['users'].items():
            print '  %s                \t%-25s' % (user, ', '.join(operations))


class Grant(PermissionAction):

    description = _('grant permissions to pulp users or roles')

    def run(self):
        resource = self.get_required_option('resource')
        operations = self.get_required_option('operations', 'operation')
        operations = [o.upper() for o in operations]
        for user in self.opts.users:
            success = self.permission_api.grant_permission_to_user(resource,
                                                              user,
                                                              operations)
            if not success:
                continue
            print _('Operations %s granted to user [ %s ] on resource [ %s ]') % \
                    (str(operations), user, resource)
        for role in self.opts.roles:
            success = self.permission_api.grant_permission_to_role(resource,
                                                              role,
                                                              operations)
            if not success:
                continue
            print _('Operations %s granted to role [ %s ] on resource [ %s ]') % \
                    (str(operations), role, resource)


class Revoke(PermissionAction):

    description = _('revoke permissions from pulp users or roles')

    def run(self):
        resource = self.get_required_option('resource')
        operations = self.get_required_option('operations', 'operation')
        operations = [o.upper() for o in operations]
        for user in self.opts.users:
            success = self.permission_api.revoke_permission_from_user(resource,
                                                                 user,
                                                                 operations)
            if not success:
                continue
            print _('Operations %s revoked from user [ %s ] on resource [ %s ]') % \
                    (str(operations), user, resource)
        for role in self.opts.roles:
            success = self.permission_api.revoke_permission_from_role(resource,
                                                                 role,
                                                                 operations)
            if not success:
                continue
            print _('Operations %s revoked from role [ %s ] on resource [ %s ]') % \
                    (str(operations), role, resource)

# permission command ----------------------------------------------------------

class Permission(Command):

    description = _('manage pulp permissions')
