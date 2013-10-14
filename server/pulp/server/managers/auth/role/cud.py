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
import logging
import re
from gettext import gettext as _

from celery import task

from pulp.server.async.tasks import Task
from pulp.server.auth.authorization import _operations_not_granted_by_roles
from pulp.server.db.model.auth import Role, User
from pulp.server.exceptions import (DuplicateResource, InvalidValue, MissingResource,
                                    PulpDataException)
from pulp.server.managers import factory
from pulp.server.util import Delta


SUPER_USER_ROLE = 'super-users'
_ROLE_NAME_REGEX = re.compile(r'^[\-_A-Za-z0-9]+$') # letters, numbers, underscore, hyphen


class RoleManager(object):
    """
    Performs role related functions relating to CRUD operations.
    """
    @staticmethod
    def create_role(role_id, display_name=None, description=None):
        """
        Creates a new Pulp role.

        :param role_id:           unique identifier for the role
        :type  role_id:           str
        :param display_name:      user-readable name of the role
        :type  display_name:      str
        :param description:       free form text used to describe the role
        :type  description:       str
        :raise DuplicateResource: if there is already a role with the requested name
        :raise InvalidValue:      if any of the fields are unacceptable
        """
        existing_role = Role.get_collection().find_one({'id' : role_id})
        if existing_role is not None:
            raise DuplicateResource(role_id)

        if role_id is None or _ROLE_NAME_REGEX.match(role_id) is None:
            raise InvalidValue(['role_id'])

        # Use the ID for the display name if one was not specified
        display_name = display_name or role_id

        # Creation
        create_me = Role(id=role_id, display_name=display_name, description=description)
        Role.get_collection().save(create_me, safe=True)

        # Retrieve the role to return the SON object
        created = Role.get_collection().find_one({'id' : role_id})

        return created

    @staticmethod
    def update_role(role_id, delta):
        """
        Updates a role object.

        :param role_id:           The role identifier.
        :type  role_id:           str
        :param delta:             A dict containing update keywords.
        :type  delta:             dict
        :return:                  The updated object
        :rtype:                   dict
        :raise MissingResource:   if the given role does not exist
        :raise PulpDataException: if update keyword  is not supported
        """
        delta.pop('id', None)

        role = Role.get_collection().find_one({'id' : role_id})
        if role is None:
            raise MissingResource(role_id)

        for key, value in delta.items():
            # simple changes
            if key in ('display_name', 'description', 'permissions',):
                role[key] = value
                continue

            # unsupported
            raise PulpDataException(_("Update Keyword [%s] is not supported" % key))

        Role.get_collection().save(role, safe=True)

        # Retrieve the user to return the SON object
        updated = Role.get_collection().find_one({'id' : role_id})
        return updated

    @staticmethod
    def delete_role(role_id):
        """
        Deletes the given role. This has the side-effect of revoking any permissions granted
        to the role from the users in the role, unless those permissions are also granted 
        through another role the user is a memeber of.

        :param role_id:         identifies the role being deleted
        :type  role_id:         str
        :raise InvalidValue:    if any of the fields are unacceptable
        :raise MissingResource: if the given role does not exist
        """
        # Raise exception if role id is invalid
        if role_id is None or not isinstance(role_id, basestring):
            raise InvalidValue(['role_id'])

        # Check whether role exists
        role = Role.get_collection().find_one({'id' : role_id})
        if role is None:
            raise MissingResource(role_id)

        # Make sure role is not a superuser role
        if role_id == SUPER_USER_ROLE:
            raise PulpDataException(_('Role %s cannot be changed') % role_id)

        # Remove respective roles from users
        users = factory.user_query_manager().find_users_belonging_to_role(role_id)
        for resource, operations in role['permissions'].items():
            for user in users:
                other_roles = factory.role_query_manager().get_other_roles(role, user['roles'])
                user_ops = _operations_not_granted_by_roles(resource, operations, other_roles)
                factory.permission_manager().revoke(resource, user['login'], user_ops)

        for user in users:
            user['roles'].remove(role_id)
            factory.user_manager().update_user(user['login'], Delta(user, 'roles'))

        Role.get_collection().remove({'id' : role_id}, safe=True)

    @staticmethod
    def add_permissions_to_role(role_id, resource, operations):
        """
        Add permissions to a role. 

        :param role_id:         role identifier
        :type  role_id:         str
        :param resource:        resource path to grant permissions to
        :type  resource:        str
        :param operations:      list or tuple
        :type  operations:      list of allowed operations being granted
        :raise MissingResource: if the given role does not exist
        """
        if role_id == SUPER_USER_ROLE:
            raise PulpDataException(_('super-users role cannot be changed'))

        role = Role.get_collection().find_one({'id' : role_id})
        if role is None:
            raise MissingResource(role_id)

        current_ops = role['permissions'].setdefault(resource, [])
        for o in operations:
            if o in current_ops:
                continue
            current_ops.append(o)

        users = factory.user_query_manager().find_users_belonging_to_role(role_id)
        for user in users:
            factory.permission_manager().grant(resource, user['login'], operations)

        Role.get_collection().save(role, safe=True)

    @staticmethod
    def remove_permissions_from_role(role_id, resource, operations):
        """
        Remove permissions from a role. 
        
        :param role_id:         role identifier
        :type  role_id:         str
        :param resource:        resource path to revoke permissions from
        :type  resource:        str
        :param operations:      list or tuple
        :type  operations:      list of allowed operations being revoked
        :raise MissingResource: if the given role does not exist
        """
        if role_id == SUPER_USER_ROLE:
            raise PulpDataException(_('super-users role cannot be changed'))

        role = Role.get_collection().find_one({'id' : role_id})
        if role is None:
            raise MissingResource(role_id)

        current_ops = role['permissions'].get(resource, [])
        if not current_ops:
            return
        for o in operations:
            if o not in current_ops:
                continue
            current_ops.remove(o)

        users = factory.user_query_manager().find_users_belonging_to_role(role_id)
        for user in users:
            other_roles = factory.role_query_manager().get_other_roles(role, user['roles'])
            user_ops = _operations_not_granted_by_roles(resource,
                                                    operations,
                                                    other_roles)
            factory.permission_manager().revoke(resource, user['login'], user_ops)

        # in no more allowed operations, remove the resource
        if not current_ops:
            del role['permissions'][resource]

        Role.get_collection().save(role, safe=True)

    @staticmethod
    def add_user_to_role(role_id, login):
        """
        Add a user to a role. This has the side-effect of granting all the
        permissions granted to the role to the user.
        
        :param role_id:         role identifier
        :type  role_id:         str
        :param login:           login of user
        :type  login:           str
        :return:                True on success
        :rtype:                 bool
        :raise MissingResource: if the given role or user does not exist
        """
        role = Role.get_collection().find_one({'id' : role_id})
        if role is None:
            raise MissingResource(role_id)

        user = User.get_collection().find_one({'login' : login})
        if user is None:
            raise MissingResource(login)

        if role_id in user['roles']:
            return

        user['roles'].append(role_id)
        User.get_collection().save(user, safe=True)

        for resource, operations in role['permissions'].items():
            factory.permission_manager().grant(resource, login, operations)

    @staticmethod
    def remove_user_from_role(role_id, login):
        """
        Remove a user from a role. This has the side-effect of revoking all the
        permissions granted to the role from the user, unless the permissions are
        also granted by another role.
        
        :param role_id:         role identifier
        :type  role_id:         str
        :param login:           name of user
        :type  login:           str
        :return:                True on success
        :rtype:                 bool
        :raise MissingResource: if the given role or user does not exist
        """
        role = Role.get_collection().find_one({'id' : role_id})
        if role is None:
            raise MissingResource(role_id)

        user = User.get_collection().find_one({'login' : login})
        if user is None:
            raise MissingResource(login)

        if role_id == SUPER_USER_ROLE and factory.user_query_manager().is_last_super_user(login):
            raise PulpDataException(_('%s cannot be empty, and %s is the last member') %
                                     (SUPER_USER_ROLE, login))

        if role_id not in user['roles']:
            return

        user['roles'].remove(role_id)
        User.get_collection().save(user, safe=True)

        for resource, operations in role['permissions'].items():
            other_roles = factory.role_query_manager().get_other_roles(role, user['roles'])
            user_ops = _operations_not_granted_by_roles(resource,
                                                        operations,
                                                        other_roles)
            factory.permission_manager().revoke(resource, login, user_ops)

    def ensure_super_user_role(self):
        """
        Ensure that the super user role exists.
        """
        role = Role.get_collection().find_one({'id' : SUPER_USER_ROLE})
        if role is None:
            role = self.create_role(SUPER_USER_ROLE, 'Super Users',
                                    'Role indicates users with admin privileges')
            pm = factory.permission_manager()
            role['permissions'] = {'/':[pm.CREATE, pm.READ, pm.UPDATE, pm.DELETE, pm.EXECUTE]}
            Role.get_collection().save(role, safe=True)


add_permissions_to_role = task(RoleManager.add_permissions_to_role, base=Task, ignore_result=True)
add_user_to_role = task(RoleManager.add_user_to_role, base=Task, ignore_result=True)
create_role = task(RoleManager.create_role, base=Task)
delete_role = task(RoleManager.delete_role, base=Task, ignore_result=True)
remove_permissions_from_role = task(RoleManager.remove_permissions_from_role, base=Task,
                                    ignore_result=True)
remove_user_from_role = task(RoleManager.remove_user_from_role, base=Task, ignore_result=True)
update_role = task(RoleManager.update_role, base=Task)
