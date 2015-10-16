"""
Contains the manager class and exceptions for operations surrounding the creation,
update, and deletion on a Pulp Role.
"""
import re
from gettext import gettext as _

from celery import task

from pulp.server.constants import SUPER_USER_ROLE
from pulp.server.async.tasks import Task
from pulp.server.auth.authorization import CREATE, READ, UPDATE, DELETE, EXECUTE, \
    _operations_not_granted_by_roles
from pulp.server.controllers import user as user_controller
from pulp.server.db import model
from pulp.server.db.model.auth import Role
from pulp.server.exceptions import (DuplicateResource, InvalidValue, MissingResource,
                                    PulpDataException)
from pulp.server.managers import factory


_ROLE_NAME_REGEX = re.compile(r'^[\-_A-Za-z0-9]+$')  # letters, numbers, underscore, hyphen


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

        :return: The created object
        :rtype: dict
        """
        existing_role = Role.get_collection().find_one({'id': role_id})
        if existing_role is not None:
            raise DuplicateResource(role_id)

        if role_id is None or _ROLE_NAME_REGEX.match(role_id) is None:
            raise InvalidValue(['role_id'])

        # Use the ID for the display name if one was not specified
        display_name = display_name or role_id

        # Creation
        create_me = Role(id=role_id, display_name=display_name, description=description)
        Role.get_collection().save(create_me)

        # Retrieve the role to return the SON object
        created = Role.get_collection().find_one({'id': role_id})

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

        :return: The updated object
        :rtype: dict
        """
        delta.pop('id', None)

        role = Role.get_collection().find_one({'id': role_id})
        if role is None:
            raise MissingResource(role_id)

        for key, value in delta.items():
            # simple changes
            if key in ('display_name', 'description',):
                role[key] = value
                continue

            # unsupported
            raise PulpDataException(_("Update Keyword [%s] is not supported" % key))

        Role.get_collection().save(role)

        # Retrieve the user to return the SON object
        updated = Role.get_collection().find_one({'id': role_id})
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
        :raise PulpDataException: if role is a superuser role
        """
        # Raise exception if role id is invalid
        if role_id is None or not isinstance(role_id, basestring):
            raise InvalidValue(['role_id'])

        # Check whether role exists
        role = Role.get_collection().find_one({'id': role_id})
        if role is None:
            raise MissingResource(role_id)

        # Make sure role is not a superuser role
        if role_id == SUPER_USER_ROLE:
            raise PulpDataException(_('Role %s cannot be changed') % role_id)

        # Remove respective roles from users
        users_with_role = user_controller.find_users_belonging_to_role(role_id)

        for item in role['permissions']:
            for user in users_with_role:
                other_roles = factory.role_query_manager().get_other_roles(role, user.roles)
                user_ops = _operations_not_granted_by_roles(item['resource'],
                                                            item['permission'], other_roles)
                factory.permission_manager().revoke(item['resource'], user.login, user_ops)

        for user in users_with_role:
            user.roles.remove(role_id)
            user.save()

        Role.get_collection().remove({'id': role_id})

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
        :raise InvalidValue: if some params are invalid
        :raise PulpDataException: if role is a superuser role
        """
        if role_id == SUPER_USER_ROLE:
            raise PulpDataException(_('super-users role cannot be changed'))

        role = Role.get_collection().find_one({'id': role_id})
        if role is None:
            raise InvalidValue(['role_id'])
        if not role['permissions']:
            role['permissions'] = []

        resource_permission = {}
        current_ops = []
        for item in role['permissions']:
            if item['resource'] == resource:
                resource_permission = item
                current_ops = resource_permission['permission']

        if not resource_permission:
            resource_permission = dict(resource=resource, permission=current_ops)
            role['permissions'].append(resource_permission)

        for o in operations:
            if o in current_ops:
                continue
            current_ops.append(o)

        users = user_controller.find_users_belonging_to_role(role_id)
        for user in users:
            factory.permission_manager().grant(resource, user.login, operations)

        Role.get_collection().save(role)

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
        :raise InvalidValue: if some params are invalid
        :raise PulpDataException: if role is a superuser role
        """
        if role_id == SUPER_USER_ROLE:
            raise PulpDataException(_('super-users role cannot be changed'))

        role = Role.get_collection().find_one({'id': role_id})
        if role is None:
            raise InvalidValue(['role_id'])

        resource_permission = {}
        current_ops = []
        for item in role['permissions']:
            if item['resource'] == resource:
                resource_permission = item
                current_ops = resource_permission['permission']

        if not current_ops:
            return
        for o in operations:
            if o not in current_ops:
                continue
            current_ops.remove(o)

        users = user_controller.find_users_belonging_to_role(role_id)
        for user in users:
            other_roles = factory.role_query_manager().get_other_roles(role, user.roles)
            user_ops = _operations_not_granted_by_roles(resource,
                                                        operations,
                                                        other_roles)
            factory.permission_manager().revoke(resource, user.login, user_ops)

        # in no more allowed operations, remove the resource
        if not current_ops:
            role['permissions'].remove(resource_permission)

        Role.get_collection().save(role)

    @staticmethod
    def add_user_to_role(role_id, login):
        """
        Add a user to a role. This has the side-effect of granting all the
        permissions granted to the role to the user.

        :param role_id:         role identifier
        :type  role_id:         str
        :param login:           login of user
        :type  login:           str
        :raise MissingResource: if the given role does not exist
        :raise InvalidValue: if some params are invalid
        """
        role = Role.get_collection().find_one({'id': role_id})
        if role is None:
            raise MissingResource(role_id)

        user = model.User.objects(login=login).first()
        if user is None:
            raise InvalidValue(['login'])

        if role_id in user.roles:
            return

        user.roles.append(role_id)
        user.save()
        for item in role['permissions']:
            factory.permission_manager().grant(item['resource'], login,
                                               item.get('permission', []))

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
        :raise MissingResource: if the given role or user does not exist
        """
        role = Role.get_collection().find_one({'id': role_id})
        if role is None:
            raise MissingResource(role_id)

        user = model.User.objects.get_or_404(login=login)

        if role_id == SUPER_USER_ROLE and user_controller.is_last_super_user(login):
            raise PulpDataException(
                _('%(role)s cannot be empty, and %(login)s is the last member') %
                {'role': SUPER_USER_ROLE, 'login': login})

        if role_id not in user.roles:
            return

        user.roles.remove(role_id)
        user.save()

        for item in role['permissions']:
            other_roles = factory.role_query_manager().get_other_roles(role, user.roles)
            user_ops = _operations_not_granted_by_roles(item['resource'],
                                                        item['permission'],
                                                        other_roles)
            factory.permission_manager().revoke(item['resource'], login, user_ops)

    def ensure_super_user_role(self):
        """
        Ensure that the super user role exists.
        """
        role = self.get_role(SUPER_USER_ROLE)
        if role is None:
            role = self.create_role(SUPER_USER_ROLE, 'Super Users',
                                    'Role indicates users with admin privileges')
            role['permissions'] = [{'resource': '/',
                                    'permission': [CREATE, READ, UPDATE, DELETE, EXECUTE]}]
            Role.get_collection().save(role)

    @staticmethod
    def get_role(role):
        """
        Get a Role by id.

        :param role: A role id to search for
        :type  role: str

        :return: a Role object that have the given role id.
        :rtype:  Role or None
        """
        return Role.get_collection().find_one({'id': role})


add_permissions_to_role = task(RoleManager.add_permissions_to_role, base=Task, ignore_result=True)
add_user_to_role = task(RoleManager.add_user_to_role, base=Task, ignore_result=True)
create_role = task(RoleManager.create_role, base=Task)
delete_role = task(RoleManager.delete_role, base=Task, ignore_result=True)
remove_permissions_from_role = task(RoleManager.remove_permissions_from_role, base=Task,
                                    ignore_result=True)
remove_user_from_role = task(RoleManager.remove_user_from_role, base=Task, ignore_result=True)
update_role = task(RoleManager.update_role, base=Task)
