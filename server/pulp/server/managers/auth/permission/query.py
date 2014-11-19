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

from pulp.server.db.model.auth import Permission


class PermissionQueryManager(object):
    
    """
    Manager used to process queries on permissions. Permissions returned from
    these calls are permission SON objects from the database.
    """
    
    def find_all(self):
        """
        Returns serialized versions of all permissions in the database.

        @return: list of serialized permissions
        @rtype:  list of dict
        """
        all_permissions = list(Permission.get_collection().find())
        return all_permissions

    def find_by_resource(self, resource_uri):
        """
        Returns a serialized version of the given permission if it exists.
        If a resource cannot be found with the given URI, None is returned.

        @return: serialized data describing the permission
        @rtype:  dict or None
        """
        permission = Permission.get_collection().find_one({'resource': resource_uri})
        return permission
