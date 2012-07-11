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

from pulp.server.db.model.auth import User
from logging import getLogger

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
        return users

    
    
    def get_users_belonging_to_role(self, role):
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


