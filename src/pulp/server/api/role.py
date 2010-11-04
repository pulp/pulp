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
from pulp.server import config
from pulp.server.db import model
from pulp.server.db.connection import get_object_db
from pulp.server.event.dispatcher import event
import pulp.server.auth.password_util as password_util

log = logging.getLogger(__name__)
user_fields = model.User(None, None, None, None).keys()


class RoleApi(BaseApi):

    def _getcollection(self):
        return get_object_db('roles',
                             self._unique_indexes,
                             self._indexes)


    @audit(params=['name'])
    # role = self.rolapi.create(name, desc, action_type, resource_type)
    def create(self, name, description=None, action_types=None, resource_type=None):
        """
        Create a new User object and return it
        """
        role = model.Role(name, description, action_types, resource_type)
        self.insert(role)
        return role


    def roles(self, spec=None, fields=None):
        """
        List all Roles.
        """
        users = list(self.objectdb.find(spec=spec, fields=fields))
        return users

    def role(self, name, fields=None):
        """
        Return a single User object
        """
        return self.objectdb.find_one({'name': name}, fields)

    @audit(params=['name'])
    def delete(self, name):
        self.objectdb.remove({'name' : name}, safe=True)
        
        
        
        
        
        
