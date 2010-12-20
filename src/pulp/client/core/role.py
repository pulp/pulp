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

from pulp.client.connection import RoleConnection
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit

# base role action class ------------------------------------------------------

class RoleAction(Action):

    def setup_connections(self):
        self.role_conn = RoleConnection()

# role action classes ---------------------------------------------------------

class List(RoleAction):

    description = _('list current roles')

    def run(self):
        print_header(_('Available Roles'))
        for role in self.role_conn.list():
            print '  %s' % role


class Info(RoleAction):

    description = _('get information for a single role')

    def setup_parser(self):
        self.parser.add_option('--role', dest='role', help=_('role name'))

    def run(self):
        rolename = self.get_required_option('role')
        info = self.role_conn.info(rolename)
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

    description = _('create a new role')

    def setup_parser(self):
        self.parser.add_option('--role', dest='role', help=_('role name'))

    def run(self):
        rolename = self.get_required_option('role')
        if self.role_conn.create(rolename):
            print _('Role [ %s ] created') % rolename


class Delete(RoleAction):

    description = _('delete an existing role')

    def setup_parser(self):
        self.parser.add_option('--role', dest='role', help=_('role name'))

    def run(self):
        rolename = self.get_required_option('role')
        if self.role_conn.delete(rolename):
            print _('Role [ %s ] deleted') % rolename


class Add(RoleAction):

    description = _('add a user to a role')

    def setup_parser(self):
        self.parser.add_option('--role', dest='role', help=_('role name'))
        self.parser.add_option('--user', dest='user', help=_('user to add'))

    def run(self):
        rolename = self.get_required_option('role')
        username = self.get_required_option('user')
        if self.role_conn.add_user(rolename, username):
            print _('[ %s ] added to role [ %s ]') % (username, rolename)


class Remove(RoleAction):

    description = _('remove a user from a role')

    def setup_parser(self):
        self.parser.add_option('--role', dest='role', help=_('role name'))
        self.parser.add_option('--user', dest='user', help=_('user to remove'))

    def run(self):
        rolename = self.get_required_option('role')
        username = self.get_required_option('user')
        if self.role_conn.remove_user(rolename, username):
            print _('[ %s ] removed from role [ %s ]') % (username, rolename)

# role command ----------------------------------------------------------------

class Role(Command):

    description = _('manage pulp permission roles')
