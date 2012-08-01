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

import time
import getpass

from gettext import gettext as _
from pulp.client.extensions.extensions import PulpCliSection, PulpCliCommand, \
    PulpCliOption, PulpCliFlag, UnknownArgsParser
from pulp.bindings.exceptions import NotFoundException

# -- framework hook -----------------------------------------------------------

def initialize(context):
    role_section = RoleSection(context)
    role_section.add_subsection(UserSection(context))
    context.cli.add_section(role_section)

# -- common exceptions --------------------------------------------------------

class InvalidConfig(Exception):
    """
    During parsing of the user supplied arguments, this will indicate a
    malformed set of values. The message in the exception (e[0]) is formatted
    and i18n'ed to be displayed directly to the user.
    """
    pass

# -- sections -----------------------------------------------------------------

class RoleSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'role', 'role lifecycle (list, create, update, etc.) commands')

        self.context = context
        self.prompt = context.prompt # for easier access

        # Common Options
        name_option = PulpCliOption('--name', 'uniquely identifies the role; only alphanumeric, -, and _ allowed', required=True)

        # Create command
        create_command = PulpCliCommand('create', 'creates a role', self.create)
        create_command.add_option(name_option)
        self.add_command(create_command)

        # Delete Command
        delete_command = PulpCliCommand('delete', 'deletes a role', self.delete)
        delete_command.add_option(PulpCliOption('--name', 'identifies the role to be deleted', required=True))
        self.add_command(delete_command)

        # List Command
        list_command = PulpCliCommand('list', 'lists summary of roles on the Pulp server', self.list)
        list_command.add_option(PulpCliFlag('--details', 'if specified, all the role information is displayed'))
        list_command.add_option(PulpCliOption('--fields', 'comma-separated list of role fields; if specified, only the given fields will displayed', required=False))
        self.add_command(list_command)
        
        # 

    def create(self, **kwargs):
        name = kwargs['name']

        # Call the server
        self.context.server.role.create(name)
        self.prompt.render_success_message('Role [%s] successfully created' % name)

    def delete(self, **kwargs):
        name = kwargs['name']
        try:
            self.context.server.role.delete(name)
            self.prompt.render_success_message('Role [%s] successfully deleted' % name)
        except NotFoundException:
            self.prompt.write('Role [%s] does not exist on the server' % name, tag='not-found')

    def list(self, **kwargs):

        self.prompt.render_title('Roles')

        role_list = self.context.server.role.roles().response_body

        # Default flags to render_document_list
        filters = ['name']
        order = filters

        if kwargs['details'] is True:
            filters = ['name','users','permissions']
            order = filters
        elif kwargs['fields'] is not None:
            filters = kwargs['fields'].split(',')
            if 'name' not in filters:
                filters.append('name')
            order = ['name']

        for r in role_list:
            self.prompt.render_document(r, filters=filters, order=order)
            
class UserSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'user', _('add/remove user from the role'))
        
        self.context = context
        self.prompt = context.prompt # for easier access
        
        # Common Options
        name_option = PulpCliOption('--name', 'identifies the role', required=True)
        login_option = PulpCliOption('--login', 'identifies the user', required=True)
        
        # AddUser command
        add_user_command = PulpCliCommand('add', 'adds user to a role', self.add_user)
        add_user_command.add_option(name_option)
        add_user_command.add_option(login_option)
        self.add_command(add_user_command)
        
        # RemoveUser command
        remove_user_command = PulpCliCommand('remove', 'removes user from a role', self.remove_user)
        remove_user_command.add_option(name_option)
        remove_user_command.add_option(login_option)
        self.add_command(remove_user_command)
        
    def add_user(self, **kwargs):
        name = kwargs['name']
        login = kwargs['login']

        # Call the server
        self.context.server.role.add_user(name, login)
        self.prompt.render_success_message('User [%s] successfully added to role [%s]' % (login, name))

    def remove_user(self, **kwargs):
        name = kwargs['name']
        login = kwargs['login']

        # Call the server
        self.context.server.role.remove_user(name, login)
        self.prompt.render_success_message('User [%s] successfully removed from role [%s]' % (login, name))

