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

import os
from gettext import gettext as _

from pulp.client.extensions.extensions import PulpCliSection, PulpCliCommand, \
    PulpCliOption, PulpCliFlag
from pulp.bindings.exceptions import NotFoundException
from pulp.client import validators
from pulp.client.commands.criteria import CriteriaCommand

# -- framework hook -----------------------------------------------------------

def initialize(context):
    auth_section = AuthSection(context)
    context.cli.add_section(auth_section)

# -- common exceptions --------------------------------------------------------

class InvalidConfig(Exception):
    """
    During parsing of the user supplied arguments, this will indicate a
    malformed set of values. The message in the exception (e[0]) is formatted
    and i18n'ed to be displayed directly to the user.
    """
    pass

# -- sections -----------------------------------------------------------------

class AuthSection(PulpCliSection):

    def __init__(self, context):
        """
        @param context: pre-populated context that is given to the extensions by loader
        @type  context: pulp.client.extensions.core.ClientContext
        """
        PulpCliSection.__init__(self, 'auth', _('manage users, roles and permissions'))

        self.context = context
        self.prompt = context.prompt # for easier access

        # Subsections
        self.add_subsection(UserSection(context))
        role_section = RoleSection(context)
        role_section.add_subsection(RoleUserSection(context))
        self.add_subsection(role_section)
        self.add_subsection(PermissionSection(context))

# -- user sections -----------------------------------------------------------

class UserSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'user', 'manage users')

        self.context = context
        self.prompt = context.prompt # for easier access

        # Common Options
        login_option = PulpCliOption('--login', 'uniquely identifies the user; only alphanumeric, -, ., and _ allowed',
                                     required=True, validate_func=validators.id_validator_allow_dots)
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
        update_command.add_option(PulpCliOption('--password', 'new password for the user, use -p if you want to be prompted for the password', required=False))
        update_command.add_option(PulpCliFlag('-p', 'if specified, you will be prompted to enter new password for the user'))
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
        
        # Search Command
        self.add_command(CriteriaCommand(self.search, include_search=True))

    def create(self, **kwargs):
        login = kwargs['login']
        if kwargs['password']:
            password = kwargs['password']
        else:
            # Hidden, interactive prompt for the password if not specified
            prompt_msg = "Enter password for user [%s] : " % login
            verify_msg = "Re-enter password for user [%s]: " % login
            unmatch_msg = "Passwords do not match"
            password = self.context.prompt.prompt_password(_(prompt_msg), _(verify_msg), _(unmatch_msg))
            if password is self.context.prompt.ABORT:
                self.context.prompt.render_spacer()
                self.context.prompt.write(_('Create user cancelled'))
                return os.EX_NOUSER

        name = kwargs['name'] or login

        # Call the server
        self.context.server.user.create(login, password, name)
        self.prompt.render_success_message('User [%s] successfully created' % login)

    def update(self, **kwargs):
        # Assemble the delta for all options that were passed in
        delta = dict([(k, v) for k, v in kwargs.items() if v is not None])
        login = delta.pop('login') # not needed in the delta
        if not delta.has_key('password'):
            if kwargs['p'] is True:
                # Hidden, interactive prompt for the password
                prompt_msg = "Enter new password for user [%s] : " % login
                verify_msg = "Re-enter new password for user [%s]: " % login
                unmatch_msg = "Passwords do not match"
                password = self.context.prompt.prompt_password(_(prompt_msg), _(verify_msg), _(unmatch_msg))
                if password is self.context.prompt.ABORT:
                    self.context.prompt.render_spacer()
                    self.context.prompt.write(_('Update user cancelled'))
                    return os.EX_NOUSER
                delta['password'] = password

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
            filters = ['login', 'name', 'roles']
            order = ['login', 'name']
        elif kwargs['fields'] is not None:
            filters = kwargs['fields'].split(',')
            if 'login' not in filters:
                filters.append('login')
            order = ['login']

        for u in user_list:
            self.prompt.render_document(u, filters=filters, order=order)

    def search(self, **kwargs):
        user_list = self.context.server.user_search.search(**kwargs)
        for user in user_list:
            self.prompt.render_document(user)

# -- role sections -----------------------------------------------------------

class RoleSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'role', 'manage user roles')

        self.context = context
        self.prompt = context.prompt # for easier access

        # Common Options
        id_option = PulpCliOption('--role-id', 'uniquely identifies the role; only alphanumeric, -, and _ allowed', required=True, validate_func=validators.id_validator)

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
            
class RoleUserSection(PulpCliSection):

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

# -- permission sections -------------------------------------------------------

class PermissionSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'permission', 'manage granting, revoking and listing permissions for resources')

        self.context = context
        self.prompt = context.prompt # for easier access

        # List Command
        list_command = PulpCliCommand('list', 'lists permissions for a particular resource', self.list)
        list_command.add_option(PulpCliOption('--resource', 'uniquely identifies a resource', required=True))
        self.add_command(list_command)
        
        # Grant Command
        usage_description = 'you can specify either login or role-id in this command; both cannot be specified at the same time'
        grant_command = PulpCliCommand('grant', 'grants resource permissions to given user or given role', self.grant, usage_description=usage_description)
        grant_command.add_option(PulpCliOption('--resource', 'resource REST API path whose permissions are being manipulated', required=True))
        grant_command.add_option(PulpCliOption('--login', 'login of the user to which access to given resource is being granted', required=False))
        grant_command.add_option(PulpCliOption('--role-id', 'id of the role to which access to given resource is being granted', required=False))
        grant_command.add_option(PulpCliOption('-o', 'type of permissions being granted, valid permissions: create, read, update, delete, execute', required=True, allow_multiple=True))
        self.add_command(grant_command)
        
        # Revoke Command
        revoke_command = PulpCliCommand('revoke', 'revokes resource permissions from given user or given role', self.revoke, usage_description=usage_description)
        revoke_command.add_option(PulpCliOption('--resource', 'resource REST API path whose permissions are being manipulated', required=True))
        revoke_command.add_option(PulpCliOption('--login', 'login of the user from which access to given resource is being revoked', required=False))
        revoke_command.add_option(PulpCliOption('--role-id', 'id of the role from which access to given resource is being revoked', required=False))
        revoke_command.add_option(PulpCliOption('-o', 'type of permissions being revoked, valid permissions: create, read, update, delete, execute', required=True, allow_multiple=True))
        self.add_command(revoke_command)

    
    def list(self, **kwargs):
        resource = kwargs['resource']
        self.prompt.render_title('Permissions for %s' % resource)
        permissions = self.context.server.permission.permission(resource).response_body
        if permissions:
            permission = permissions[0]
            if 'users' in permission:
                self.prompt.render_document(permission['users'])
            

    def grant(self, **kwargs):
        resource = kwargs['resource']
        login = kwargs['login'] or None
        role_id = kwargs['role-id'] or None
        operations = [o.upper() for o in kwargs['o']]
        
        if login is None and role_id is None:
            self.prompt.render_failure_message('No user login or role id specified to grant permissions to.')
            return

        if login and role_id:
            self.prompt.render_failure_message('Both user login and role id specified. Please specify either user login OR role id.')
            return

        if login:
            self.context.server.permission.grant_to_user(resource, login, operations)
            self.prompt.render_success_message('Permissions [%s : %s] successfully granted to user [%s]' % (resource, operations, login))
        else:
            self.context.server.permission.grant_to_role(resource, role_id, operations)
            self.prompt.render_success_message('Permissions [%s : %s] successfully granted to role [%s]' % (resource, operations, role_id))

    def revoke(self, **kwargs):
        resource = kwargs['resource']
        login = kwargs['login'] or None
        role_id = kwargs['role-id'] or None
        operations = [o.upper() for o in kwargs['o']]
        
        if login is None and role_id is None:
            self.prompt.render_failure_message('No user login or role id specified to revoke permissions from.')
            return

        if login and role_id:
            self.prompt.render_failure_message('Both user login and role id specified. Please specify either user login OR role id.')
            return

        if login:
            self.context.server.permission.revoke_from_user(resource, login, operations)
            self.prompt.render_success_message('Permissions [%s : %s] successfully revoked from user [%s]' % (resource, operations, login))
        else:
            self.context.server.permission.revoke_from_role(resource, role_id, operations)
            self.prompt.render_success_message('Permissions [%s : %s] successfully revoked from role [%s]' % (resource, operations, role_id))

