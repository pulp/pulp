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
Contains the manager class and exceptions for operations surrounding the creation,
update, and deletion on a Pulp Role.
"""

from gettext import gettext as _

from celery import task

from pulp.server.async.tasks import Task
from pulp.server.auth.authorization import _get_operations
from pulp.server.db.model.auth import Permission, User
from pulp.server.exceptions import (
    DuplicateResource, InvalidValue, MissingResource, PulpDataException,
    PulpExecutionException)
from pulp.server.managers import factory
from pulp.server.managers.auth.user import system


class PermissionManager(object):
    """
    Performs permission related functions relating to CRUD operations.
    """

    def __init__(self):
        self.CREATE, self.READ, self.UPDATE, self.DELETE, self.EXECUTE = range(5)
        self.operation_names = ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXECUTE']

    @staticmethod
    def create_permission(resource_uri):
        """
        Creates a new Pulp permission.

        @param resource_uri: resource_uri for the permission
        @type  resource_uri: str

        @raise DuplicateResource: if there is already a permission with the requested resource
        @raise InvalidValue: if any of the fields are unacceptable
        """

        existing_permission = Permission.get_collection().find_one({'resource' : resource_uri})
        if existing_permission is not None:
            raise DuplicateResource(resource_uri)

        # Creation
        create_me = Permission(resource=resource_uri)
        Permission.get_collection().save(create_me, safe=True)

        # Retrieve the permission to return the SON object
        created = Permission.get_collection().find_one({'resource' : resource_uri})

        return created

    def update_permission(self, resource_uri, delta):
        """
        Updates a permission object.

        @param resource_uri: identifies the resource URI of the permission being deleted
        @type resource_uri: str

        @param delta: A dict containing update keywords.
        @type delta: dict

        @return: The updated object
        @rtype: dict
        """

        # Check whether the permission exists
        found = Permission.get_collection().find_one({'resource' : resource_uri})
        if found is None:
            raise MissingResource(resource_uri)

        for key, value in delta.items():
            # simple changes
            if key in ('users',):
                found[key] = value
                continue

            # unsupported
            raise PulpDataException(_("Update Keyword [%s] is not supported" % key))

        Permission.get_collection().save(found, safe=True)

    @staticmethod
    def delete_permission(resource_uri):
        """
        Deletes the given permission.
        @param resource_uri: identifies the resource URI of the permission being deleted
        @type  resource_uri: str

        @raise MissingResource: if permission for a given resource does not exist
        @raise InvalidValue: if resource URI is invalid
        """

        # Raise exception if resource is invalid
        if resource_uri is None or not isinstance(resource_uri, basestring):
            raise InvalidValue(['resource_uri'])

        # Check whether the permission exists
        found = Permission.get_collection().find_one({'resource' : resource_uri})
        if found is None:
            raise MissingResource(resource_uri)

        Permission.get_collection().remove({'resource' : resource_uri}, safe=True)

    @staticmethod
    def grant(resource, login, operations):
        """
        Grant permission on a resource for a user and a set of operations.

        @type resource: str
        @param resource: uri path representing a pulp resource

        @type user: str
        @param user: login of user to grant permissions to

        @type operations: list or tuple of integers
        @param operations:list of allowed operations being granted
        """
        # we don't grant permissions to the system
        if login == system.SYSTEM_LOGIN:
            return

        user = User.get_collection().find_one({'login' : login})
        if user is None:
            raise MissingResource(user=login)

        # Make sure resource is a valid string or unicode
        if not isinstance(resource, basestring):
            raise InvalidValue(resource)

        # Get or create permission if it doesn't already exist
        permission = Permission.get_collection().find_one({'resource' : resource})
        if permission is None:
            permission = PermissionManager.create_permission(resource)

        current_ops = permission['users'].setdefault(user['login'], [])
        for o in operations:
            if o in current_ops:
                continue
            current_ops.append(o)

        Permission.get_collection().save(permission, safe=True)

    @staticmethod
    def revoke(resource, login, operations):
        """
        Revoke permission on a resource for a user and a set of operations.

        :param resource:   uri path representing a pulp resource
        :type  resource:   str
        :param user:       login of user to revoke permissions from
        :type  user:       str
        :param operations: list of allowed operations being revoked
        :type  operations: list or tuple of integers
        """
        # we don't revoke permissions from the system
        if login == system.SYSTEM_LOGIN:
            return

        user = User.get_collection().find_one({'login' : login})
        if user is None:
            raise MissingResource(user=login)

        permission = Permission.get_collection().find_one({'resource' : resource})
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
            PermissionManager.delete_permission(resource)
            return

        Permission.get_collection().save(permission, safe=True)

    def grant_automatic_permissions_for_resource(self, resource):
        """
        Grant CRUDE permissions for a newly created resource to current principal.

        @type resource: str
        @param resource: resource path to grant permissions to

        @rtype: bool
        @return: True on success, False otherwise

        @raise PulpExecutionException: if the system principal has not been set
        """
        principal_manager = factory.principal_manager()
        user = principal_manager.get_principal()
        if principal_manager.is_system_principal():
            raise PulpExecutionException(_('Cannot grant automatic permissions for [%s] on resource [%s]') %
                               (user, resource))

        operations = [self.CREATE, self.READ, self.UPDATE, self.DELETE, self.EXECUTE]
        self.grant(resource, user['login'], operations)

    def grant_automatic_permissions_for_user(self, login):
        """
        Grant the permissions required for a new user so that they my log into Pulp
        and update their own information.

        @param login: login of the new user
        @type  login: str
        """
        self.grant('/v2/actions/login/', login, [self.READ, self.UPDATE])
        self.grant('/v2/actions/logout/', login, [self.READ, self.UPDATE])
        self.grant('/v2/users/%s/' % login, login, [self.READ, self.UPDATE])

    def revoke_permission_from_user(self, resource, login, operation_names):
        """
        Revoke the operations on the resource from the user
        @type resource: str
        @param resource: pulp resource to revoke operations on

        @type login: str
        @param login: name of the user to revoke permissions from

        @type operation_names: list or tuple of str's
        @param operation_names: name of the operations to revoke

        @rtype: bool
        @return: True on success
        """
        operations = _get_operations(operation_names)
        self.revoke(resource, login, operations)
        return True

    def revoke_all_permissions_from_user(self, login):
        """
        Revoke all the permissions from a given user

        @type login: str
        @param login: login of the user to revoke all permissions from

        @rtype: bool
        @return: True on success
        """
        for permission in factory.permission_query_manager().find_all():
            if login not in permission['users']:
                continue
            del permission['users'][login]
            if permission['users']:
                Permission.get_collection().save(permission, safe=True)
            else:
                # Delete entire permission if there are no more users
                Permission.get_collection().remove({'resource':permission['resource']}, safe=True)


grant = task(PermissionManager.grant, base=Task, ignore_result=True)
revoke = task(PermissionManager.revoke, base=Task, ignore_result=True)
