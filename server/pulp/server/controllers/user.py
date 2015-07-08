from gettext import gettext as _

from mongoengine import NotUniqueError, ValidationError

from pulp.server import exceptions as pulp_exceptions
from pulp.server.constants import SUPER_USER_ROLE
from pulp.server.db import model
from pulp.server.db.model.auth import Permission, Role
from pulp.server.managers import factory as manager_factory


def create_user(login, password=None, name=None, roles=None):
    """
    Creates a new Pulp user and adds it to specified to roles.

    :param login: login name / unique identifier for the user
    :type  login: str
    :param password: password for login credentials
    :type  password: str
    :param name: user's full name
    :type  name: str
    :param roles: list of roles user will belong to
    :type  roles: list

    :raise DuplicateResource: if there is already a user with the requested login
    :raise InvalidValue: if any of the fields are unacceptable
    """
    user = model.User(login=login, name=name, roles=roles)
    user.set_password(password)
    try:
        user.save()
    except NotUniqueError:
        raise pulp_exceptions.DuplicateResource(login)
    except ValidationError, e:
        raise pulp_exceptions.InvalidValue(e.to_dict().keys())

    # Grant default user permissions
    permission_manager = manager_factory.permission_manager()
    permission_manager.grant_automatic_permissions_for_user(user.login)
    return user


def update_user(login, delta):
    """
    Updates the user with a delta dict. The delta can only contain fields that may be changed,
    which are name, password, and roles.

    :param login: identifies the user
    :type  login: str
    :param delta: user attributes and their new values
    :type  delta: dict

    :raise InvalidValue: if extra params are passed or params contain invalid values
    """

    user = model.User.objects.get_or_404(login=login)
    user.name = delta.pop('name', user.name)

    password = delta.pop('password', None)
    if password is not None:
        user.set_password(password)

    roles = delta.pop('roles', None)
    if roles:
        if not isinstance(roles, list):
            raise pulp_exceptions.InvalidValue('roles')
        else:
            # Add new roles and remove deleted roles from the user
            role_manager = manager_factory.role_manager()
            roles_to_add = list(set(roles) - set(user.roles))
            roles_to_remove = list(set(user.roles) - set(roles))

            for new_role in roles_to_add:
                role_manager.add_user_to_role(new_role, login)
            for remove_role in roles_to_remove:
                role_manager.remove_user_from_role(remove_role, login)
            user.roles = roles

    # Raise before save if extra values were passed
    if delta:
        raise pulp_exceptions.InvalidValue(delta.keys())

    try:
        user.save()
    except ValidationError, e:
        raise pulp_exceptions.InvalidValue(e.to_dict().keys())

    return user


def delete_user(login):
    """
    Deletes the given user. Deletion of last superuser is not permitted.

    :param login: identifies the user being deleted
    :type  login: str

    :raise pulp_exceptions.PulpDataException: if user is the last super user
    """

    user = model.User.objects.get_or_404(login=login)
    if is_last_super_user(login):
        raise pulp_exceptions.PulpDataException(
            _("The last superuser [%s] cannot be deleted" % login))

    # Revoke all permissions from the user
    permission_manager = manager_factory.permission_manager()
    permission_manager.revoke_all_permissions_from_user(login)
    user.delete()


def is_last_super_user(login):
    """
    Check to see if a user is the last super user

    :param user: login of user to check
    :type user: str

    :return: True if the user is the last super user, False otherwise
    :rtype: bool

    :raise PulpDataException: if no super users are found
    """
    user = model.User.objects.get_or_404(login=login)
    if not user.is_superuser():
        return False

    super_users = find_users_belonging_to_role(SUPER_USER_ROLE)
    if not super_users:
        raise pulp_exceptions.PulpDataException(_('no super users defined'))

    if len(super_users) > 1:
        return False

    return True


def is_authorized(resource, login, operation):
    """
    Check to see if a user is authorized to perform an operation on a resource.

    :param resource: pulp resource url
    :type  resource: str
    :param login: login of user to check permissions for
    :type  login: str
    :param operation: operation to be performed on resource
    :type  operation: int

    :return: True if the user is authorized for the operation on the resource, False otherwise
    :rtype: bool
    """
    user = model.User.objects.get_or_404(login=login)
    if user.is_superuser():
        return True

    permission_query_manager = manager_factory.permission_query_manager()

    # User is authorized if they have access to the resource or any of the its base resources.
    parts = [p for p in resource.split('/') if p]
    while parts:
        current_resource = '/%s/' % '/'.join(parts)
        permission = permission_query_manager.find_by_resource(current_resource)
        if permission is not None:
            if operation in permission_query_manager.find_user_permission(permission, login):
                return True
        parts = parts[:-1]

    permission = Permission.get_collection().find_one({'resource': '/'})
    return (permission is not None and
            operation in permission_query_manager.find_user_permission(permission, login))


def find_users_belonging_to_role(role_id):
    """
    Get a list of users belonging to the given role

    :param role_id: get members of this role
    :type  role_id: str

    :return: list of users that are members of the given role
    :rtype:  list of pulp.server.db.model.User instances
    """
    role = Role.get_collection().find_one({'id': role_id})
    if role is None:
        raise pulp_exceptions.MissingResource(role_id)
    return [user for user in model.User.objects() if role_id in user.roles]
