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

from pymongo.errors import DuplicateKeyError

from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
from pulp.server.db.model import Permission
from pulp.server.exceptions import PulpException


class PermissionAPI(BaseApi):
    """
    API class for manipulating permission model instances.
    """

    # base class methods overridden for implementation

    def _getcollection(self):
        return Permission.get_collection()

    @audit()
    def create(self, resource):
        if self.permission(resource) is not None:
            raise PulpException('permission for %s already exists' % resource)
        permission = Permission(resource)
        self.collection.insert(permission, safe=True)
        return permission

    # base class methods overridden for auditing

    @audit()
    def update(self, resource, delta):
        """
        Updates a permission object.
        @param id: The repo ID.
        @type id: str
        @param delta: A dict containing update keywords.
        @type delta: dict
        @return: The updated object
        @rtype: dict
        """
        delta.pop('resource', None)
        permission = self.permission(resource)
        if not permission:
            raise PulpException('Permission [%s] does not exist', id)
        for key, value in delta.items():
            # simple changes
            if key in ('users',):
                permission[key] = value
                continue
            # unsupported
            raise Exception, \
                'update keyword "%s", not-supported' % key
        self.collection.save(permission, safe=True)

    @audit()
    def delete(self, permission):
        self.collection.remove({'resource':permission['resource']})

    @audit()
    def clean(self):
        super(PermissionAPI, self).clean()

    # permission-specific methods

    def _get_or_create(self, resource):
        try:
            self.create(resource)
        except (DuplicateKeyError, PulpException):
            pass
        permission = self.permission(resource)
        return permission

    def permission(self, resource):
        permissions = self.permissions({'resource': resource})
        if not permissions:
            return None
        return permissions[0]

    def permissions(self, spec=None, fields=None):
        return list(self.collection.find(spec=spec, fields=fields))

    @audit()
    def grant(self, resource, user, operations):
        """
        Grant permission on a resource for a user and a set of operations.
        @type resource: str
        @param resource: uri path representing a pulp resource
        @type user: L{pulp.server.db.model.User} instance
        @param user: user to grant permissions to
        @type operations: list or tuple
        @param operations:list of allowed operations being granted
        """
        permission = self._get_or_create(resource)
        current_ops = permission['users'].setdefault(user['login'], [])
        for o in operations:
            if o in current_ops:
                continue
            current_ops.append(o)
        self.collection.save(permission, safe=True)

    @audit()
    def revoke(self, resource, user, operations):
        """
        Revoke permission on a resource for a user and a set of operations.
        @type resource: str
        @param resource: uri path representing a pulp resource
        @type user: L{pulp.server.db.model.User} instance
        @param user: user to revoke permissions from
        @type operations: list or tuple
        @param operations:list of allowed operations being revoked
        """
        permission = self.permission(resource)
        if permission is None:
            return
        current_ops = permission['users'].get(user['login'], [])
        if not current_ops:
            return
        for o in operations:
            if o not in current_ops:
                continue
            current_ops.remove(o)
        # delete the user if there are no more allowed operations
        if not current_ops:
            del permission['users'][user['login']]
        # delete the permission if there are no more users
        if not permission['users']:
            self.delete(permission)
            return
        self.collection.save(permission, safe=True)
