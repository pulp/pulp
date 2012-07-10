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
    user_section = UserSection(context)
    context.cli.add_section(user_section)

# -- common exceptions --------------------------------------------------------

class InvalidConfig(Exception):
    """
    During parsing of the user supplied arguments, this will indicate a
    malformed set of values. The message in the exception (e[0]) is formatted
    and i18n'ed to be displayed directly to the user.
    """
    pass

# -- sections -----------------------------------------------------------------

class UserSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'user', 'user lifecycle (list, create, update, etc.) commands')

        self.context = context
        self.prompt = context.prompt # for easier access

        # Common Options
        login_option = PulpCliOption('--login', 'uniquely identifies the user; only alphanumeric, -, and _ allowed', required=True)
        name_option = PulpCliOption('--name', 'user-readable full name of the user', required=False)

        # Create command
        create_command = PulpCliCommand('create', 'creates a user', self.create)
        create_command.add_option(login_option)
        create_command.add_option(PulpCliOption('--password', 'password for the new user, if you do not want to be prompted for one', required=False))
        create_command.add_option(name_option)
        self.add_command(create_command)

        # Update Command
        update_command = PulpCliCommand('update', 'changes metadata of an existing user', self.update)
        update_command.add_option(PulpCliOption('--login', 'identifies the user to be updated', required=True))
        update_command.add_option(name_option)
        self.add_command(update_command)

        # Delete Command
        delete_command = PulpCliCommand('delete', 'deletes a user', self.delete)
        delete_command.add_option(PulpCliOption('--login', 'identifies the user to be deleted', required=True))
        self.add_command(delete_command)

        # List Command
        list_command = PulpCliCommand('list', 'lists summary of users registered to the Pulp server', self.list)
        list_command.add_option(PulpCliFlag('--details', 'if specified, all the user information is displayed'))
        list_command.add_option(PulpCliOption('--fields', 'comma-separated list of user fields; if specified, only the given fields will displayed', required=False))
        self.add_command(list_command)

    def create(self, **kwargs):
        login = kwargs['login']
        if kwargs['password']:
            newpassword = kwargs['password']
        else:
            while True:
                newpassword = getpass.getpass("Enter password for user [%s] : " % login)
                newpassword_confirm = getpass.getpass("Re-enter password for user [%s]: " % login)
                if newpassword == "" or newpassword_confirm == "":
                    self.prompt.render_failure_message("User password cannot be empty")
                elif newpassword == newpassword_confirm:
                    break
                else:
                    self.prompt.render_failure_message("Passwords do not match")
        name = kwargs['name'] or login

        # Call the server
        self.context.server.user.create(login, newpassword, name)
        self.prompt.render_success_message('User [%s] successfully created' % login)

    def update(self, **kwargs):
        # Assemble the delta for all options that were passed in
        delta = dict([(k, v) for k, v in kwargs.items() if v is not None])
        delta.pop('login') # not needed in the delta

        try:
            self.context.server.user.update(kwargs['login'], delta)
            self.prompt.render_success_message('User [%s] successfully updated' % kwargs['login'])
        except NotFoundException:
            self.prompt.write('User [%s] does not exist on the server' % kwargs['login'], tag='not-found')

    def delete(self, **kwargs):
        login = kwargs['login']
        try:
            self.context.server.user.delete(login)
            self.prompt.render_success_message('User [%s] successfully deleted' % login)
        except NotFoundException:
            self.prompt.write('User [%s] does not exist on the server' % login, tag='not-found')

    def list(self, **kwargs):

        self.prompt.render_title('Users')

        user_list = self.context.server.user.users().response_body

        # Default flags to render_document_list
        filters = ['login', 'name']
        order = filters

        if kwargs['details'] is True:
            filters = None
            order = ['login', 'name']
        elif kwargs['fields'] is not None:
            filters = kwargs['fields'].split(',')
            if 'login' not in filters:
                filters.append('login')
            order = ['login']

        for u in user_list:
            self.prompt.render_document(u, filters=filters, order=order)

