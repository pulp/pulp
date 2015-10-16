import mock
from mongoengine import NotUniqueError, ValidationError

from pulp.common.compat import unittest
from pulp.server import exceptions as pulp_exceptions
from pulp.server.controllers import user as user_controller

import logging
log = logging.getLogger(__name__)


@mock.patch('pulp.server.controllers.user.model.User')
@mock.patch('pulp.server.controllers.user.manager_factory')
class TestCreateUser(unittest.TestCase):
    """
    Tests for the creation of a user.
    """

    def test_duplicate_user(self, mock_f, mock_model):
        """
        Test handling of Mongoengine's NotUniqueError.
        """
        mock_user = mock_model.return_value
        mock_user.save.side_effect = NotUniqueError()
        try:
            user_controller.create_user('new_user')
        except pulp_exceptions.DuplicateResource, e:
            pass
        else:
            raise AssertionError('Duplicate resource should be raised if user is not unique.')
        self.assertDictEqual({'resource_id': 'new_user'}, e.data_dict())

    def test_validation_error(self, mock_f, mock_model):
        """
        Test handling of Mongoengine's ValidationError.
        """
        mock_user = mock_model.return_value
        mock_user.save.side_effect = ValidationError()
        self.assertRaises(pulp_exceptions.InvalidValue, user_controller.create_user, 'invalid&')

    def test_as_expected(self, mock_f, mock_model):
        """
        Test the creatation of a new users that works as expected.
        """
        mock_perm_manager = mock_f.permission_manager()
        user = user_controller.create_user('curiosity', password='pahump_hills')
        mock_perm_manager.grant_automatic_permissions_for_user.assert_called_once_with(user.login)
        user.set_password.assert_called_once_with('pahump_hills')
        self.assertTrue(user is mock_model.return_value)


@mock.patch('pulp.server.controllers.user.model.User')
@mock.patch('pulp.server.controllers.user.manager_factory')
class TestUpdateUser(unittest.TestCase):
    """
    Tests for updating a user.
    """

    def test_update_as_expected(self, mock_f, mock_model):
        """
        Test the expected path of a successful update.
        """
        m_user = mock_model.objects.get_or_404.return_value
        m_user.roles = ['photograph', 'skycrane']
        delta = {'password': 'marius_pass', 'roles': ['analyze', 'photograph']}
        m_role_manager = mock_f.role_manager.return_value
        updated = user_controller.update_user('curiosity', delta)

        m_role_manager.add_user_to_role('analyze', 'curiosity')
        m_role_manager.remove_user_from_role('skycrane', 'curiosity')
        m_user.set_password.assert_called_once_with('marius_pass')
        m_user.save.assert_called_once_with()
        m_user.roles = ['analyze', 'photograph']
        self.assertTrue(updated is m_user)

    def test_invalid_value(self, mock_f, mock_model):
        """
        Test the handling of a Mongoengine Validation error on update.
        """
        m_user = mock_model.objects.get_or_404.return_value
        delta = {'name': 'invalid&name'}
        m_user.save.side_effect = ValidationError()
        self.assertRaises(pulp_exceptions.InvalidValue, user_controller.update_user,
                          'curiosity', delta)

    def test_extra_param(self, mock_f, mock_model):
        """
        Test the handling of a Mongoengine Validation error on update.
        """
        delta = {'invalid': 'key'}
        self.assertRaises(pulp_exceptions.InvalidValue, user_controller.update_user,
                          'curiosity', delta)

    def test_invalid_roles(self, mock_f, mock_model):
        """
        Test the handling of non-list of roles.
        """
        delta = {'roles': 'not a list'}
        self.assertRaises(pulp_exceptions.InvalidValue, user_controller.update_user,
                          'curiosity', delta)


@mock.patch('pulp.server.controllers.user.is_last_super_user')
@mock.patch('pulp.server.controllers.user.model.User')
@mock.patch('pulp.server.controllers.user.manager_factory')
class TestDeleteUser(unittest.TestCase):
    """
    Tests for deleting a user.
    """

    def test_as_expected(self, mock_f, mock_model, mock_last_su):
        """
        Test delete that works as expected.
        """
        mock_last_su.return_value = False
        m_permission_manager = mock_f.permission_manager.return_value
        user_controller.delete_user('curiosity')

        m_permission_manager.revoke_all_permissions_from_user.assert_called_once_with('curiosity')
        mock_model.objects.get_or_404.return_value.delete.assert_called_once_with()

    def test_last_super_user(self, mock_f, mock_model, mock_last_su):
        """
        Test an attempted delete of the last super user.
        """
        mock_last_su.return_value = True
        m_permission_manager = mock_f.permission_manager.return_value
        self.assertRaises(pulp_exceptions.PulpDataException, user_controller.delete_user,
                          'curiosity')
        self.assertFalse(m_permission_manager.revoke_all_permissions_from_user.called)


