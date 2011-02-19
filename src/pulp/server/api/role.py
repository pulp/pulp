# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
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

from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
#from pulp.server.db.connection import get_object_db
from pulp.server.db.model import Role
from pulp.server.pexceptions import PulpException


class RoleAPI(BaseApi):
    """
    API class for manipulating role model instances.
    """

    # base class methods overridden for implementation

    def _getcollection(self):
        #return get_object_db('roles', self._unique_indexes, self._indexes)
        return Role.get_collection()

    @property
    def _unique_indexes(self):
        return ['name']

    @audit()
    def create(self, name):
        role = self.role(name)
        if role is not None:
            raise PulpException('role %s already exists' % name)
        role = Role(name)
        self.insert(role)
        return role

    # base class methods overridden for auditing

    @audit()
    def delete(self, role):
        super(RoleAPI, self).delete(name=role['name'])

    @audit()
    def clean(self):
        super(RoleAPI, self).clean()

    # role-specific methods

    def role(self, name):
        roles = self.roles({'name': name})
        if not roles:
            return None
        return roles[0]

    def roles(self, spec=None, fields=None):
        return list(self.objectdb.find(spec=spec, fields=fields))

    @audit()
    def add_permissions(self, role, resource, operations):
        current_ops = role['permissions'].setdefault(resource, [])
        for o in operations:
            if o in current_ops:
                continue
            current_ops.append(o)
        self.update(role)

    @audit()
    def remove_permissions(self, role, resource, operations):
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
        self.update(role)
