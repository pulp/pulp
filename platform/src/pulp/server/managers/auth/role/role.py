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

from pulp.server.db.model.auth import User, Role
from pulp.server.exceptions import DuplicateResource, InvalidValue, MissingResource


# -- constants ----------------------------------------------------------------

_ROLE_NAME_REGEX = re.compile(r'^[\-_A-Za-z0-9]+$') # letters, numbers, underscore, hyphen

_LOG = logging.getLogger(__name__)

# -- classes ------------------------------------------------------------------

class RoleManager(object):
    """
    Performs role related functions relating to CRUD operations.
    """

    def create_role(self, name):
        """
        Creates a new Pulp role.

        @param name: role name / unique identifier for the role
        @type  name: str

        @raise DuplicateResource: if there is already a role with the requested name
        @raise InvalidValue: if any of the fields are unacceptable
        """
        
        existing_role = Role.get_collection().find_one({'name' : name})
        if existing_role is not None:
            raise DuplicateResource(name)

        # Creation
        create_me = Role(name=name)
        Role.get_collection().save(create_me, safe=True)

        # Retrieve the role to return the SON object
        created = Role.get_collection().find_one({'name' : name})

        return created


    def delete_role(self, name):
        """
        Deletes the given role. 
        @param name: identifies the role being deleted
        @type  name: str

        @raise MissingResource: if the given role does not exist
        @raise InvalidValue: if role name is invalid
        """

        # Raise exception if login is invalid
        if name is None or not isinstance(name, str):
            raise InvalidValue(['name'])

        # Check whether role exists
        found = Role.get_collection().find_one({'name' : name})
        if found is None:
            raise MissingResource(name)

        # To do: Remove respective roles from users
      
        Role.get_collection().remove({'name' : name}, safe=True)


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


    def find_all(self):
        """
        Returns serialized versions of all role in the database.

        @return: list of serialized roles
        @rtype:  list of dict
        """
        all_roles = list(Role.get_collection().find())
        return all_roles


    def find_by_name(self, name):
        """
        Returns a serialized version of the given role if it exists.
        If a role cannot be found with the given name, None is returned.

        @return: serialized data describing the role
        @rtype:  dict or None
        """
        role = Role.get_collection().find_one({'name' : name})
        return role



# -- functions ----------------------------------------------------------------

def is_role_name_valid(name):
    """
    @return: true if the role name is valid; false otherwise
    @rtype:  bool
    """
    result = _ROLE_NAME_REGEX.match(name) is not None
    return result
