# -*- coding: utf-8 -*-

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

from pulp.server.api.base import BaseApi
from pulp.server.db.model.auth import Role
from pulp.server.exceptions import PulpException


class RoleAPI(BaseApi):
    """
    API class for manipulating role model instances.
    """

    # base class methods overridden for implementation

    def _getcollection(self):
        return Role.get_collection()

    def create(self, name):
        role = self.role(name)
        if role is not None:
            raise PulpException('role %s already exists' % name)
        role = Role(name)
        self.collection.insert(role, safe=True)
        return role

    # base class methods overridden for auditing

    def update(self, id, delta):
        """
        Updates a role object.
        @param id: The repo ID.
        @type id: str
        @param delta: A dict containing update keywords.
        @type delta: dict
        @return: The updated object
        @rtype: dict
        """
        delta.pop('id', None)
        role = self.role(id)
        if not role:
            raise PulpException('Role [%s] does not exist', id)
        for key, value in delta.items():
            # simple changes
            if key in ('users','permissions',):
                role[key] = value
                continue
            # unsupported
            raise Exception, \
                'update keyword "%s", not-supported' % key
        self.collection.save(role, safe=True)

    def delete(self, role):
        self.collection.remove({'name':role['name']})

    def clean(self):
        super(RoleAPI, self).clean()

    # role-specific methods

    def role(self, name):
        roles = self.roles({'name': name})
        if not roles:
            return None
        return roles[0]

    def roles(self, spec=None, fields=None):
        return list(self.collection.find(spec=spec, fields=fields))

    def add_permissions(self, role, resource, operations):
        current_ops = role['permissions'].setdefault(resource, [])
        for o in operations:
            if o in current_ops:
                continue
            current_ops.append(o)
        self.collection.save(role, safe=True)

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
        self.collection.save(role, safe=True)
