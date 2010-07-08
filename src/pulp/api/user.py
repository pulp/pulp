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
import uuid
import logging
import pymongo
import re

from pulp import model
from pulp.api.base import BaseApi
from pulp.pexceptions import PulpException
from pulp.util import chunks
from pulp.agent import Agent
from pulp.certificate import Certificate

# Pulp
from pulp.api.consumer import ConsumerApi


log = logging.getLogger('pulp.api.user')

class UserApi(BaseApi):

    def __init__(self, config):
        BaseApi.__init__(self, config)
        self.default_login = self.config.get('server', 'default_login')
        self._ensure_default_admin()

    def _getcollection(self):
        return self.db.users

    def _ensure_default_admin(self):
        admin = self.user(self.default_login)
        if (admin == None):
            default_password = self.config.get('server', 'default_password') 
            self.create(self.default_login, password=default_password)

    def create(self, login, id=None, password=None, name=None, certificate=None):
        """
        Create a new User object and return it
        """
        if (id != None and certificate != None):
            raise PulpException(
                "Specify either an id or a certificate string but not both")
        if (certificate != None):
            idcert = Certificate(content=certificate)
            subject = idcert.subject()
            id = subject['UID']
        elif (id == None):
            id = str(uuid.uuid4())
        user = model.User(login, id, password, name, certificate)
        self.insert(user)
        return user

    def users(self):
        """
        List all users.
        """
        users = list(self.objectdb.find())
        return users

    def user(self, login):
        """
        Return a single User object
        """
        return self.objectdb.find_one({'login': login})

    def clean(self):
        """
        Delete all the Users in the database except the default admin user.  default 
        user can not be deleted
        """
        self.objectdb.remove({'login': {'$ne': self.default_login}}, safe=True)
