# -*- coding: utf-8 -*-

"""
Utility functions to manage permissions and roles in pulp.
"""

import logging

_log = logging.getLogger(__name__)

# operation names and values --------------------------------------------------

OPERATION_NAMES = ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXECUTE']
CREATE = 0
READ = 1
UPDATE = 2
DELETE = 3
EXECUTE = 4

# utilities -------------------------------------------------------------------


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
        permissions = {}
        for item in role['permissions']:
            permissions[item['resource']] = item['permission']
        if resource not in permissions:
            continue
        for operation in culled_ops[:]:
            if operation in permissions[resource]:
                culled_ops.remove(operation)
    return culled_ops


def _lookup_operation_name(operation_value):
    """
    Returns the human readable name for a given operation numerical value.

    :param operation_value: The operation value
    :type operation_value: int

    :return: The human readable name as a string corresponding to the given
             operation numerical value.
    :raises: KeyError if operation_value does not have a corresponding name.
    """
    if operation_value == CREATE:
        return 'CREATE'
    if operation_value == READ:
        return 'READ'
    if operation_value == UPDATE:
        return 'UPDATE'
    if operation_value == DELETE:
        return 'DELETE'
    if operation_value == EXECUTE:
        return 'EXECUTE'
    msg_string = 'Could not find a valid name for authorization value %s'
    raise KeyError(msg_string % operation_value)
