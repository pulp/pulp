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
Contains users query classes
"""

from gettext import gettext as _

from pulp.server.db.model.auth import User, Role
from pulp.server.managers import factory
from pulp.server.managers.auth.role.cud import super_user_role
from logging import getLogger

from pulp.server.exceptions import PulpDataException

# -- constants ----------------------------------------------------------------

_LOG = getLogger(__name__)

# -- manager ------------------------------------------------------------------


class UserQueryManager(object):
    
    """
    Manager used to process queries on users. Users returned from
    these calls are user SON objects from the database.
    """

    def find_all(self):
        """
        Returns serialized versions of all users in the database.

        @return: list of serialized users
        @rtype:  list of dict
        """
        all_users = list(User.get_collection().find())
        for user in all_users:
            user.pop('password')
        return all_users


    def find_by_login(self, login):
        """
        Returns a serialized version of the given user if it exists.
        If a user cannot be found with the given login, None is returned.

        @return: serialized data describing the user
        @rtype:  dict or None
        """
        user = User.get_collection().find_one({'login' : login})
        return user


    def find_by_id_list(self, login_list):
        """
        Returns serialized versions of all of the given users. Any
        login that does not refer to valid user are ignored and will not
        raise an error.

        @param login_list: list of logins
        @type  login_list: list of str

        @return: list of serialized users
        @rtype:  list of dict
        """
        users = list(User.get_collection().find({'id' : {'$in' : login_list}}))
        for user in users:
            user.pop('password')
        return users
    
    
    def find_users_belonging_to_role(self, role):
        """
        Get a list of users belonging to the given role
        
        @type role: L{pulp.server.db.model.Role} instance
        @param role: role to get members of
        
        @rtype: list of L{pulp.server.db.model.User} instances
        @return: list of users that are members of the given role
        """
        users = []
        for user in self.find_all():
            if role['name'] in user['roles']:
                users.append(user)
        return users


    def is_superuser(self, user):
        """
        Return True if the user is a super user
        
        @type user: L{pulp.server.db.model.User} instance
        @param user: user to check
        
        @rtype: bool
        @return: True if the user is a super user, False otherwise
        """
        return super_user_role in user['roles']


    def is_authorized(self, resource, user, operation):
        """
        Check to see if a user is authorized to perform an operation on a resource
        
        @type resource: str
        @param resource: pulp resource path
    
        @type user: L{pulp.server.db.model.User} instance
        @param user: user to check permissions for
    
        @type operation: int
        @param operation: operation to be performed on resource
    
        @rtype: bool
        @return: True if the user is authorized for the operation on the resource,
                 False otherwise
        """
        if self.is_superuser(user):
            return True
        login = user['login']
        parts = [p for p in resource.split('/') if p]
        
        permission_query_manager = factory.permission_query_manager()
        while parts:
            current_resource = '/%s/' % '/'.join(parts)
            permission = permission_query_manager.find_by_resource(current_resource)
            if permission is not None:
                if operation in permission['users'].get(login, []):
                    return True
            parts = parts[:-1]
        permission = permission_query_manager.find_by_resource('/')
        return (permission is not None and
                operation in permission['users'].get(login, []))
        
        
    def is_last_super_user(self, user):
        """
        Check to see if a user is the last super user
        
        @type user: L{pulp.server.db.model.User} instace
        @param user: user to check
        
        @rtype: bool
        @return: True if the user is the last super user, False otherwise
        
        @raise PulpException: if no super users are found
        """
        if super_user_role not in user['roles']:
            return False

        role = Role.get_collection().find_one({'name' : super_user_role})

        users = self.find_users_belonging_to_role(role)
        if not users:
            raise PulpDataException(_('no super users defined'))
        if len(users) >= 2:
            return False
        return users[0]['_id'] == user['_id'] # this should be True



