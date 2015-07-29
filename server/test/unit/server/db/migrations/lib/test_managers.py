import functools

import mock

from ..... import base
from pulp.common.compat import unittest
from pulp.devel import mock_plugins
from pulp.plugins.loader import api as plugin_api
from pulp.server import exceptions
from pulp.server.db import model
from pulp.server.db.model.repository import RepoDistributor
from pulp.server.db.model import TaskStatus
from pulp.server.db.migrations.lib import managers


@mock.patch('pulp.server.db.migrations.lib.managers.get_collection')
@mock.patch('pulp.server.db.model.repository.RepoContentUnit.get_collection')
class RepoManagerTests(base.ResourceReservationTests):
    """
    Legacy tests for the RepoManager methods that were preserved for migrations.
    """

    def setUp(self):
        super(RepoManagerTests, self).setUp()

        plugin_api._create_manager()
        mock_plugins.install()

        # Create the manager instance to test
        self.manager = managers.RepoManager()

    def tearDown(self):
        super(RepoManagerTests, self).tearDown()
        mock_plugins.reset()

    def clean(self):
        super(RepoManagerTests, self).clean()

        model.Repository.drop_collection()
        model.Importer.drop_collection()
        RepoDistributor.get_collection().remove()
        TaskStatus.objects().delete()

    def test_rebuild_content_unit_counts(self, mock_get_assoc_col, mock_get_repo_col):
        # platform migration 0004 has a test for this that uses live data

        repo_col = mock_get_repo_col.return_value
        find = mock_get_assoc_col.return_value.find
        cursor = find.return_value
        cursor.distinct.return_value = ['rpm', 'srpm']
        cursor.count.return_value = 6

        self.manager.rebuild_content_unit_counts(['repo1'])

        # once to get the type_ids, then once more for each of the 2 types
        self.assertEqual(find.call_count, 3)
        find.assert_any_call({'repo_id': 'repo1'})
        find.assert_any_call({'repo_id': 'repo1', 'unit_type_id': 'rpm'})
        find.assert_any_call({'repo_id': 'repo1', 'unit_type_id': 'srpm'})

        self.assertEqual(repo_col.update.call_count, 1)
        repo_col.update.assert_called_once_with(
            {'id': 'repo1'},
            {'$set': {'content_unit_counts': {'rpm': 6, 'srpm': 6}}},
            safe=True
        )

    def test_rebuild_default_all_repos(self, mock_get_assoc_col, mock_get_repo_col):
        repo_col = mock_get_repo_col.return_value
        repo_col.find.return_value = [{'id': 'repo1'}, {'id': 'repo2'}]

        assoc_col = mock_get_assoc_col.return_value
        # don't return any type IDs
        assoc_col.find.return_value.distinct.return_value = []

        self.manager.rebuild_content_unit_counts()

        # makes sure it found these 2 repos and tried to operate on them
        assoc_col.find.assert_any_call({'repo_id': 'repo1'})
        assoc_col.find.assert_any_call({'repo_id': 'repo2'})
        self.assertEqual(assoc_col.find.call_count, 2)


@mock.patch('pulp.server.db.migrations.lib.managers.serializers.Repository')
@mock.patch('pulp.server.db.migrations.lib.managers.model.Repository.objects')
@mock.patch('pulp.server.db.migrations.lib.managers.get_collection')
class TestRepoMangerFindWithImporterType(base.PulpServerTests):
    """
    Tests for finding repositories by importer type.
    """

    def test_find_with_importer_type(self, mock_coll, mock_repo_qs, mock_repo_ser):
        """
        Ensure that repos are found and importers are placed into them.
        """
        mock_importer_coll = mock_coll.return_value
        mock_repos = {'repo_id': 'repo-a'}
        mock_importers = [{'id': 'imp1', 'repo_id': 'repo-a'}]
        mock_importer_coll.find.return_value = mock_importers
        mock_repo_ser().data = mock_repos

        repos = managers.RepoManager().find_with_importer_type('mock-imp-type')
        self.assertEqual(1, len(repos))

        self.assertEqual(repos[0]['repo_id'], 'repo-a')
        self.assertEqual(1, len(repos[0]['importers']))
        self.assertEqual(repos[0]['importers'][0]['id'], 'imp1')


@mock.patch('pulp.server.db.migrations.lib.managers.get_collection')
@mock.patch('pulp.server.db.migrations.lib.managers.UserManager.get_admins')
@mock.patch('pulp.server.db.migrations.lib.managers.config')
@mock.patch('pulp.server.db.migrations.lib.managers.factory')
class TestUserManagerEnsureAdmin(unittest.TestCase):

    def test_already_admin(self, mock_f, mock_conf, mock_get_admins, mock_col):
        """
        Test that if admins already exist, another is not created.
        """
        mock_get_admins.return_value = 'some admins'
        user_man = managers.UserManager()
        user_man.ensure_admin()
        self.assertFalse(mock_col.called)

    @mock.patch('pulp.server.db.migrations.lib.managers.UserManager.create_user')
    def test_no_admins(self, mock_create, mock_f, mock_conf, mock_get_admins, mock_col):
        """
        Test that if admins do not exist, one is created using the default values.
        """
        mock_get_admins.return_value = False
        mock_conf.config.get.return_value = 'default'
        mock_col.return_value.find_one.return_value = None
        user_man = managers.UserManager()
        user_man.ensure_admin()

        mock_create.assert_called_once_with(login='default', password='default')
        mock_f.role_manager.return_value.add_user_to_role.assert_called_once_with(
            'super-users', 'default')

    @mock.patch('pulp.server.db.migrations.lib.managers.UserManager.create_user')
    def test_admin_without_role(self, mock_create, mock_f, mock_conf, mock_get_admins, mock_col):
        """
        Test that if the default admin user does exist, but does not have admin, it is given admin.
        """
        mock_get_admins.return_value = False
        mock_conf.config.get.return_value = 'default'
        mock_col.return_value.find_one.return_value = 'admin'
        user_man = managers.UserManager()
        user_man.ensure_admin()

        self.assertFalse(mock_create.called)
        mock_f.role_manager.return_value.add_user_to_role.assert_called_once_with(
            'super-users', 'default')


