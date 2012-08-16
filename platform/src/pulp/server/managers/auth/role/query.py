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

"""
Contains roles query classes
"""
from gettext import gettext as _

from pulp.server.db.model.auth import Role
from logging import getLogger

# -- constants ----------------------------------------------------------------

_LOG = getLogger(__name__)

# -- manager ------------------------------------------------------------------


class RoleQueryManager(object):
    
    """
    Manager used to process queries on roles. Roles returned from
    these calls are role SON objects from the database.
    """
    def find_all(self):
        """
        Returns serialized versions of all role in the database.

        @return: list of serialized roles
        @rtype:  list of dict
        """
        all_roles = list(Role.get_collection().find())
        return all_roles


    def find_by_id(self, role_id):
        """
        Returns a serialized version of the given role if it exists.
        If a role cannot be found with the given id, None is returned.

        @return: serialized data describing the role
        @rtype:  dict or None
        """
        role = Role.get_collection().find_one({'id' : role_id})
        return role


 
    def get_other_roles(self, role, role_ids):
        """
        Get a list of role instances corresponding to the role ids, excluding the
        given role instance
        
        @type role: L{pulp.server.model.db.Role} instance
        @param role: role to exclude
    
        @type role_ids: list or tuple of str's
    
        @rtype: list of L{pulp.server.model.db.Role} instances
        @return: list of roles
        """
        return [self.find_by_id(n) for n in role_ids if n != role['id']]

