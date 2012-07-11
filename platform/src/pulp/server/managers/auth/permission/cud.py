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
Contains the manager class and exceptions for operations surrounding the creation,
update, and deletion on a Pulp Role.
"""

import logging
import re

from pulp.server.db.model.auth import User, Role, Permission
from pulp.server.exceptions import DuplicateResource, InvalidValue, MissingResource


# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- classes ------------------------------------------------------------------

class PermissionManager(object):
    """
    Performs permission related functions relating to CRUD operations.
    """

    def create_permission(self, resource_uri):
        """
        Creates a new Pulp permission.

        @param resource_uri: resource_uri for the permission
        @type  resource_uri: str

        @raise DuplicateResource: if there is already a permission with the requested resource
        @raise InvalidValue: if any of the fields are unacceptable
        """
        
        existing_permission = Permission.get_collection().find_one({'resource' : resource_uri})
        if existing_permission is not None:
            raise DuplicateResource(resource_uri)

        # Creation
        create_me = Permission(resource=resource_uri)
        Permission.get_collection().save(create_me, safe=True)

        # Retrieve the permission to return the SON object
        created = Permission.get_collection().find_one({'resource' : resource_uri})

        return created


    def delete_permission(self, resource_uri):
        """
        Deletes the given permission. 
        @param resource_uri: identifies the resource URI of the permission being deleted
        @type  resource_uri: str

        @raise MissingResource: if permission for a given resource does not exist
        @raise InvalidValue: if resource URI is invalid
        """

        # Raise exception if resource is invalid
        if resource_uri is None or not isinstance(resource_uri, str):
            raise InvalidValue(['resource_uri'])

        # Check whether the permission exists
        found = Permission.get_collection().find_one({'resource' : resource_uri})
        if found is None:
            raise MissingResource(resource_uri)

        # To do: Remove respective roles from users
      
        Permission.get_collection().remove({'resource' : resource_uri}, safe=True)

    
    def update_permission(self, resource_uri, delta):
        """
        Updates a permission object.
        
        @param resource_uri: identifies the resource URI of the permission being deleted
        @type resource_uri: str
        
        @param delta: A dict containing update keywords.
        @type delta: dict
        
        @return: The updated object
        @rtype: dict
        """
        
        # Check whether the permission exists
        found = Permission.get_collection().find_one({'resource' : resource_uri})
        if found is None:
            raise MissingResource(resource_uri)

        for key, value in delta.items():
            # simple changes
            if key in ('users',):
                found[key] = value
                continue
            # unsupported
            raise Exception, \
                'update keyword "%s", not-supported' % key
        
        Permission.get_collection().save(found, safe=True)

    def grant(self, resource, user, operations):
        """
        Grant permission on a resource for a user and a set of operations.
        @type resource: str
        @param resource: uri path representing a pulp resource
        @type user: L{pulp.server.db.model.User} instance
        @param user: user to grant permissions to
        @type operations: list or tuple
        @param operations:list of allowed operations being granted
        """
        permission = self._get_or_create(resource)
        current_ops = permission['users'].setdefault(user['login'], [])
        for o in operations:
            if o in current_ops:
                continue
            current_ops.append(o)
        self.collection.save(permission, safe=True)

    def revoke(self, resource, user, operations):
        """
        Revoke permission on a resource for a user and a set of operations.
        @type resource: str
        @param resource: uri path representing a pulp resource
        @type user: L{pulp.server.db.model.User} instance
        @param user: user to revoke permissions from
        @type operations: list or tuple
        @param operations:list of allowed operations being revoked
        """
        permission = self.permission(resource)
        if permission is None:
            return
        current_ops = permission['users'].get(user['login'], [])
        if not current_ops:
            return
        for o in operations:
            if o not in current_ops:
                continue
            current_ops.remove(o)
        # delete the user if there are no more allowed operations
        if not current_ops:
            del permission['users'][user['login']]
        # delete the permission if there are no more users
        if not permission['users']:
            self.delete(permission)
            return
        self.collection.save(permission, safe=True)


    def add_permissions_to_role(self, name, resource, operations):
        role = Role.get_collection().find_one({'name' : name})
        if role is None:
            raise MissingResource(name)
        
        current_ops = role['permissions'].setdefault(resource, [])
        for o in operations:
            if o in current_ops:
                continue
            current_ops.append(o)
            
        Role.get_collection().save(role, safe=True)

    def remove_permissions_from_role(self, name, resource, operations):
        role = Role.get_collection().find_one({'name' : name})
        if role is None:
            raise MissingResource(name)
        
        current_ops = role['permissions'].get(resource, [])
        if not current_ops:
            return
        for o in operations:
            if o not in current_ops:
                continue
            current_ops.remove(o)
        # in no more allowed operations, remove the resource
        if not current_ops:
            del role['permissions'][resource]
        Role.get_collection().save(role, safe=True)



