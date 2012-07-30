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
from gettext import gettext as _

import logging
import re

from pulp.server.util import Delta
from pulp.server.db.model.auth import Role, User
from pulp.server.auth.authorization import _operations_not_granted_by_roles
from pulp.server.exceptions import DuplicateResource, InvalidValue, MissingResource, PulpDataException
from pulp.server.managers import factory


# -- constants ----------------------------------------------------------------

_ROLE_NAME_REGEX = re.compile(r'^[\-_A-Za-z0-9]+$') # letters, numbers, underscore, hyphen

# built in roles --------------------------------------------------------------

super_user_role = 'super-users'

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
        
        if name is None or _ROLE_NAME_REGEX.match(name) is None:
            raise InvalidValue(['name'])
        
        # Creation
        create_me = Role(name=name)
        Role.get_collection().save(create_me, safe=True)

        # Retrieve the role to return the SON object
        created = Role.get_collection().find_one({'name' : name})

        return created
    

    def update_role(self, name, delta):
        """
        Updates a role object.

        @param id: The role name.
        @type id: str

        @param delta: A dict containing update keywords.
        @type delta: dict

        @return: The updated object
        @rtype: dict
        
        @raise MissingResource: if the given role does not exist
        @raise PulpDataException: if update keyword  is not supported
        """
 
        delta.pop('name', None)
         
        role = Role.get_collection().find_one({'name' : name})
        if role is None:
            raise MissingResource(name)

        for key, value in delta.items():
            # simple changes
            if key in ('users','permissions',):
                role[key] = value
                continue
            # unsupported
            raise PulpDataException(_("Update Keyword [%s] is not supported" % key))
        
        Role.get_collection().save(role, safe=True)
         
        # Retrieve the user to return the SON object
        updated = Role.get_collection().find_one({'name' : name})
        return updated


    def delete_role(self, name):
        """
        Deletes the given role. This has the side-effect of revoking any permissions granted
        to the role from the users in the role, unless those permissions are also granted 
        through another role the user is a memeber of.

        @param name: identifies the role being deleted
        @type  name: str

        @raise InvalidValue: if any of the fields are unacceptable
        @raise MissingResource: if the given role does not exist
        """
        # Raise exception if role name is invalid
        if name is None or not isinstance(name, basestring):
            raise InvalidValue(['name'])

        # Check whether role exists
        role = Role.get_collection().find_one({'name' : name})
        if role is None:
            raise MissingResource(name)

        # Make sure role is not a superuser role
        if name == super_user_role:
            raise PulpDataException(_('Role %s cannot be changed') % name)

        # Remove respective roles from users
        users = factory.user_query_manager().find_users_belonging_to_role(role)
        for resource, operations in role['permissions'].items():
            for user in users:
                other_roles = factory.role_query_manager().get_other_roles(role, user['roles'])
                user_ops = _operations_not_granted_by_roles(resource, operations, other_roles)
                factory.permission_manager().revoke(resource, user, user_ops)

        for user in users:
            user['roles'].remove(name)
            factory.user_manager().update_user(user['login'], Delta(user, 'roles'))
      
        Role.get_collection().remove({'name' : name}, safe=True)


    def add_permissions_to_role(self, name, resource, operations):
        """
        Add permissions to a role. 

        @type name: str
        @param name: name of role
        
        @type resource: str
        @param resource: resource path to grant permissions to
        
        @type operations: list of allowed operations being granted
        @param operations: list or tuple

        @raise MissingResource: if the given role does not exist
        """
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
        """
        Remove permissions from a role. 
        
        @type name: str
        @param name: name of role
    
        @type resource: str
        @param resource: resource path to revoke permissions from
        
        @type operations: list of allowed operations being revoked
        @param operations: list or tuple
        
        @raise MissingResource: if the given role does not exist
        """
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
        
    
    def add_user_to_role(self, name, login):
        """
        Add a user to a role. This has the side-effect of granting all the
        permissions granted to the role to the user.
        
        @type name: str
        @param name: name of role
        
        @type login: str
        @param login: login of user
        
        @rtype: bool
        @return: True on success
        
        @raise MissingResource: if the given role or user does not exist
        """
        role = Role.get_collection().find_one({'name' : name})
        if role is None:
            raise MissingResource(name)

        user = User.get_collection().find_one({'login' : login})
        if user is None:
            raise MissingResource(login)
       
        if name in user['roles']:
            return False

        user['roles'].append(name)
        User.get_collection().save(user, safe=True)
        
        for resource, operations in role['permissions'].items():
            factory.permission_manager().grant(resource, user, operations)
        return True


    def remove_user_from_role(self, name, login):
        """
        Remove a user from a role. This has the side-effect of revoking all the
        permissions granted to the role from the user, unless the permissions are
        also granted by another role.
        
        @type name: str
        @param name: name of role
    
        @type login: str
        @param login: name of user
        
        @rtype: bool
        @return: True on success
                        
        @raise MissingResource: if the given role or user does not exist
        """
        role = Role.get_collection().find_one({'name' : name})
        if role is None:
            raise MissingResource(name)

        user = User.get_collection().find_one({'login' : login})
        if user is None:
            raise MissingResource(login)

        if name == super_user_role and factory.user_query_manager().is_last_super_user(user):
            raise PulpDataException(_('%s cannot be empty, and %s is the last member') %
                                     (super_user_role, login))
        
        if name not in user['roles']:
            return False

        user['roles'].remove(name)
        User.get_collection().save(user, safe=True)
        
        for resource, operations in role['permissions'].items():
            other_roles = factory.role_query_manager().get_other_roles(role, user['roles'])
            user_ops = _operations_not_granted_by_roles(resource,
                                                        operations,
                                                        other_roles)
            factory.permission_manager().revoke(resource, user, user_ops)
        return True
 
        
        
    def ensure_super_user_role(self):
        """
        Assure the super user role exists.
        """
        role_query_manager = factory.role_query_manager()
        role = role_query_manager.find_by_name(super_user_role)
        if role is None:
            role = self.create_role(super_user_role)
            self.add_permissions_to_role(role['name'], '/', [CREATE, READ, UPDATE, DELETE, EXECUTE])


# -- functions ----------------------------------------------------------------

