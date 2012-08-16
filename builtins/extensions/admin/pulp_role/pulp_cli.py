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
        id_option = PulpCliOption('--role-id', 'uniquely identifies the role; only alphanumeric, -, and _ allowed', required=True)

        # Create command
        create_command = PulpCliCommand('create', 'creates a role', self.create)
        create_command.add_option(id_option)
        create_command.add_option(PulpCliOption('--display-name', 'user-friendly name for the role', required=False))
        create_command.add_option(PulpCliOption('--description', 'user-friendly text describing the role', required=False))
        self.add_command(create_command)

        # Update command
        update_command = PulpCliCommand('update', 'updates a role', self.update)
        update_command.add_option(PulpCliOption('--role-id', 'identifies the role to be updated', required=True))
        update_command.add_option(PulpCliOption('--display-name', 'user-friendly name for the role', required=False))
        update_command.add_option(PulpCliOption('--description', 'user-friendly text describing the role', required=False))
        self.add_command(update_command)

        # Delete Command
        delete_command = PulpCliCommand('delete', 'deletes a role', self.delete)
        delete_command.add_option(PulpCliOption('--role-id', 'identifies the role to be deleted', required=True))
        self.add_command(delete_command)

        # List Command
        list_command = PulpCliCommand('list', 'lists summary of roles on the Pulp server', self.list)
        list_command.add_option(PulpCliFlag('--details', 'if specified, all the role information is displayed'))
        list_command.add_option(PulpCliOption('--fields', 'comma-separated list of role fields; if specified, only the given fields will displayed', required=False))
        self.add_command(list_command)
        
    def create(self, **kwargs):
        role_id = kwargs['role-id']
        display_name = None
        description = None
        if 'display-name' in kwargs:
            display_name = kwargs['display-name']
        if 'description' in kwargs:
            description = kwargs['description']

        # Call the server
        self.context.server.role.create(role_id, display_name, description)
        self.prompt.render_success_message('Role [%s] successfully created' % role_id)
        
    def update(self, **kwargs):
        role_id = kwargs['role-id']

        delta = {}
        if 'display-name' in kwargs:
            delta['display_name'] = kwargs['display-name']
        if 'description' in kwargs:
            delta['description'] = kwargs['description']
            
        # Call the server
        self.context.server.role.update(role_id, delta)
        self.prompt.render_success_message('Role [%s] successfully updated' % role_id)

    def delete(self, **kwargs):
        role_id = kwargs['role-id']
        try:
            self.context.server.role.delete(role_id)
            self.prompt.render_success_message('Role [%s] successfully deleted' % role_id)
        except NotFoundException:
            self.prompt.write('Role [%s] does not exist on the server' % role_id, tag='not-found')

    def list(self, **kwargs):

        self.prompt.render_title('Roles')

        role_list = self.context.server.role.roles().response_body

        # Default flags to render_document_list
        filters = ['id', 'users']
        order = filters

        if kwargs['details'] is True:
            filters = ['id','display_name','description','users','permissions']
            order = filters
        elif kwargs['fields'] is not None:
            filters = kwargs['fields'].split(',')
            if 'id' not in filters:
                filters.append('id')
            order = ['id']

        for r in role_list:
            self.prompt.render_document(r, filters=filters, order=order)
            
class UserSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'user', _('add/remove user from the role'))
        
        self.context = context
        self.prompt = context.prompt # for easier access
        
        # Common Options
        id_option = PulpCliOption('--role-id', 'identifies the role', required=True)
        login_option = PulpCliOption('--login', 'identifies the user', required=True)
        
        # AddUser command
        add_user_command = PulpCliCommand('add', 'adds user to a role', self.add_user)
        add_user_command.add_option(id_option)
        add_user_command.add_option(login_option)
        self.add_command(add_user_command)
        
        # RemoveUser command
        remove_user_command = PulpCliCommand('remove', 'removes user from a role', self.remove_user)
        remove_user_command.add_option(id_option)
        remove_user_command.add_option(login_option)
        self.add_command(remove_user_command)
        
    def add_user(self, **kwargs):
        role_id = kwargs['role-id']
        login = kwargs['login']

        # Call the server
        self.context.server.role.add_user(role_id, login)
        self.prompt.render_success_message('User [%s] successfully added to role [%s]' % (login, role_id))

    def remove_user(self, **kwargs):
        role_id = kwargs['role-id']
        login = kwargs['login']

        # Call the server
        self.context.server.role.remove_user(role_id, login)
        self.prompt.render_success_message('User [%s] successfully removed from role [%s]' % (login, role_id))

