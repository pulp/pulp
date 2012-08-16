#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Python

import base
import dummy_plugins

from pulp.server.db.model.auth import (User, Role, Permission)
from pulp.server.managers import factory as manager_factory


class AuthControllersTests(base.PulpWebserviceTests):

    def setUp(self):
        super(AuthControllersTests, self).setUp()
        self.user_manager = manager_factory.user_manager()
        self.user_query_manager = manager_factory.user_query_manager()
        self.role_manager = manager_factory.role_manager()
        self.role_query_manager = manager_factory.role_query_manager()
        self.permission_manager = manager_factory.permission_manager()
        self.permission_query_manager = manager_factory.permission_query_manager()
        self.password_manager = manager_factory.password_manager()

        self.role_manager.ensure_super_user_role()
        self.user_manager.ensure_admin()

    def clean(self):
        super(AuthControllersTests, self).clean()
        User.get_collection().remove(safe=True)
        Role.get_collection().remove(safe=True)
        Permission.get_collection().remove(safe=True)
        

class UserCollectionTests(AuthControllersTests):

    def test_get(self):
        """
        Tests retrieving a list of users.
        """

        # Setup
        self.user_manager.create_user(login='dummy-1', password='dummy-1')
        self.user_manager.create_user(login='dummy-2', password='dummy-2')

        # Test
        status, body = self.get('/v2/users/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(3, len(body))
        self.assertTrue('password' not in body[0])
        self.assertTrue('_href' in body[0])


    def test_get_no_users(self):
        """
        Tests that a list with admin user is returned when no users are present.
        """

        # Test
        status, body = self.get('/v2/users/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(1, len(body))


    def test_post(self):
        """
        Tests using post to create a user.
        """

        # Setup
        params = {
            'login' : 'user-1',
            'name' : 'User 1',
            'password' : 'test-password',
            'roles': [self.role_manager.super_user_role],
        }

        # Test
        status, body = self.post('/v2/users/', params=params)

        # Verify
        self.assertEqual(201, status)

        self.assertEqual(body['login'], 'user-1')

        user = User.get_collection().find_one({'login' : 'user-1'})
        self.assertTrue(user is not None)
        self.assertEqual(params['name'], user['name'])
        self.assertEqual(params['roles'], user['roles'])
        self.assertTrue(self.password_manager.check_password(user['password'], params['password']))

    def test_post_bad_data(self):
        """
        Tests a create user with invalid data.
        """

        # Setup
        body = {'login' : 'HA! This looks so totally invalid :)'}

        # Test
        status, body = self.post('/v2/users/', params=body)

        # Verify
        self.assertEqual(400, status)

    def test_post_conflict(self):
        """
        Tests creating a user with an existing login.
        """

        # Setup
        self.user_manager.create_user('existing')

        body = {'login' : 'existing'}

        # Test
        status, body = self.post('/v2/users/', params=body)

        # Verify
        self.assertEqual(409, status)

class UserResourceTests(AuthControllersTests):

    def test_get(self):
        """
        Tests retrieving a valid user.
        """

        # Setup
        self.user_manager.create_user('user-1')

        # Test
        status, body = self.get('/v2/users/user-1/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual('user-1', body['login'])
        self.assertTrue('_href' in body)
        self.assertTrue(body['_href'].endswith('users/user-1/'))


    def test_get_missing_user(self):
        """
        Tests that a 404 is returned when getting a user that doesn't exist.
        """

        # Test
        status, body = self.get('/v2/users/foo/')

        # Verify
        self.assertEqual(404, status)

    def test_delete(self):
        """
        Tests deleting an existing user.
        """

        # Setup
        self.user_manager.create_user('doomed')

        # Test
        status, body = self.delete('/v2/users/doomed/')

        # Verify
        self.assertEqual(200, status)

        user = User.get_collection().find_one({'login' : 'doomed'})
        self.assertTrue(user is None)

    def test_delete_missing_user(self):
        """
        Tests deleting a user that isn't there.
        """

        # Test
        status, body = self.delete('/v2/users/fake/')

        # Verify
        self.assertEqual(404, status)

    def test_put(self):
        """
        Tests using put to update a user.
        """

        # Setup
        self.user_manager.create_user('user-1', name='original name')

        req_body = {'delta' : {'name' : 'new name', 'password': 'new password'}}

        # Test
        status, body = self.put('/v2/users/user-1/', params=req_body)

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(body['name'], req_body['delta']['name'])
        
        user = User.get_collection().find_one({'login' : 'user-1'})
        self.assertEqual(user['name'], req_body['delta']['name'])
        
        self.assertTrue(self.password_manager.check_password(user['password'], req_body['delta']['password']))

    def test_put_missing_user(self):
        """
        Tests updating a user that doesn't exist.
        """

        # Test
        req_body = {'delta' : {'pie' : 'apple'}}
        status, body = self.put('/v2/users/not-there/', params=req_body)

        # Verify
        self.assertEqual(404, status)


class RoleCollectionTests(AuthControllersTests):

    def test_get(self):
        """
        Tests retrieving a list of roles.
        """

        # Setup
        self.role_manager.create_role(role_id='dummy-1')
        self.role_manager.create_role(role_id='dummy-2')

        # Test
        status, body = self.get('/v2/roles/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(3, len(body))
        self.assertTrue('_href' in body[0])


    def test_get_no_roles(self):
        """
        Tests that an super-user-role is returned when no other roles are present.
        """

        # Test
        status, body = self.get('/v2/roles/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(1, len(body))


    def test_post(self):
        """
        Tests using post to create a role.
        """

        # Setup
        params = {
            'role_id' : 'role-1',
            'display_name' : 'Role 1',
            'description' : 'Role 1 description',
        }

        # Test
        status, body = self.post('/v2/roles/', params=params)

        # Verify
        self.assertEqual(201, status)

        self.assertEqual(body['id'], 'role-1')

        role = Role.get_collection().find_one({'id' : 'role-1'})
        self.assertTrue(role is not None)
        self.assertEqual(params['display_name'], role['display_name'])
        self.assertEqual(params['description'], role['description'])


    def test_post_bad_data(self):
        """
        Tests a create role with invalid data.
        """

        # Setup
        body = {'role_id' : 'HA! This looks so totally invalid :)'}

        # Test
        status, body = self.post('/v2/roles/', params=body)

        # Verify
        self.assertEqual(400, status)


    def test_post_conflict(self):
        """
        Tests creating a role with an existing id.
        """

        # Setup
        self.role_manager.create_role('existing')

        body = {'role_id' : 'existing'}

        # Test
        status, body = self.post('/v2/roles/', params=body)

        # Verify
        self.assertEqual(409, status)

class RoleResourceTests(AuthControllersTests):

    def test_get(self):
        """
        Tests retrieving a valid role.
        """

        # Setup
        self.role_manager.create_role('role-1')

        # Test
        status, body = self.get('/v2/roles/role-1/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual('role-1', body['id'])
        self.assertTrue('_href' in body)
        self.assertTrue(body['_href'].endswith('roles/role-1/'))


    def test_get_missing_role(self):
        """
        Tests that a 404 is returned when getting a role that doesn't exist.
        """

        # Test
        status, body = self.get('/v2/roles/foo/')

        # Verify
        self.assertEqual(404, status)

    def test_delete(self):
        """
        Tests deleting an existing role.
        """

        # Setup
        self.role_manager.create_role('doomed')

        # Test
        status, body = self.delete('/v2/roles/doomed/')

        # Verify
        self.assertEqual(200, status)

        role = Role.get_collection().find_one({'id' : 'doomed'})
        self.assertTrue(role is None)

    def test_delete_missing_role(self):
        """
        Tests deleting a role that isn't there.
        """

        # Test
        status, body = self.delete('/v2/roles/fake/')

        # Verify
        self.assertEqual(404, status)

    def test_put(self):
        """
        Tests using put to update a role.
        """

        # Setup
        self.role_manager.create_role('role-1', display_name='original name')

        req_body = {'delta' : {'display_name' : 'new name', 'description': 'new description'}}

        # Test
        status, body = self.put('/v2/roles/role-1/', params=req_body)

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(body['display_name'], req_body['delta']['display_name'])
        
        role = Role.get_collection().find_one({'id' : 'role-1'})
        self.assertEqual(role['display_name'], req_body['delta']['display_name'])
        self.assertEqual(role['description'], req_body['delta']['description'])
        

    def test_put_missing_role(self):
        """
        Tests updating a role that doesn't exist.
        """

        # Test
        req_body = {'delta' : {'pie' : 'apple'}}
        status, body = self.put('/v2/roles/not-there/', params=req_body)

        # Verify
        self.assertEqual(404, status)
        

class RoleUsersTests(AuthControllersTests):
   
    def test_get(self):
        """
        Tests getting the list of users belonging to a valid role.
        """

        # Setup
        self.role_manager.create_role(role_id = 'role-1')
        self.user_manager.create_user(login = 'user-1', roles = ['role-1'])

        # Test
        status, body = self.get('/v2/roles/role-1/users/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(1, len(body))
        

    def test_get_no_users(self):
        """
        Tests an empty list is returned for a role with no users.
        """

        # Setup
        self.role_manager.create_role(role_id = 'role-1')

        # Test
        status, body = self.get('/v2/roles/role-1/users/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(0, len(body))

    def test_get_missing_role(self):
        """
        Tests getting users for a role that doesn't exist.
        """

        # Test
        status, body = self.get('/v2/roles/not_there/users/')

        # Verify
        self.assertEqual(404, status)

    def test_post(self):
        """
        Tests adding a user to a role.
        """

        # Setup
        self.user_manager.create_user(login = 'user-1')
        self.role_manager.create_role(role_id = 'role-1')

        req_body = {
            'login' : 'user-1',
        }

        # Test
        status, body = self.post('/v2/roles/role-1/users/', params=req_body)

        # Verify
        self.assertEqual(201, status)

        user = User.get_collection().find_one({'login' : 'user-1'})
        self.assertTrue(user is not None)
        self.assertEqual(user['roles'], ['role-1'])


    def test_post_missing_role(self):
        """
        Tests adding an user to a role that doesn't exist.
        """

        # Test
        req_body = {
            'login' : 'dummy-user',
        }

        status, body = self.post('/v2/roles/blah/users/', params=req_body)

        # Verify
        self.assertEqual(404, status)

    def test_post_bad_request_missing_data(self):
        """
        Tests adding a user but not specifying the required data.
        """

        # Setup
        self.role_manager.create_role(role_id = 'role-1')

        # Test
        status, body = self.post('/v2/roles/role-1/users/', params={})

        # Verify
        self.assertEqual(400, status)

    def test_post_bad_request_invalid_data(self):
        """
        Tests adding a user but specifying non-existing user.
        """

        # Setup
        self.role_manager.create_role(role_id = 'role-1')

        req_body = {
            'login' : 'missing-user'
        }

        # Test
        status, body = self.post('/v2/roles/role-1/users/', params=req_body)

        # Verify
        self.assertEqual(404, status)
        
class RoleUserTests(AuthControllersTests):


    def test_delete(self):
        """
        Tests removing a user from a role.
        """

        # Setup
        self.role_manager.create_role(role_id = 'role-1')
        self.user_manager.create_user(login = 'user-1', roles = ['role-1'])


        # Test
        status, body = self.delete('/v2/roles/role-1/users/user-1/')

        # Verify
        self.assertEqual(200, status)

        user = User.get_collection().find_one({'login' : 'user-1'})
        self.assertFalse('role-1' in user['roles'])

    def test_delete_missing_role(self):
        """
        Tests deleting a user from a role that doesn't exist.
        """

        # Test
        status, body = self.delete('/v2/roles/dummy/users/dummy/')

        # Verify
        self.assertEqual(404, status)

    def test_delete_missing_user(self):
        """
        Tests deleting a user from a role that doesn't have one.
        """

        # Setup
        self.role_manager.create_role(role_id = 'role-1')

        # Test
        status, body = self.delete('/v2/roles/role-1/users/dummy/')

        # Verify
        self.assertEqual(404, status)


