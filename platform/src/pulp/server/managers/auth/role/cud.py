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
from pulp.server.managers import factory


# -- constants ----------------------------------------------------------------

_ROLE_NAME_REGEX = re.compile(r'^[\-_A-Za-z0-9]+$') # letters, numbers, underscore, hyphen

# built in roles --------------------------------------------------------------

super_user_role = 'super-users'
consumer_users_role = 'consumer-users'

CREATE, READ, UPDATE, DELETE, EXECUTE = range(5)
operation_names = ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXECUTE']

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

#def delete_role(role_name):
#    """
#    Delete a role. This has the side-effect of revoking any permissions granted
#    to the role from the users in the role, unless those permissions are also
#    granted through another role the user is a memeber of.
#    @type role_name: name of the role to delete
#    @param role_name: role name
#    @rtype: bool
#    @return: True on success
#    """
#    check_builtin_roles(role_name)
#    role = _get_role(role_name)
#    users = _get_users_belonging_to_role(role)
#    for resource, operations in role['permissions'].items():
#        for user in users:
#            other_roles = _get_other_roles(role, user['roles'])
#            user_ops = _operations_not_granted_by_roles(resource,
#                                                        operations,
#                                                        other_roles)
#            _permission_api.revoke(resource, user, user_ops)
#    for user in users:
#        user['roles'].remove(role_name)
#        _user_manager.update_user(user['login'], Delta(user, 'roles'))
#    _role_api.delete(role)
#    return True





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
        
    def _ensure_super_user_role(self):
        """
        Assure the super user role exists.
        """
        role_query_manager = factory.role_query_manager()
        role = role_query_manager.find_by_name(super_user_role)
        if role is None:
            role = self.create_role(super_user_role)
            self.add_permissions_to_role(role, '/', [CREATE, READ, UPDATE, DELETE, EXECUTE])


    def _ensure_consumer_user_role(self):
        """
        Assure the consumer role exists.
        """
        role_query_manager = factory.role_query_manager()
        role = role_query_manager.find_by_name(consumer_users_role)
        if role is None:
            role = self.create_role(consumer_users_role)
            self.add_permissions_to_role(role, '/consumers/', [CREATE, READ]) # XXX not sure this is necessary
            self.add_permissions_to_role(role, '/errata/', [READ])
            self.add_permissions_to_role(role, '/repositories/', [READ])

    def ensure_builtin_roles(self):
        """
        Assure the roles required for pulp's operation are in the database.
        """
        self._ensure_super_user_role()
        self._ensure_consumer_user_role()


# -- functions ----------------------------------------------------------------

def is_role_name_valid(name):
    """
    @return: true if the role name is valid; false otherwise
    @rtype:  bool
    """
    result = _ROLE_NAME_REGEX.match(name) is not None
    return result