@mock.patch('pulp.server.controllers.user.find_users_belonging_to_role')
@mock.patch('pulp.server.controllers.user.model.User')
class TestIsLastSuperUser(unittest.TestCase):
    """
    Tests for determining whether a user is the last remaining super user.
    """

    def test_user_not_su(self, mock_model, mock_find_users_w_role):
        """
        Should return False if the user is not a super user.
        """
        m_user = mock_model.objects.get_or_404.return_value
        m_user.is_superuser.return_value = False
        self.assertFalse(user_controller.is_last_super_user('test'))

    def test_multiple_sus(self, mock_model, mock_find_users_w_role):
        """
        Should return False if there are more than one super user.
        """
        mock_find_users_w_role.return_value = ['su1', 'su2']
        self.assertFalse(user_controller.is_last_super_user('test'))

    def test_no_sus(self, mock_model, mock_find_users_w_role):
        """
        Should raise an exception if there are no super users.
        """
        mock_find_users_w_role.return_value = []
        self.assertRaises(pulp_exceptions.PulpDataException, user_controller.is_last_super_user,
                          'test')

    def test_user_is_last_su(self, mock_model, mock_find_users_w_role):
        """
        Should return True if there is one super user, the one requested.
        """
        m_user = mock_model.objects.get_or_404.return_value
        mock_find_users_w_role.return_value = [m_user]
        self.assertTrue(user_controller.is_last_super_user('test'))


@mock.patch('pulp.server.controllers.user.manager_factory')
@mock.patch('pulp.server.controllers.user.model.User')
class TestIsAuthorized(unittest.TestCase):
    """
    Tests for determining whether a user is authorized to view a resource.
    """

    def test_super_user(self, mock_model, mock_f):
        """
        Ensure that super users have access to everything.
        """
        m_user = mock_model.objects.get_or_404.return_value
        m_user.is_superuser.return_value = True
        self.assertTrue(m_user.is_superuser('some_resource', 'superuser', 'op'))

    def test_explicit_access(self, mock_model, mock_f):
        """
        Ensure that a user with access to a resource url is authorized for it.
        """
        m_user = mock_model.objects.get_or_404.return_value
        m_user.is_superuser.return_value = False
        mock_pqm = mock_f.permission_query_manager.return_value
        mock_pqm.find_by_resource.return_value = '/mock/resource/'
        mock_pqm.find_user_permission.return_value = ['op']

        self.assertTrue(user_controller.is_authorized('/mock/resource/', 'testuser', 'op'))
        mock_pqm.find_by_resource.assert_called_once_with('/mock/resource/')
        mock_pqm.find_user_permission.assert_called_once_with('/mock/resource/', 'testuser')

    def test_subdomain_access(self, mock_model, mock_f):
        """
        Ensure that a user with access to the subdomain of a url has access to the url.
        """

        def base_only(permission, login):
            """
            Simulate permission over a subdomain, but nothing else.
            """
            if permission == '/mock/':
                return ['op']
            else:
                return []

        m_user = mock_model.objects.get_or_404.return_value
        m_user.is_superuser.return_value = False
        mock_pqm = mock_f.permission_query_manager.return_value
        mock_pqm.find_by_resource.side_effect = lambda x: x
        mock_pqm.find_user_permission.side_effect = base_only

        self.assertTrue(user_controller.is_authorized('/mock/resource/', 'test-user', 'op'))
        self.assertTrue(user_controller.is_authorized('/mock/other_resource/', 'test-user', 'op'))
        self.assertFalse(user_controller.is_authorized('/other/', 'test-user', 'op'))
        self.assertFalse(user_controller.is_authorized('/', 'test-user', 'op'))

    @mock.patch('pulp.server.controllers.user.Permission.get_collection')
    def test_root_access(self, mock_perm_collection, mock_model, mock_f):
        """
        Ensure that a user that has access to the root domain '/' has access to everything.
        """

        def root_only(permission, login):
            """
            Simulate permission over root domain, but nothing else.
            """
            if permission == '/':
                return ['op']
            else:
                return []

        m_user = mock_model.objects.get_or_404.return_value
        m_user.is_superuser.return_value = False
        mock_pqm = mock_f.permission_query_manager.return_value
        mock_pqm.find_by_resource.side_effect = lambda x: x
        mock_pqm.find_user_permission.side_effect = root_only
        mock_perm_collection.return_value.find_one.return_value = '/'

        self.assertTrue(user_controller.is_authorized('/mock/resource/', 'test-user', 'op'))
        self.assertTrue(user_controller.is_authorized('/mock/other_resource/', 'test-user', 'op'))
        self.assertTrue(user_controller.is_authorized('/', 'test-user', 'op'))


@mock.patch('pulp.server.controllers.user.Role.get_collection')
class TestFindUsersBelongingToRole(unittest.TestCase):
    """
    Tests for finding a list of users that belong to a role.
    """

    def test_role_does_not_exist(self, mock_role):
        """
        Ensure that a MissingResource is raised if the role does not exist.
        """
        mock_role.return_value.find_one.return_value = None
        self.assertRaises(
            pulp_exceptions.MissingResource, user_controller.find_users_belonging_to_role, 'role')

    @mock.patch('pulp.server.controllers.user.model.User.objects')
    def test_as_expected(self, mock_user_qs, mock_role):
        """
        Test finding the list of users with roles.
        """
        user_1 = mock.MagicMock()
        user_2 = mock.MagicMock()

        user_3 = mock.MagicMock()
        user_1.roles = ['role_1', 'role_2']
        user_2.roles = ['role_2', 'role_3']
        user_3.roles = ['role_3', 'role_4']
        mock_user_qs.return_value = [user_1, user_2, user_3]
        users_with_role = user_controller.find_users_belonging_to_role('role_2')
        self.assertEqual(sorted(users_with_role), sorted([user_1, user_2]))
