# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging
import uuid

import pulp.server.auth.password_util as password_util
from pulp.server import config
from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
from pulp.server.db import model

log = logging.getLogger(__name__)

user_fields = model.User(None, None, None, None).keys()


class UserApi(BaseApi):

    def _getcollection(self):
        return model.User.get_collection()

    @audit(params=['login'])
    def create(self, login, password=None, name=None, id=None):
        """
        Create a new User object and return it
        """
        if id is None:
            id = str(uuid.uuid4())
        hashed_password = None
        if (password is not None):
            hashed_password = password_util.hash_password(password)
        user = model.User(login, id, hashed_password, name)
        self.collection.insert(user, safe=True)
        return user

    @audit()
    def update(self, login, delta):
        """
        Update a user and hash the inbound password if it is different
        from the existing password.
        @param login: The user login.
        @param delta: A dict of fields to change.
        """
        delta.pop('login', None)
        user = self.user(login)
        for key, value in delta.items():
            # simple changes
            if key in ('name', 'roles',):
                user[key] = value
                continue
            # password changed
            if key == 'password':
                if value:
                    user['password'] = password_util.hash_password(value)
                continue
            raise Exception, \
                'update keyword "%s", not-supported' % key
        self.collection.save(user, safe=True)
        return user

    @audit()
    def delete(self, login):
        """
        Delete a user.
        @param login: The login.
        @type login: str
        """
        self.collection.remove({'login':login})

    def users(self, spec=None, fields=None):
        """
        List all users.
        """
        users = list(self.collection.find(spec=spec, fields=fields))
        return users

    def user(self, login, fields=None):
        """
        Return a single User object
        """
        users = self.users({'login': login}, fields)
        if not users:
            return None
        return users[0]

    @audit()
    def clean(self):
        """
        Delete all the Users in the database except the default admin user.  default 
        user can not be deleted
        """
        default_login = config.config.get('server', 'default_login')
        self.collection.remove({'login': {'$ne': default_login}}, safe=True)
