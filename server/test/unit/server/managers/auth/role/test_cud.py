import random
import string
import mock

from ..... import base
from pulp.server.auth import authorization
from pulp.server.db import model
from pulp.server.db.model.auth import Role
from pulp.server.controllers import user as user_controller
from pulp.server.exceptions import PulpDataException, InvalidValue, MissingResource
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.auth.role import cud


class RoleManagerTests(base.PulpServerTests):
    def setUp(self):
        super(RoleManagerTests, self).setUp()

        self.alpha_num = string.letters + string.digits

        self.role_manager = manager_factory.role_manager()
        self.role_query_manager = manager_factory.role_query_manager()
        self.permission_manager = manager_factory.permission_manager()
        self.permission_query_manager = manager_factory.permission_query_manager()

        self.role_manager.ensure_super_user_role()
        manager_factory.principal_manager().clear_principal()

    def tearDown(self):
        super(RoleManagerTests, self).tearDown()

    def clean(self):
        base.PulpServerTests.clean(self)
        Role.get_collection().remove()

    # test data generation
    def _create_user(self):
        username = ''.join(random.sample(self.alpha_num, random.randint(6, 10)))
        password = ''.join(random.sample(self.alpha_num, random.randint(6, 10)))
        return user_controller.create_user(login=username, password=password, name=username)

    def _create_role(self):
        role_id = ''.join(random.sample(self.alpha_num, random.randint(6, 10)))
        return self.role_manager.create_role(role_id)

    def _create_resource(self):
        return '/%s/' % '/'.join(''.join(random.sample(self.alpha_num,
                                                       random.randint(6, 10)))
                                 for i in range(random.randint(2, 4)))

    # test role management
    def test_create_role(self):
        n = 'create_role'
        r1 = self.role_manager.create_role(n)
        r2 = self.role_query_manager.find_by_id(n)
        self.assertEquals(r1['_id'], r2['_id'])

    def test_delete_role(self):
        n = 'delete_role'
        r1 = self.role_manager.create_role(n)
        self.assertFalse(r1 is None)
        self.role_manager.delete_role(n)
        r2 = self.role_query_manager.find_by_id(n)
        self.assertTrue(r2 is None)

    def test_update_role(self):
        role_id = 'update_role'
        self.role_manager.create_role(role_id)
        delta = {'display_name': 'display_name',
                 'description': 'description'}
        returned_role = self.role_manager.update_role(role_id, delta)
        self.assertEqual(returned_role.get('display_name'), delta['display_name'])
        self.assertEqual(returned_role.get('description'), delta['description'])
        updated_role = self.role_query_manager.find_by_id(role_id)
        self.assertEqual(updated_role.get('display_name'), delta['display_name'])
        self.assertEqual(updated_role.get('description'), delta['description'])

    def test_update_role_unsupported(self):
        role_id = 'update_role'
        self.role_manager.create_role(role_id)
        delta = {'display_name': 'display_name',
                 'permissions': {"/": ["CREATE", "DELETE"]}}
        self.assertRaises(PulpDataException, self.role_manager.update_role, role_id, delta)
        role = self.role_query_manager.find_by_id(role_id)
        self.assertNotEqual(role.get('display_name'), delta['display_name'])
        self.assertNotEqual(role.get('permissions'), delta['permissions'])

    def test_add_user(self):
        user = self._create_user()
        r = self._create_role()
        self.role_manager.add_user_to_role(r['id'], user.login)
        user_names = [u.login for u in user_controller.find_users_belonging_to_role(r['id'])]
        self.assertTrue(user.login in user_names)

    def test_add_user_no_role(self):
        """
        Test that a MissingResource exception is raised when the given role doesn't exist.
        """
        user = self._create_user()
        self.assertRaises(MissingResource, self.role_manager.add_user_to_role, 'not_a_role',
                          user.login)

    def test_add_user_no_user(self):
        """
        Test that a InvalidValue exception is raised when the given user doesn't exist.
        """
        role = self._create_role()
        self.assertRaises(InvalidValue, self.role_manager.add_user_to_role, role['id'],
                          'not_a_user')

    def test_remove_user(self):
        user = self._create_user()
        r = self._create_role()
        self.role_manager.add_user_to_role(r['id'], user.login)
        self.role_manager.remove_user_from_role(r['id'], user.login)
        user_names = [u.login for u in user_controller.find_users_belonging_to_role(r['id'])]
        self.assertFalse(user.login in user_names)

    # test built in roles
    def test_super_users(self):
        role = self.role_query_manager.find_by_id(cud.SUPER_USER_ROLE)
        self.assertFalse(role is None)

    def test_super_users_grant(self):
        s = self._create_resource()
        o = authorization.READ
        self.assertRaises(PulpDataException,
                          self.role_manager.add_permissions_to_role,
                          cud.SUPER_USER_ROLE, s, [o])

    def test_super_users_revoke(self):
        s = self._create_resource()
        o = authorization.READ
        self.assertRaises(PulpDataException,
                          self.role_manager.remove_permissions_from_role,
                          cud.SUPER_USER_ROLE, s, [o])

    def test_super_user_permissions(self):
        u = self._create_user()
        s = self._create_resource()
        r = cud.SUPER_USER_ROLE
        self.role_manager.add_user_to_role(r, u.login)
        self.assertTrue(user_controller.is_authorized(s, u.login, authorization.CREATE))
        self.assertTrue(user_controller.is_authorized(s, u.login, authorization.READ))
        self.assertTrue(user_controller.is_authorized(s, u.login, authorization.UPDATE))
        self.assertTrue(user_controller.is_authorized(s, u.login, authorization.DELETE))
        self.assertTrue(user_controller.is_authorized(s, u.login, authorization.EXECUTE))

    # test multi-role/permission interaction

    def test_non_unique_permission_revoke(self):
        u = self._create_user()
        r1 = self._create_role()
        r2 = self._create_role()
        s = self._create_resource()
        o = authorization.READ
        self.role_manager.add_user_to_role(r1['id'], u.login)
        self.role_manager.add_user_to_role(r2['id'], u.login)
        self.role_manager.add_permissions_to_role(r1['id'], s, [o])
        self.role_manager.add_permissions_to_role(r2['id'], s, [o])
        self.assertTrue(user_controller.is_authorized(s, u.login, o))
        self.role_manager.remove_permissions_from_role(r1['id'], s, [o])
        u = model.User.objects(login=u.login).first()
        self.assertTrue(user_controller.is_authorized(s, u.login, o))

    def test_non_unique_permission_remove(self):
        u = self._create_user()
        r1 = self._create_role()
        r2 = self._create_role()
        s = self._create_resource()
        o = authorization.READ
        self.role_manager.add_user_to_role(r1['id'], u.login)
        self.role_manager.add_user_to_role(r2['id'], u.login)
        self.role_manager.add_permissions_to_role(r1['id'], s, [o])
        self.role_manager.add_permissions_to_role(r2['id'], s, [o])
        self.assertTrue(user_controller.is_authorized(s, u.login, o))
        self.role_manager.remove_user_from_role(r1['id'], u.login)
        self.assertTrue(user_controller.is_authorized(s, u.login, o))

    def test_non_unique_permission_delete(self):
        u = self._create_user()
        r1 = self._create_role()
        r2 = self._create_role()
        s = self._create_resource()
        o = authorization.READ
        self.role_manager.add_user_to_role(r1['id'], u.login)
        self.role_manager.add_user_to_role(r2['id'], u.login)
        self.role_manager.add_permissions_to_role(r1['id'], s, [o])
        self.role_manager.add_permissions_to_role(r2['id'], s, [o])
        self.assertTrue(user_controller.is_authorized(s, u.login, o))
        self.role_manager.delete_role(r1['id'])
        self.assertTrue(user_controller.is_authorized(s, u.login, o))

    @mock.patch('pulp.server.managers.auth.role.cud.RoleManager.create_role')
    @mock.patch('pulp.server.managers.auth.role.cud.RoleManager.get_role')
    @mock.patch('pulp.server.db.model.auth.Role.get_collection')
    def test_ensure_super_user_role(self, mock_role, mock_get_role, mock_create_role):
        self.clean()
        mock_get_role.return_value = None
        mock_create_role.return_value = {
            'display_name': 'Super Users',
            'description': 'Role indicates users hols admin privileges',
            '_ns': 'roles', 'id': 'super-users', 'permissions': {}
        }

        rm_instance = cud.RoleManager()
        rm_instance.ensure_super_user_role()

        self.assertEqual(mock_create_role.return_value['permissions'],
                         [{'resource': '/', 'permission': [0, 1, 2, 3, 4]}])
        mock_role.save.assert_called_once()

    def test_get_role(self):
        # Setup
        self.role_manager.create_role(role_id='best-user')

        # Test
        role = self.role_manager.get_role('best-user')
        self.assertEquals(role['display_name'], 'best-user')

    def test_get_role_bad_role(self):
        # Test
        self.assertEquals(self.role_manager.get_role('potato'), None)

    def test_non_existing_role_permission_revoke(self):
        role_id = 'non-existing-role'
        r = self._create_resource()
        o = authorization.READ
        try:
            self.role_manager.remove_permissions_from_role(role_id, r, [o])
        except InvalidValue, e:
            self.assertTrue('role_id' in str(e))
        else:
            self.fail('Non-existing role_id revoke did not raise an exception')

    def test_non_existing_role_permission_grant(self):
        role_id = 'non-existing-role'
        r = self._create_resource()
        o = authorization.READ
        try:
            self.role_manager.add_permissions_to_role(role_id, r, [o])
        except InvalidValue, e:
            self.assertTrue('role_id' in str(e))
        else:
            self.fail('Non-existing role_id grant did not raise an exception')
