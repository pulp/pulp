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
import logging
from gettext import gettext as _

from pulp.server.auth.principal import (
    get_principal, is_system_principal, SystemPrincipal)
from pulp.server.exceptions import PulpException

from pulp.server.managers import factory

_log = logging.getLogger(__name__)

class PulpAuthorizationError(PulpException):
    pass

# operations api --------------------------------------------------------------

CREATE, READ, UPDATE, DELETE, EXECUTE = range(5)
operation_names = ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXECUTE']

# Temporarily moved this out of db into here; this is the only place using it
# and it's going to be deleted.

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
        user = factory.user_query_manager().find_by_login(self.user_name)
        factory.permission_manager().grant(resource, user, operations)


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
        user = factory.user_query_manager().find_by_login(self.user_name)
        factory.permission_manager().revoke(resource, user, operations)


class GrantPermmissionsForTaskV2(GrantPermissionsForTask):

    def __call__(self, call_request, call_report):
        if self.user_name == SystemPrincipal.LOGIN:
            return
        resource = '/v2/tasks/%s/' % call_report.task_id
        operations = ['READ', 'DELETE']
        user = factory.user_query_manager().find_by_login(self.user_name)
        factory.permission_manager().grant(resource, user, operations)


class RevokePermissionsForTaskV2(RevokePermissionsForTask):

    def __call__(self, call_request, call_report):
        if self.user_name == SystemPrincipal.LOGIN:
            return
        resource = '/v2/tasks/%s/' % call_report.task_id
        operations = ['READ', 'DELETE']

        user = factory.user_query_manager().find_by_login(self.user_name)
        factory.permission_manager().revoke(resource, user, operations)







