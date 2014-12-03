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

    def find_user_permission(self, permission, login, create=False):
        """
        Returns an array of permissions for the given user for the given
        resource permission

        :param permission: The permission document from the database
        :param login: the username permissions are being checked for
        :return: array of permissions for user
        :rtype: array of permissions or empty array
        """
        user_permission = self.get_user_permission(permission, login)
        if user_permission is None:
            if create:
                user_permission = dict(username=login, permissions=[])
                permission['users'].append(user_permission)
                return user_permission['permissions']
            else:
                return []
        else:
            return user_permission['permissions']

    def delete_user_permission(self, permission, login):
        """
        Centralizes the deletion of user permissions from the permissions document

        :param permission:  The permissions document to modify
        :param login:  The users login to remove permissions from
        """
        user_permission = self.get_user_permission(permission, login)
        if user_permission is not None:
            permission['users'].remove(user_permission)

    def get_user_permission(self, permission, login):
        """
        Gets the dictionary that contains the username and granted permissions

        :param permission: The permissions document
        :param login: The users login to find permissions for
        :return: dictionary of username and permissions for given user
        """
        for item in permission['users']:
            if item['username'] == login:
                return item
        return None