@mock.patch('pulp.server.db.migrations.lib.managers.UserManager.find_users_belonging_to_role')
class TestGetAdmins(unittest.TestCase):
    """
    Test retrieval of all super users.
    """

    def test_sus_exist(self, mock_find_u_with_role):
        """
        Test that super users are returned if they exist.
        """
        user_man = managers.UserManager()
        super_users = user_man.get_admins()
        self.assertTrue(super_users, mock_find_u_with_role.return_value)

    def test_handle_missing_role(self, mock_find_u_with_role):
        """
        Test that if the role reqested does not exist, super_users is None.
        """
        user_man = managers.UserManager()
        mock_find_u_with_role.side_effect = exceptions.MissingResource()
        super_users = user_man.get_admins()
        self.assertTrue(super_users is None)


@mock.patch('pulp.server.db.migrations.lib.managers.get_collection')
class TestFindUsersBelongingToRole(unittest.TestCase):

    def test_missing_role(self, mock_col):
        """
        Ensure that if the role does not exist, MissingResource is raised.
        """
        mock_col.return_value.find_one.return_value = None
        user_man = managers.UserManager()
        self.assertRaises(exceptions.MissingResource, user_man.find_users_belonging_to_role, 'role')

    @mock.patch('pulp.server.db.migrations.lib.managers.UserManager.find_all')
    def test_as_expected(self, mock_find_all, mock_col):
        """
        Ensure that all users with the requested role are returned.
        """
        user_1 = {'roles': ['r1', 'r2']}
        user_2 = {'roles': ['r2', 'r3']}
        user_3 = {'roles': ['r3', 'r4']}
        mock_find_all.return_value = [user_1, user_2, user_3]
        user_man = managers.UserManager()
        users = user_man.find_users_belonging_to_role('r2')
        self.assertEqual(sorted([user_1, user_2]), sorted(users))


@mock.patch('pulp.server.db.migrations.lib.managers.get_collection')
class TestFindAll(unittest.TestCase):
    """
    Tests for retrieving all users.
    """

    def test_as_expected(self, mock_col):
        """
        Test the expected path of find_all.
        """
        user_1 = {'login': 'u1', 'password': 'hidden'}
        user_2 = {'login': 'u2', 'password': 'hidden'}
        mock_col.return_value.find.return_value = [user_1, user_2]
        user_man = managers.UserManager()
        all_users = user_man.find_all()

        self.assertEqual(len(all_users), 2)
        # Password should not be in the dict.
        self.assertDictEqual(all_users[0], {'login': 'u1'})
        self.assertDictEqual(all_users[1], {'login': 'u2'})


@mock.patch('pulp.server.db.migrations.lib.managers.get_collection')
class TestCreateUser(unittest.TestCase):
    """
    Tests the creation of a new user.
    """

    def test_dupe(self, mock_col):
        """
        Test the attemtped creation of a duplicate user.
        """
        mock_col.return_value.find_one.return_value = 'exists already'
        user_man = managers.UserManager()
        self.assertRaises(exceptions.DuplicateResource, user_man.create_user, 'test')

    @mock.patch('pulp.server.db.migrations.lib.managers.invalid_type')
    def test_invalid_values(self, mock_inv_type, mock_col):
        """
        Test that all invalid values are caught and raised.
        """
        mock_col.return_value.find_one.return_value = None
        mock_inv_type.return_value = True
        user_man = managers.UserManager()
        try:
            user_man.create_user(None)
        except exceptions.InvalidValue, e:
            pass
        else:
            raise AssertionError('Invalid value should be raised with invalid params.')

        self.assertEqual(sorted(e.property_names), sorted(['login', 'name', 'roles']))

    @mock.patch('pulp.server.db.migrations.lib.managers.factory')
    @mock.patch('pulp.server.db.migrations.lib.managers.model.User')
    @mock.patch('pulp.server.db.migrations.lib.managers.invalid_type')
    def test_as_expected(self, mock_inv_type, mock_user_model, mock_f, mock_col):
        """
        Test that user creation works as expected.
        """

        def find_user(*args):
            """Dirty trick to return None the first time, and a user the second time."""
            return args[0].pop()

        perm_man = mock_f.permission_manager.return_value
        created = {'created': 'user', 'password': 'should not be seen'}
        mock_col.return_value.find_one.side_effect = functools.partial(find_user, [created, None])
        mock_inv_type.return_value = False
        mock_user = mock_user_model.return_value
        mock_user.login = 'mlogin'
        user_man = managers.UserManager()
        user = user_man.create_user('mlogin', 'mpass', roles=['mock', 'roles'])

        mock_user.set_password.assert_called_once_with('mpass')
        mock_user.save.assert_called_once_with()
        perm_man.grant_automatic_permissions_for_user.assert_called_once_with('mlogin')
        self.assertDictEqual(user, {'created': 'user'})


class TestInvalidType(unittest.TestCase):
    """
    Tests for the helper function invalid_type.
    """

    def test_valid(self):
        """
        invalid_type for valid data should be False.
        """
        is_invalid = managers.invalid_type('test', str)
        self.assertTrue(is_invalid is False)

    def test_invalid(self):
        """
        invalid_type for invalid data should be True.
        """
        is_invalid = managers.invalid_type('test', int)
        self.assertTrue(is_invalid is True)
