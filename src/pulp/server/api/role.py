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
    def create(self, name, description=None, action_types=None, resource_type=None):
        """
        Create a new Role object and return it
        """
        role = model.Role(name, description, action_types, resource_type)
        self.insert(role)
        return role

    def roles(self, spec=None, fields=None):
        """
        List all Roles.
        """
        roles = list(self.objectdb.find(spec=spec, fields=fields))
        return roles

    def role(self, name, fields=None):
        """
        Return a single Role object
        """
        return self.objectdb.find_one({'name': name}, fields)

    @audit(params=['name'])
    def delete(self, name):
        self.objectdb.remove({'name' : name}, safe=True)
        
        
class PermissionApi(BaseApi):

    def _getcollection(self):
        return get_object_db('permissions',
                             self._unique_indexes,
                             self._indexes)


    @audit(params=['role'])
    def create(self, role, instance, user):
        """
        Create a new Permission object and return it
        """
        permission = model.Permission(role, instance, user)
        self.insert(permission)
        return permission

    def permissions(self, spec=None, fields=None):
        """
        List all Permissions
        """
        perms = list(self.objectdb.find(spec=spec, fields=fields))
        return perms

    def permission(self, id, fields=None):
        """
        Return a single User object
        """
        return self.objectdb.find_one({'id': id}, fields)

    @audit(params=['name'])
    def delete(self, id):
        self.objectdb.remove({'id' : name}, safe=True)
        
        
        
        
        
        
        
