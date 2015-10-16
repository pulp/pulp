"""
Contains legacy manager code that is required for migrations.
"""

import logging
import re

from pulp.server import config
from pulp.server.db.connection import get_collection
from pulp.server.db import model
from pulp.server.db.model.repository import RepoContentUnit, RepoImporter
from pulp.server.exceptions import DuplicateResource, InvalidValue, MissingResource
from pulp.server.managers import factory
from pulp.server.managers.auth.role.cud import SUPER_USER_ROLE
from pulp.server.webservices.views import serializers


_logger = logging.getLogger(__name__)


_USER_LOGIN_REGEX = re.compile(r'^[.\-_A-Za-z0-9]+$')
NUM_ITERATIONS = 5000


class RepoManager(object):
    """
    Performs repository related functions relating to both CRUD operations and
    actions performed on or by repositories.
    """
    @staticmethod
    def rebuild_content_unit_counts(repo_ids=None):
        """
        WARNING: This might take a long time, and it should not be used unless
        absolutely necessary. Not responsible for melted servers.

        This will iterate through the given repositories, which defaults to ALL
        repositories, and recalculate the content unit counts for each content
        type.

        This method is called from platform migration 0004, so consult that
        migration before changing this method.

        :param repo_ids:    list of repository IDs. DEFAULTS TO ALL REPO IDs!!!
        :type  repo_ids:    list
        """
        association_collection = RepoContentUnit.get_collection()

        # This line is the only difference between this lib and the original manager code. It
        # functions the same way, but the old way of accessing the collection no longer exists.
        repo_collection = get_collection('repos')

        # default to all repos if none were specified
        if not repo_ids:
            repo_ids = [repo['id'] for repo in repo_collection.find(fields=['id'])]

        _logger.info('regenerating content unit counts for %d repositories' % len(repo_ids))

        for repo_id in repo_ids:
            _logger.debug('regenerating content unit count for repository "%s"' % repo_id)
            counts = {}
            cursor = association_collection.find({'repo_id': repo_id})
            type_ids = cursor.distinct('unit_type_id')
            cursor.close()
            for type_id in type_ids:
                spec = {'repo_id': repo_id, 'unit_type_id': type_id}
                counts[type_id] = association_collection.find(spec).count()
            repo_collection.update({'id': repo_id}, {'$set': {'content_unit_counts': counts}},
                                   safe=True)

    @staticmethod
    def find_with_importer_type(importer_type_id):
        """
        This originally lived in the RepoQueryManager.

        This code is now used in a pulp_rpm migration, which is done after the `id` to `repo_id`
        migration.
        """

        results = []
        repo_importers = list(
            RepoImporter.get_collection().find({'importer_type_id': importer_type_id}))
        for ri in repo_importers:
            repo_obj = model.Repository.objects.get(repo_id=ri['repo_id'])
            repo = serializers.Repository(repo_obj).data
            repo['importers'] = [ri]
            results.append(repo)

        return results


class UserManager(object):

    def ensure_admin(self):
        """
        This function ensures that there is at least one super user for the system.
        If no super users are found, the default admin user (from the pulp config)
        is looked up or created and added to the super users role.
        """
        role_manager = factory.role_manager()
        if self.get_admins():
            return

        default_login = config.config.get('server', 'default_login')

        admin = get_collection('users').find_one({'login': default_login})
        if admin is None:
            default_password = config.config.get('server', 'default_password')
            _logger.warn('ensure admin')
            admin = UserManager.create_user(login=default_login,
                                            password=default_password)

        role_manager.add_user_to_role(SUPER_USER_ROLE, default_login)

    @staticmethod
    def get_admins():
        """
        Get a list of users with the super-user role.

        :return: list of users who are admins.
        :rtype:  list of User
        """
        try:
            super_users = UserManager.find_users_belonging_to_role(SUPER_USER_ROLE)
            return super_users
        except MissingResource:
            return None

    @staticmethod
    def find_users_belonging_to_role(role_id):
        """
        Get a list of users belonging to the given role

        @type role_id: str
        @param role_id: id of the role to get members of

        @rtype: list of L{pulp.server.db.model.auth.User} instances
        @return: list of users that are members of the given role
        """
        role = get_collection('roles').find_one({'id': role_id})
        if role is None:
            raise MissingResource(role_id)

        users = []
        for user in UserManager.find_all():
            if role_id in user['roles']:
                users.append(user)
        return users

    @staticmethod
    def find_all():
        """
        Returns serialized versions of all users in the database.

        @return: list of serialized users
        @rtype:  list of dict
        """
        all_users = list(get_collection('users').find())
        for user in all_users:
            user.pop('password', None)
        return all_users

    @staticmethod
    def create_user(login, password=None, name=None, roles=None):
        """
        Creates a new Pulp user and adds it to specified to roles.

        @param login: login name / unique identifier for the user
        @type  login: str

        @param password: password for login credentials
        @type  password: str

        @param name: user's full name
        @type  name: str

        @param roles: list of roles user will belong to
        @type  roles: list

        @raise DuplicateResource: if there is already a user with the requested login
        @raise InvalidValue: if any of the fields are unacceptable
        """

        existing_user = get_collection('users').find_one({'login': login})
        if existing_user is not None:
            raise DuplicateResource(login)

        invalid_values = []

        if login is None or _USER_LOGIN_REGEX.match(login) is None:
            invalid_values.append('login')
        if invalid_type(name, basestring):
            invalid_values.append('name')
        if invalid_type(roles, list):
            invalid_values.append('roles')

        if invalid_values:
            raise InvalidValue(invalid_values)

        # Use the login for name of the user if one was not specified
        name = name or login
        roles = roles or None

        # Creation
        create_me = model.User(login=login, name=name, roles=roles)
        create_me.set_password(password)
        create_me.save()

        # Grant permissions
        permission_manager = factory.permission_manager()
        permission_manager.grant_automatic_permissions_for_user(create_me.login)

        # Retrieve the user to return the SON object
        created = get_collection('users').find_one({'login': login})
        created.pop('password')

        return created


def invalid_type(input_value, valid_type):
    """
    Returns whether the input value is the type given.

    :return: true if input_value is not of valid_type
    :rtype:  bool
    """
    if input_value is not None and not isinstance(input_value, valid_type):
        return True
    return False
