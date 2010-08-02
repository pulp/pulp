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

from pulp import model
from pulp.api.base import BaseApi
from pulp.auditing import audit
from pulp.config import config


log = logging.getLogger(__name__)
user_fields = model.User(None, None, None, None).keys()


class UserApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)
        self.default_login = config.get('server', 'default_login')
        self._ensure_default_admin()

    def _getcollection(self):
        return self.db.users

    def _ensure_default_admin(self):
        admin = self.user(self.default_login)
        if (admin == None):
            default_password = config.get('server', 'default_password') 
            self.create(self.default_login, password=default_password)

    @audit(params=['login', 'name'])
    def create(self, login, id=None, password=None, name=None):
        """
        Create a new User object and return it
        """
        if id is None:
            id = str(uuid.uuid4())
        user = model.User(login, id, password, name)
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
