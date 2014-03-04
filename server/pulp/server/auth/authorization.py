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
        permissions = role['permissions']
        if resource not in permissions:
            continue
        for operation in culled_ops[:]:
            if operation in permissions[resource]:
                culled_ops.remove(operation)
    return culled_ops
