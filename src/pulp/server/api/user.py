#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import logging
import uuid

from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
from pulp.server.config import config
from pulp.server.db import model
from pulp.server.db.connection import get_object_db
import pulp.server.password_util as password_util

log = logging.getLogger(__name__)
user_fields = model.User(None, None, None, None).keys()


class UserApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)
        self.default_login = config.get('server', 'default_login')
        self._ensure_default_admin()

    def _getcollection(self):
        return get_object_db('users',
                             self._unique_indexes,
                             self._indexes)

    def _ensure_default_admin(self):
        admin = self.user(self.default_login)
        if (admin is None):
            default_password = config.get('server', 'default_password') 
            self.create(self.default_login, password=default_password)

    @audit(params=['login'])
    def create(self, login, password=None, name=None,  id=None):
        """
        Create a new User object and return it
        """
        if id is None:
            id = str(uuid.uuid4())
        hashed_password = None
        if (password is not None):
            log.info("password received is %s" % password)
            log.info("login %s" % login)
            log.info("name %s" % name)
            hashed_password = password_util.hash_password(password)
        user = model.User(login, id, hashed_password, name)
        self.insert(user)
        return user

    def users(self, spec=None, fields=None):
        """
        List all users.
        """
        users = list(self.objectdb.find(spec=spec, fields=fields))
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
        self.objectdb.remove({'login': {'$ne': self.default_login}}, safe=True)
