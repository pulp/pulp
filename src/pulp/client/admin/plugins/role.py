# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
from gettext import gettext as _

from pulp.client.admin.plugin import AdminPlugin
from pulp.client.api.role import RoleAPI
from pulp.client.lib.utils import print_header, system_exit
from pulp.client.pluginlib.command import Action, Command

# base role action class ------------------------------------------------------

class RoleAction(Action):

    def __init__(self, cfg):
        super(RoleAction, self).__init__(cfg)
        self.role_api = RoleAPI()

# role action classes ---------------------------------------------------------

class List(RoleAction):

    name = "list"
    description = _('list current roles')

    def run(self):
        print_header(_('Available Roles'))
        for role in self.role_api.list():
            print '  %s' % role


class Info(RoleAction):

    name = "info"
    description = _('get information for a single role')

    def setup_parser(self):
        self.parser.add_option('--role', dest='role', help=_('role name'))

    def run(self):
        rolename = self.get_required_option('role')
        info = self.role_api.info(rolename)
        if not info:
            system_exit(os.EX_DATAERR)
        print_header(_('Role Information for %s') % rolename)
        print 'Name                \t%-25s' % info['name']
        print 'Users               \t%-25s' % ', '.join(u for u in info['users'])
        print 'Permissions:'
        for resource, operations in info['permissions'].items():
            op_list = ', '.join(operations)
            print '  %s                \t%-25s' % (resource, op_list)


class Create(RoleAction):

    name = "create"
    description = _('create a new role')

    def setup_parser(self):
        self.parser.add_option('--role', dest='role', help=_('role name'))

    def run(self):
        rolename = self.get_required_option('role')
        if self.role_api.create(rolename):
            print _('Role [ %s ] created') % rolename


class Delete(RoleAction):

    name = "delete"
    description = _('delete an existing role')

    def setup_parser(self):
        self.parser.add_option('--role', dest='role', help=_('role name'))

    def run(self):
        rolename = self.get_required_option('role')
        if self.role_api.delete(rolename):
            print _('Role [ %s ] deleted') % rolename


class Add(RoleAction):

    name = "add"
    description = _('add a user to a role')

    def setup_parser(self):
        self.parser.add_option('--role', dest='role', help=_('role name'))
        self.parser.add_option('--user', dest='user', help=_('user to add'))

    def run(self):
        rolename = self.get_required_option('role')
        username = self.get_required_option('user')
        if self.role_api.add_user(rolename, username):
            print _('[ %s ] added to role [ %s ]') % (username, rolename)


class Remove(RoleAction):

    name = "remove"
    description = _('remove a user from a role')

    def setup_parser(self):
        self.parser.add_option('--role', dest='role', help=_('role name'))
        self.parser.add_option('--user', dest='user', help=_('user to remove'))

    def run(self):
        rolename = self.get_required_option('role')
        username = self.get_required_option('user')
        if self.role_api.remove_user(rolename, username):
            print _('[ %s ] removed from role [ %s ]') % (username, rolename)

# role command ----------------------------------------------------------------

class Role(Command):

    name = "role"
    description = _('manage pulp permission roles')

    actions = [ List,
                Info,
                Create,
                Delete,
                Add,
                Remove ]

# role plugin ----------------------------------------------------------------

class RolePlugin(AdminPlugin):

    name = "role"
    commands = [ Role ]
