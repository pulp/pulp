# -*- coding: utf-8 -*-

# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Utility functions to manage permissions and roles in pulp.
"""

from gettext import gettext as _

from pulp.server.api.permission import PermissionAPI
from pulp.server.api.role import RoleAPI
from pulp.server.api.user import UserApi
from pulp.server.auth.principal import (
    get_principal, is_system_principal, SystemPrincipal)
from pulp.server.exceptions import PulpException

_permission_api = PermissionAPI()
_role_api = RoleAPI()
_user_api = UserApi()


class PulpAuthorizationError(PulpException):
    pass

# operations api --------------------------------------------------------------

CREATE, READ, UPDATE, DELETE, EXECUTE = range(5)
operation_names = ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXECUTE']


# Temporarily moved this out of db into here; this is the only place using it
# and it's going to be deleted.

class Delta(dict):
    """
    The delta of a model object.
    Contains the primary key and keys/values specified in the filter.
    """

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __init__(self, obj, filter=()):
        """
        @param obj: A model object (dict).
        @type obj: Model|dict
        @param filter: A list of dictionary keys to include
            in the delta.
        @type filter: str|list
        """
        dict.__init__(self)
        if isinstance(filter, basestring):
            filter = (filter,)
        for k,v in obj.items():
            if k in filter:
                self[k] = v

def name_to_operation(name):
    """
    Convert a operation name to an operation value
    Returns None if the name does not correspond to an operation
    @type name: str
    @param name: operation name
    @rtype: int or None
    @return: operation value
    """
    name = name.upper()
    if name not in operation_names:
        return None
    return operation_names.index(name)


def names_to_operations(names):
    """
    Convert a list of operation names to operation values
    Returns None if there is any name that does not correspond to an operation
    @type name: list or tuple of str's
    @param names: names to convert to values
    @rtype: list of int's or None
    @return: list of operation values
    """
    operations = [name_to_operation(n) for n in names]
    if None in operations:
        return None
    return operations


def operation_to_name(operation):
    """
    Convert an operation value to an operation name
    Returns None if the operation value is invalid
    @type operation: int
    @param operation: operation value
    @rtype: str or None
    @return: operation name
    """
    if operation < CREATE or operation > EXECUTE:
        return None
    return operation_names[operation]

# utilities -------------------------------------------------------------------

def _get_user(user_name):
    """
    Get a user from the database that corresponds to the user name
    Raise an exception if the user isn't found
    @type user_name: str
    @param user_name: user's login
    @rtype: L{pulp.server.db.model.User} instance
    @return: user instance
    @raise L{PulpAuthorizationError}: if no user with name exists
    """
    user = _user_api.user(user_name)
    if user is None:
        raise PulpAuthorizationError(_('no such user: %s') % user_name)
    return user


def _get_role(role_name):
    """
    Get a role from the database that corresponds to the role name
    Raise an exceptoin if the role isn't found
    @type role_name: str
    @param role_name: role's name
    @rtype: L{pulp.server.db.model.Role} instance
    @return: role instance
    @raise L{PulpAuthorizationError}: if no user with role exists
    """
    role = _role_api.role(role_name)
    if role is None:
        raise PulpAuthorizationError(_('no such role: %s') % role_name)
    return role


def _get_operations(operation_names):
    """
    Get a list of operation values give a list of operation names
    Raise an exception if any of the names are invalid
    @type operation_names: list or tuple of str's
    @param operation_names: list of operation names
    @rtype: list of int's
    @return: list of operation values
    @raise L{PulpAuthorizationError}: on any invalid names
    """
    operations = names_to_operations(operation_names)
    if operations is None:
        raise PulpAuthorizationError(_('invalid operation name or names: %s') %
                            ', '.join(operation_names))
    return operations


def _get_users_belonging_to_role(role):
    """
    Get a list of users belonging to the given role
    @type role: L{pulp.server.db.model.Role} instance
    @param role: role to get members of
    @rtype: list of L{pulp.server.db.model.User} instances
    @return: list of users that are members of the given role
    """
    users = []
    for user in _user_api.users():
        if role['name'] in user['roles']:
            users.append(user)
    return users


def _get_other_roles(role, role_names):
    """
    Get a list of role instance corresponding to the role names, excluding the
    given role instance
    @type role: L{pulp.server.model.db.Role} instance
    @param role: role to exclude
    @type role_names: list or tuple of str's
    @rtype: list of L{pulp.server.model.db.Role} instances
    @return: list of roles
    """
    return [_get_role(n) for n in role_names if n != role['name']]


def _operations_not_granted_by_roles(resource, operations, roles):
    """
    Filter a list of operations on a resource, removing the operations that
    are granted to the resource by any role in a given list of roles
    @type resource: str
    @param resource: pulp resource
    @type operations: list or tuple of int's
    @param operations: operations pertaining to the resource
    @type roles: list or tuple of L{pulp.server.db.model.Role} instances
    @param roles: list of roles
    @rtype: list of int's
    @return: list of operations on resource not granted by the roles
    """
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
    """
    Grant the operations on the resource to the user
    @type resource: str
    @param resource: pulp resource to grant operations on
    @type user_name: str
    @param user_name: name of the user to grant permissions to
    @type operation_names: list or tuple of str's
    @param operation_names: name of the operations to grant
    @rtype: bool
    @return: True on success
    """
    user = _get_user(user_name)
    operations = _get_operations(operation_names)
    _permission_api.grant(resource, user, operations)
    return True


def grant_automatic_permissions_for_created_resource(resource):
    """
    Grant CRUDE permissions for a newly created resource to current principal.
    @type resource: str
    @param resource: resource path to grant permissions to
    @rtype: bool
    @return: True on success, False otherwise
    @raise RuntimeError: if the system principal has not been set
    """
    user = get_principal()
    if is_system_principal():
        raise RuntimeError(_('cannot grant auto permission on %s to %s') %
                           (resource, user))
    operations = [CREATE, READ, UPDATE, DELETE, EXECUTE]
    _permission_api.grant(resource, user, operations)
    return True


def grant_automatic_permissions_for_new_user(user_name):
    """
    Grant the permissions required for a new user so that they my log into Pulp
    and update their own information.
    @param user_name: name of the new user
    @type  user_name: str
    """
    user = _get_user(user_name)
    _permission_api.grant('/users/%s/' % user_name, user, [READ, UPDATE])
    _permission_api.grant('/users/admin_certificate/', user, [READ])


def grant_automatic_permissions_to_consumer_user(user_name):
    """
    Grant the permissions required by a consumer user.
    @type user_name: str
    @param user_name: name of the consumer user
    @type user_resource: str
    @param user_resource: the resource path for the consumer user
    @rtype: bool
    @return: True on success, False otherwise
    """
    user = _get_user(user_name)
    user_operations = [READ, UPDATE, DELETE, EXECUTE]
    _permission_api.grant('/consumers/%s/' % user_name, user, user_operations)


def revoke_permission_from_user(resource, user_name, operation_names):
    """
    Revoke the operations on the resource from the user
    @type resource: str
    @param resource: pulp resource to revoke operations on
    @type user_name: str
    @param user_name: name of the user to revoke permissions from
    @type operation_names: list or tuple of str's
    @param operation_names: name of the operations to revoke
    @rtype: bool
    @return: True on success
    """
    user = _get_user(user_name)
    operations = _get_operations(operation_names)
    _permission_api.revoke(resource, user, operations)
    return True


def revoke_all_permissions_from_user(user_name):
    """
    Revoke all the permissions from a given user
    @type user_name: str
    @param user_name: name of the user to revoke all permissions from
    @rtype: bool
    @return: True on success
    """
    user = _get_user(user_name)
    for permission in _permission_api.collection.find():
        if user['login'] not in permission['users']:
            continue
        del permission['users'][user['login']]
        _permission_api.update(permission['resource'],
                               {'users': permission['users']})
    return True


def grant_permission_to_role(resource, role_name, operation_names):
    """
    Grant the operations on the resource to the users in the given role
    @type resource: str
    @param resource: pulp resource to grant operations on
    @type role_name: str
    @param role_name: name of the role to grant permissions to
    @type operation_names: list or tuple of str's
    @param operation_names: name of the operations to grant
    @rtype: bool
    @return: True on success
    """
    check_builtin_roles(role_name)
    role = _get_role(role_name)
    users = _get_users_belonging_to_role(role)
    operations = _get_operations(operation_names)
    current_ops = role['permissions'].setdefault(resource, [])
    new_ops = []
    for op in operations:
        if op in current_ops:
            continue
        new_ops.append(op)
    _role_api.add_permissions(role, resource, new_ops)
    for user in users:
        _permission_api.grant(resource, user, operations)
    return True


def revoke_permission_from_role(resource, role_name, operation_names):
    """
    Revoke the operations on the resource from the users in the given role
    @type resource: str
    @param resource: pulp resource to revoke operations on
    @type role_name: str
    @param role_name: name of the role to revoke permissions from
    @type operation_names: list or tuple of str's
    @param operation_names: name of the operations to revoke
    @rtype: bool
    @return: True on success
    """
    check_builtin_roles(role_name)
    role = _get_role(role_name)
    if resource not in role['permissions']:
        return False
    operations = _get_operations(operation_names)
    _role_api.remove_permissions(role, resource, operations)
    users = _get_users_belonging_to_role(role)
    for user in users:
        other_roles = _get_other_roles(role, user['roles'])
        user_ops = _operations_not_granted_by_roles(resource,
                                                    operations,
                                                    other_roles)
        _permission_api.revoke(resource, user, user_ops)
    return True


def show_permissions(resource):
    """
    Get the permissions for a given resource
    Returns None if no permissions are found
    @type resource: str
    @param resource: pulp managed resource
    @rtype: L{pulp.server.db.model.Permission} instance or None
    @return: permissions for the given resource
    """
    return _permission_api.permission(resource)


class GrantPermissionsForTask(object):
    """
    Grant appropriate permissions to a task resource for the user that started
    the task.
    """

    def __init__(self):
        self.user_name = get_principal()['login']

    def __call__(self, task):
        if self.user_name == SystemPrincipal.LOGIN:
            return
        resource = '/tasks/%s/' % task.id
        operations = ['READ', 'DELETE']
        grant_permission_to_user(resource, self.user_name, operations)


class RevokePermissionsForTask(object):
    """
    Revoke the permissions for a task from the user that started the task.
    """

    def __init__(self):
        self.user_name = get_principal()['login']

    def __call__(self, task):
        if self.user_name == SystemPrincipal.LOGIN:
            return
        resource = '/tasks/%s/' % task.id
        operations = ['READ', 'DELETE']
        revoke_permission_from_user(resource, self.user_name, operations)


class GrantPermmissionsForTaskV2(GrantPermissionsForTask):

    def __call__(self, call_request, call_report):
        if self.user_name == SystemPrincipal.LOGIN:
            return
        resource = '/v2/tasks/%s/' % call_report.task_id
        operations = ['READ', 'DELETE']
        grant_permission_to_user(resource, self.user_name, operations)


class RevokePermissionsForTaskV2(RevokePermissionsForTask):

    def __call__(self, call_request, call_report):
        if self.user_name == SystemPrincipal.LOGIN:
            return
        resource = '/v2/tasks/%s/' % call_report.task_id
        operations = ['READ', 'DELETE']
        revoke_permission_from_user(resource, self.user_name, operations)

# role api --------------------------------------------------------------------

def create_role(role_name):
    """
    Create a role with the give name
    Raises and exception if the role already exists
    @type role_name: str
    @param role_name: name of role
    @rtype: bool
    @return: True on success
    """
    return _role_api.create(role_name)


def delete_role(role_name):
    """
    Delete a role. This has the side-effect of revoking any permissions granted
    to the role from the users in the role, unless those permissions are also
    granted through another role the user is a memeber of.
    @type role_name: name of the role to delete
    @param role_name: role name
    @rtype: bool
    @return: True on success
    """
    check_builtin_roles(role_name)
    role = _get_role(role_name)
    users = _get_users_belonging_to_role(role)
    for resource, operations in role['permissions'].items():
        for user in users:
            other_roles = _get_other_roles(role, user['roles'])
            user_ops = _operations_not_granted_by_roles(resource,
                                                        operations,
                                                        other_roles)
            _permission_api.revoke(resource, user, user_ops)
    for user in users:
        user['roles'].remove(role_name)
        _user_api.update(user['login'], Delta(user, 'roles'))
    _role_api.delete(role)
    return True


def add_user_to_role(role_name, user_name):
    """
    Add a user to a role. This has the side-effect of granting all the
    permissions granted to the role to the user.
    @type role_name: str
    @param role_name: name of role
    @type user_name: str
    @param user_name: name of user
    @rtype: bool
    @return: True on success
    """
    role = _get_role(role_name)
    user = _get_user(user_name)
    if role_name in user['roles']:
        return False
    user['roles'].append(role_name)
    _user_api.update(user['login'], Delta(user, 'roles'))
    for resource, operations in role['permissions'].items():
        _permission_api.grant(resource, user, operations)
    return True


def remove_user_from_role(role_name, user_name):
    """
    Remove a user from a role. This has the side-effect of revoking all the
    permissions granted to the role from the user, unless the permissions are
    also granted by another role.
    @type role_name: str
    @param role_name: name of role
    @type user_name: str
    @param suer_name: name of user
    @rtype: bool
    @return: True on success
    """
    role = _get_role(role_name)
    user = _get_user(user_name)
    if role_name == super_user_role and is_last_super_user(user):
        raise PulpAuthorizationError(_('%s cannot be empty, and %s is the last member') %
                                     (super_user_role, user_name))
    if role_name not in user['roles']:
        return False
    user['roles'].remove(role_name)
    _user_api.update(user['login'], Delta(user, 'roles'))
    for resource, operations in role['permissions'].items():
        other_roles = _get_other_roles(role, user['roles'])
        user_ops = _operations_not_granted_by_roles(resource,
                                                    operations,
                                                    other_roles)
        _permission_api.revoke(resource, user, user_ops)
    return True


def list_users_in_role(role_name):
    """
    Get a list of the users belonging to a role
    @type role_name: str
    @param role_name: name of role
    @rtype: list of L{pulp.server.db.model.User} instances
    @return: users belonging to the role
    """
    role = _get_role(role_name)
    return _get_users_belonging_to_role(role)

# built in roles --------------------------------------------------------------

super_user_role = 'super-users'
consumer_users_role = 'consumer-users'


def is_last_super_user(user):
    """
    Check to see if a user is the last super user
    @type user: L{pulp.server.db.model.User} instace
    @param user: user to check
    @rtype: bool
    @return: True if the user is the last super user, False otherwise
    @raise PulpException: if no super users are found
    """
    if super_user_role not in user['roles']:
        return False
    role = _role_api.role(super_user_role)
    users = _get_users_belonging_to_role(role)
    if not users:
        raise PulpException(_('no super users defined'))
    if len(users) >= 2:
        return False
    return users[0]['_id'] == user['_id'] # this should be True


def check_builtin_roles(role_name):
    """
    Check to see if a role name corresponds to a built in role, and raise an
    exception if it does
    @type role_name: str
    @param role_name: name of role to check
    @raise L{PulpAuthorizationError}: if the role name matches a built in role
    """
    if role_name not in (super_user_role, consumer_users_role):
        return
    raise PulpAuthorizationError(_('role %s cannot be changed') % role_name)


def _ensure_super_user_role():
    """
    Assure the super user role exists.
    """
    role = _role_api.role(super_user_role)
    if role is None:
        role = _role_api.create(super_user_role)
        _role_api.add_permissions(role, '/', [CREATE, READ, UPDATE, DELETE, EXECUTE])


def _ensure_consumer_user_role():
    """
    Assure the consumer role exists.
    """
    role = _role_api.role(consumer_users_role)
    if role is None:
        role = _role_api.create(consumer_users_role)
        _role_api.add_permissions(role, '/consumers/', [CREATE, READ]) # XXX not sure this is necessary
        _role_api.add_permissions(role, '/errata/', [READ])
        _role_api.add_permissions(role, '/repositories/', [READ])

def ensure_builtin_roles():
    """
    Assure the roles required for pulp's operation are in the database.
    """
    _ensure_super_user_role()
    _ensure_consumer_user_role()

# authorization api -----------------------------------------------------------

def is_superuser(user):
    """
    Return True if the user is a super user
    @type user: L{pulp.server.db.model.User} instance
    @param user: user to check
    @rtype: bool
    @return: True if the user is a super user, False otherwise
    """
    return super_user_role in user['roles']


def is_authorized(resource, user, operation):
    """
    Check to see if a user is authorized to perform an operation on a resource
    @type resource: str
    @param resource: pulp resource path
    @type user: L{pulp.server.db.model.User} instance
    @param user: user to check permissions for
    @type operation: int
    @param operation: operation to be performed on resource
    @rtype: bool
    @return: True if the user is authorized for the operation on the resource,
             False otherwise
    """
    if is_superuser(user):
        return True
    login = user['login']
    parts = [p for p in resource.split('/') if p]
    while parts:
        current_resource = '/%s/' % '/'.join(parts)
        permission = _permission_api.permission(current_resource)
        if permission is not None:
            if operation in permission['users'].get(login, []):
                return True
        parts = parts[:-1]
    permission = _permission_api.permission('/')
    return (permission is not None and
            operation in permission['users'].get(login, []))
