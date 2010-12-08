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

"""
Utility functions to manage permissions and roles in pulp.
"""

from gettext import gettext as _

from pulp.server.api.permission import PermissionAPI
from pulp.server.api.role import RoleAPI
from pulp.server.api.user import UserApi
from pulp.server.pexceptions import PulpException


_permission_api = PermissionAPI()
_role_api = RoleAPI()
_user_api = UserApi()

# operations api --------------------------------------------------------------

CREATE, READ, UPDATE, DELETE, EXECUTE = range(5)
operation_names = ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXECUTE']


def name_to_operation(name):
    name = name.upper()
    if name not in operation_names:
        return None
    return operation_names.index(name)


def names_to_operations(names):
    operations = [name_to_operation(n) for n in names]
    if None in operations:
        return None
    return operations


def operation_to_name(operation):
    return operation_names[operation]

# utilities -------------------------------------------------------------------

def _get_user(user_name):
    user = _user_api.user(user_name)
    if user is None:
        raise PulpException(_('no such user: %s') % user_name)
    return user


def _get_role(role_name):
    role = _role_api.role(role_name)
    if role is None:
        raise PulpException(_('no such role: %s') % role_name)
    return role


def _get_operations(operation_names):
    operations = names_to_operations(operation_names)
    if operations is None:
        raise PulpException(_('invalid operation name or names: %s') %
                            ', '.join(operation_names))
    return operations


def _get_users_belonging_to_role(role):
    users = []
    for user in _user_api.users():
        if role['name'] in user['roles']:
            users.append(user)
    return users


def _get_other_roles(role, role_names):
    return [_get_role(n) for n in role_names if n != role['name']]


def _operations_not_granted_by_roles(resource, operations, roles):
    culled_ops = operations[:]
    for role in roles:
        permissions = role['permissions']
        if resource not in permissions:
            continue
        for operation in culled_ops[:]:
            if operation in permissions[resource]:
                culled_ops.remove(operation)
    return culled_ops

# permissions api -------------------------------------------------------------

def grant_permission_to_user(resource, user_name, operation_names):
    user = _get_user(user_name)
    operations = _get_operations(operation_names)
    _permission_api.grant(resource, user, operations)
    return True


def revoke_permission_from_user(resource, user_name, operation_names):
    user = _get_user(user_name)
    operations = _get_operations(operation_names)
    _permission_api.revoke(resource, user, operations)
    return True


def grant_permission_to_role(resource, role_name, operation_names):
    role = _get_role(role_name)
    users = _get_users_belonging_to_role(role)
    operations = _get_operations(operation_names)
    for user in users:
        _permission_api.grant(resource, user, operations)
    return True


def revoke_permissions_from_role(resource, role_name, operations_name):
    role = _get_role(role_name)
    users = _get_users_belonging_to_role(role)
    operations = _get_operations(operation_names)
    for user in users:
        other_roles = _get_other_roles(role, user['roles'])
        user_ops = _operations_not_granted_by_roles(resource,
                                                    operations,
                                                    other_roles)
        _permission_api.revoke(resource, user, user_ops)
    return True


def show_permissions(resource):
    return _permission_api.permission(resource)

# role api --------------------------------------------------------------------

def create_role(role_name):
    _role_api.create(role_name)
    return True


def delete_role(role_name):
    role = _get_role(role_name)
    users = _get_users_belonging_to_role(role)
    for resource, operations in role['permissions'].items():
        for user in users:
            other_roles = _get_other_roles(role, user['roles'])
            user_ops = _operations_not_granted_by_roles(resource,
                                                        operations,
                                                        other_roles)
            _permission_api.revoke(resource, user, user_ops)
    _role_api.delete(role)
    return True


def add_user_to_role(role_name, user_name):
    role = _get_role(role_name)
    user = _get_user(user_name)
    for resource, operations in role['premissions'].items():
        _permission_api.grant(resource, user, operations)
    return True


def remove_user_from_role(role_name, user_name):
    role = _get_role(role_name)
    user = _get_user(user_name)
    for resource, operations in role['permissions'].items():
        other_roles = _get_other_roles(role, user['roles'])
        user_ops = _operations_not_granted_by_roles(resource,
                                                    operations,
                                                    other_roles)
        _permission_api.revoke(resource, user, user_ops)
    return True


def list_users_in_role(role_name):
    role = _get_role(role_name)
    return _get_users_belonging_to_role(role)
