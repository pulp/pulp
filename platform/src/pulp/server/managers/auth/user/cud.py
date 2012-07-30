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
update, and deletion on a Pulp user.
"""

import logging
import re

from pulp.server import config
from pulp.server.db.model.auth import User
from pulp.server.auth.authorization import _operations_not_granted_by_roles
from pulp.server.exceptions import PulpDataException, DuplicateResource, InvalidValue, MissingResource
from pulp.server.managers import factory
from pulp.server.managers.auth.role.cud import super_user_role

from pulp.server.managers.auth.password import PasswordManager

# -- constants ----------------------------------------------------------------

super_user_role = 'super-users'

_USER_LOGIN_REGEX = re.compile(r'^[\-_A-Za-z0-9]+$') # letters, numbers, underscore, hyphen

_LOG = logging.getLogger(__name__)

# -- classes ------------------------------------------------------------------

class UserManager(object):
    """
    Performs user related functions relating to CRUD operations.
    """

    def create_user(self, login, password=None, name=None, roles=None):
        """
        Creates a new Pulp user and adds it to specified to roles.

        @param login: login name / unique identifier for the user
        @type  login: str

        @param password: password for login credentials
        @type  password: str

        @param name: user's full name
        @type  name: str

        @param roles: list of roles user will belong to
        @type  notes: dict

        @raise DuplicateResource: if there is already a user with the requested login
        @raise InvalidValue: if any of the fields are unacceptable
        """

        existing_user = User.get_collection().find_one({'login' : login})
        if existing_user is not None:
            raise DuplicateResource(login)

        invalid_values = []

        if login is None or _USER_LOGIN_REGEX.match(login) is None:
            invalid_values.append('login')
        if invalid_type(name, basestring):
            invalid_values.append('name')
        if invalid_type(roles, list):
            invalid_values.append('roles')

        if invalid_values:
            raise InvalidValue(invalid_values)

        # Use the login for user name if one was not specified
        name = name or login
        roles = roles or None

        # Encode plain-text password
        hashed_password = None
        if password:
            hashed_password = PasswordManager().hash_password(password)

        # Creation
        create_me = User(login=login, password=hashed_password, name=name, roles=roles)
        User.get_collection().save(create_me, safe=True)
        
        # Grant permissions
        permission_manager = factory.permission_manager()
        permission_manager.grant_automatic_permissions_for_user(create_me['login'])

        # Retrieve the user to return the SON object
        created = User.get_collection().find_one({'login' : login})

        return created



    def update_user(self, login, delta):
        """
        Updates the user. Following fields may be updated through this call:
        * password
        * name
        * roles

        Other fields found in delta will be ignored.

        @param login: identifies the user
        @type  login: str

        @param delta: list of attributes and their new values to change
        @type  delta: dict

        @raise MissingResource: if there is no user with login
        """

        user = User.get_collection().find_one({'login' : login})
        if user is None:
            raise MissingResource(login)

        # Check invalid values
        invalid_values = []
        if 'password' in delta:
            if delta['password'] is None or invalid_type(delta['password'], basestring):
                invalid_values.append('password')
            else:
                user['password'] = PasswordManager().hash_password(delta['password'])

        if 'name' in delta:
            if delta['name'] is None or invalid_type(delta['name'], basestring):
                invalid_values.append('name')
            else:
                user['name'] = delta['name']

        if 'roles' in delta:
            if delta['roles'] is None or invalid_type(delta['roles'], list):
                invalid_values.append('roles')
            else:
                # Add new roles to the user and remove deleted roles from the user according to delta
                old_roles = user['roles']
                for new_role in delta['roles']:
                    if new_role not in old_roles:
                        self.add_user_to_role(new_role, login)
                for old_role in old_roles:
                    if old_role not in delta['roles']:
                        self.remove_user_from_role(old_role, login)
                user['roles'] = delta['roles']

        if invalid_values:
            raise InvalidValue(invalid_values)

        User.get_collection().save(user, safe=True)

        # Retrieve the user to return the SON object
        updated = User.get_collection().find_one({'login' : login})
        updated.pop('password')

        return updated
    

    def delete_user(self, login):
        """
        Deletes the given user. Deletion of last superuser is not permitted.

        @param login: identifies the user being deleted
        @type  login: str

        @raise MissingResource: if the given user does not exist
        @raise InvalidValue: if login value is invalid
        """

        # Raise exception if login is invalid
        if login is None or invalid_type(login, basestring):
            raise InvalidValue(['login'])

        # Check whether user exists
        found = User.get_collection().find_one({'login' : login})
        if found is None:
            raise MissingResource(login)

        # Make sure user is not the last super user 
        if factory.user_query_manager().is_last_super_user(found): 
            raise PulpDataException(_("The last superuser [%s] cannot be deleted" % found['id']))
             
        # Revoke all permissions from the user
        factory.permission_manager().revoke_all_permissions_from_user(login)
        
        User.get_collection().remove({'login' : login}, safe=True)


    def ensure_admin(self):
        """
        This function ensures that there is at least one super user for the system.
        If no super users are found, the default admin user (from the pulp config)
        is looked up or created and added to the super users role.
        """
        user_query_manager = factory.user_query_manager()
        role_query_manager = factory.role_query_manager()

        super_users = user_query_manager.get_users_belonging_to_role( 
                    role_query_manager.find_by_name(super_user_role))
        if super_users:
            return
        
        default_login = config.config.get('server', 'default_login')
        
        admin = factory.user_query_manager().find_by_login(default_login)
        if admin is None:
            default_password = config.config.get('server', 'default_password')
            admin = factory.user_manager().create_user(login=default_login, password=default_password)
        
        self.add_user_to_role(super_user_role, default_login)

    
    def add_user_to_role(self, role_name, login):
        """
        Add a user to a role. This has the side-effect of granting all the
        permissions granted to the role to the user.
        
        @type role_name: str
        @param role_name: name of role
        
        @type login: str
        @param login: login of user
        
        @rtype: bool
        @return: True on success
        """
        role =  factory.role_query_manager().find_by_name(role_name)
        user = factory.user_query_manager().find_by_login(login)
       
        if role_name in user['roles']:
            return False

        user['roles'].append(role_name)
        User.get_collection().save(user, safe=True)
        
        for resource, operations in role['permissions'].items():
            factory.permission_manager().grant(resource, user, operations)
        return True


    def remove_user_from_role(self, role_name, user_name):
        """
        Remove a user from a role. This has the side-effect of revoking all the
        permissions granted to the role from the user, unless the permissions are
        also granted by another role.
        
        @type role_name: str
        @param role_name: name of role
    
        @type user_name: str
        @param suer_name: name of user
        
        @rtype: bool
        @return: True on success
        """
      
        role = factory.role_query_manager().find_by_name(role_name)
        user = factory.user_query_manager().find_by_login(user_name)
        if role_name == super_user_role and factory.user_query_manager().is_last_super_user(user):
            raise PulpDataException(_('%s cannot be empty, and %s is the last member') %
                                     (super_user_role, user_name))
        
        if role_name not in user['roles']:
            return False

        user['roles'].remove(role_name)
        User.get_collection().save(user, safe=True)
        
        for resource, operations in role['permissions'].items():
            other_roles = factory.role_query_manager().get_other_roles(role, user['roles'])
            user_ops = _operations_not_granted_by_roles(resource,
                                                        operations,
                                                        other_roles)
            factory.permission_manager().revoke(resource, user, user_ops)
        return True
 


# -- functions ----------------------------------------------------------------


def invalid_type(input_value, valid_type):
    """
    @return: true if input_value is not of valid_type
    @rtype: bool
    """
    if input_value is not None and not isinstance(input_value, valid_type):
        return True
    return False
