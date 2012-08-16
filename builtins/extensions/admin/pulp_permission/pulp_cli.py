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


from gettext import gettext as _
from pulp.client.extensions.extensions import PulpCliSection, PulpCliCommand, \
    PulpCliOption, PulpCliFlag, UnknownArgsParser
from pulp.bindings.exceptions import NotFoundException

# -- framework hook -----------------------------------------------------------

def initialize(context):
    permission_section = PermissionSection(context)
    context.cli.add_section(permission_section)

# -- common exceptions --------------------------------------------------------

class InvalidConfig(Exception):
    """
    During parsing of the user supplied arguments, this will indicate a
    malformed set of values. The message in the exception (e[0]) is formatted
    and i18n'ed to be displayed directly to the user.
    """
    pass

# -- sections -----------------------------------------------------------------

class PermissionSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'permission', 'permission lifecycle (list, grant, revoke, etc.) commands')

        self.context = context
        self.prompt = context.prompt # for easier access

        # List Command
        list_command = PulpCliCommand('list', 'lists permissions for a particular resource', self.list)
        list_command.add_option(PulpCliOption('--resource', 'uniquely identifies a resource', required=True))
        self.add_command(list_command)
        
        # Grant Command
        grant_command = PulpCliCommand('grant', 'grants resource permissions to given user or given role', self.grant)
        grant_command.add_option(PulpCliOption('--resource', 'resource REST API path whose permissions are being manipulated', required=True))
        grant_command.add_option(PulpCliOption('--login', 'login of the user to which access to given resource is being granted', required=False))
        grant_command.add_option(PulpCliOption('--role-id', 'id of the role to which access to given resource is being granted', required=False))
        grant_command.add_option(PulpCliOption('-o', 'type of permissions being granted', required=True, allow_multiple=True))
        self.add_command(grant_command)
        
        # Revoke Command
        revoke_command = PulpCliCommand('revoke', 'revokes resource permissions from given user or given role', self.revoke)
        revoke_command.add_option(PulpCliOption('--resource', 'resource REST API path whose permissions are being manipulated', required=True))
        revoke_command.add_option(PulpCliOption('--login', 'login of the user from which access to given resource is being revoked', required=False))
        revoke_command.add_option(PulpCliOption('--role-id', 'id of the role from which access to given resource is being revoked', required=False))
        revoke_command.add_option(PulpCliOption('-o', 'type of permissions being revoked', required=True, allow_multiple=True))
        self.add_command(revoke_command)

    
    def list(self, **kwargs):
        resource = kwargs['resource']
        self.prompt.render_title('Permissions for %s' % resource)
        permission = self.context.server.permission.permission(resource).response_body
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

