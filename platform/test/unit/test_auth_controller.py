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
        self.assertTrue(body[1]['_href'].find('users/dummy-') >= 0)

    def test_get_no_users(self):
        """
        Tests that an empty list is returned when no users are present.
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


#class RepoPluginsTests(RepoControllersTests):
#
#    def setUp(self):
#        super(RepoPluginsTests, self).setUp()
#
#        plugin_api._create_manager()
#        dummy_plugins.install()
#
#        self.importer_manager = manager_factory.repo_importer_manager()
#        self.distributor_manager = manager_factory.repo_distributor_manager()
#        self.sync_manager = manager_factory.repo_sync_manager()
#        self.publish_manager = manager_factory.repo_publish_manager()
#
#    def tearDown(self):
#        super(RepoPluginsTests, self).tearDown()
#        dummy_plugins.reset()
#
#    def clean(self):
#        super(RepoPluginsTests, self).clean()
#        RepoImporter.get_collection().remove(safe=True)
#        RepoDistributor.get_collection().remove(safe=True)
#        RepoSyncResult.get_collection().remove(safe=True)
#        RepoPublishResult.get_collection().remove(safe=True)
#
#
#class RepoImportersTests(RepoPluginsTests):
#
#    def test_get(self):
#        """
#        Tests getting the list of importers for a valid repo with importers.
#        """
#
#        # Setup
#        self.repo_manager.create_repo('stuffing')
#        self.importer_manager.set_importer('stuffing', 'dummy-importer', {})
#
#        # Test
#        status, body = self.get('/v2/repositories/stuffing/importers/')
#
#        # Verify
#        self.assertEqual(200, status)
#        self.assertEqual(1, len(body))
#
#    def test_get_no_importers(self):
#        """
#        Tests an empty list is returned for a repo with no importers.
#        """
#
#        # Setup
#        self.repo_manager.create_repo('potatoes')
#
#        # Test
#        status, body = self.get('/v2/repositories/potatoes/importers/')
#
#        # Verify
#        self.assertEqual(200, status)
#        self.assertEqual(0, len(body))
#
#    def test_get_missing_repo(self):
#        """
#        Tests getting importers for a repo that doesn't exist.
#        """
#
#        # Test
#        status, body = self.get('/v2/repositories/not_there/importers/')
#
#        # Verify
#        self.assertEqual(404, status)
#
#    def test_post(self):
#        """
#        Tests adding an importer to a repo.
#        """
#
#        # Setup
#        self.repo_manager.create_repo('gravy')
#
#        req_body = {
#            'importer_type_id' : 'dummy-importer',
#            'importer_config' : {'foo' : 'bar'},
#        }
#
#        # Test
#        status, body = self.post('/v2/repositories/gravy/importers/', params=req_body)
#
#        # Verify
#        self.assertEqual(201, status)
#        self.assertEqual(body['importer_type_id'], req_body['importer_type_id'])
#        self.assertEqual(body['repo_id'], 'gravy')
#        self.assertEqual(body['config'], req_body['importer_config'])
#
#        importer = RepoImporter.get_collection().find_one({'repo_id' : 'gravy'})
#        self.assertTrue(importer is not None)
#        self.assertEqual(importer['importer_type_id'], req_body['importer_type_id'])
#        self.assertEqual(importer['config'], req_body['importer_config'])
#
#    def test_post_missing_repo(self):
#        """
#        Tests adding an importer to a repo that doesn't exist.
#        """
#
#        # Test
#        req_body = {
#            'importer_type_id' : 'dummy-importer',
#            'importer_config' : {'foo' : 'bar'},
#        }
#        status, body = self.post('/v2/repositories/blah/importers/', params=req_body)
#
#        # Verify
#        self.assertEqual(404, status)
#
#    def test_post_bad_request_missing_data(self):
#        """
#        Tests adding an importer but not specifying the required data.
#        """
#
#        # Setup
#        self.repo_manager.create_repo('icecream')
#
#        # Test
#        status, body = self.post('/v2/repositories/icecream/importers/', params={})
#
#        # Verify
#        self.assertEqual(400, status)
#
#    def test_post_bad_request_invalid_data(self):
#        """
#        Tests adding an importer but specifying incorrect metadata.
#        """
#
#        # Setup
#        self.repo_manager.create_repo('walnuts')
#        req_body = {
#            'importer_type_id' : 'not-a-real-importer'
#        }
#
#        # Test
#        status, body = self.post('/v2/repositories/walnuts/importers/', params=req_body)
#
#        # Verify
#        self.assertEqual(400, status)
#
#class RepoImporterTests(RepoPluginsTests):
#
#    def test_get(self):
#        """
#        Tests getting an importer that exists.
#        """
#
#        # Setup
#        self.repo_manager.create_repo('pie')
#        self.importer_manager.set_importer('pie', 'dummy-importer', {})
#
#        # Test
#        status, body = self.get('/v2/repositories/pie/importers/dummy-importer/')
#
#        # Verify
#        self.assertEqual(200, status)
#        self.assertEqual(body['id'], 'dummy-importer')
#
#    def test_get_missing_repo(self):
#        """
#        Tests getting the importer for a repo that doesn't exist.
#        """
#
#        # Test
#        status, body = self.get('/v2/repositories/not-there/importers/irrelevant')
#
#        # Verify
#        self.assertEqual(404, status)
#
#    def test_get_missing_importer(self):
#        """
#        Tests getting the importer for a repo that doesn't have one.
#        """
#
#        # Setup
#        self.repo_manager.create_repo('cherry_pie')
#
#        # Test
#        status, body = self.get('/v2/repositories/cherry_pie/importers/not_there/')
#
#        # Verify
#        self.assertEqual(404, status)
#
#    def test_delete(self):
#        """
#        Tests removing an importer from a repo.
#        """
#
#        # Setup
#        self.repo_manager.create_repo('blueberry_pie')
#        self.importer_manager.set_importer('blueberry_pie', 'dummy-importer', {})
#
#        # Test
#        status, body = self.delete('/v2/repositories/blueberry_pie/importers/dummy-importer/')
#
#        # Verify
#        self.assertEqual(200, status)
#
#        importer = RepoImporter.get_collection().find_one({'repo_id' : 'blueberry_pie'})
#        self.assertTrue(importer is None)
#
#    def test_delete_missing_repo(self):
#        """
#        Tests deleting the importer from a repo that doesn't exist.
#        """
#
#        # Test
#        status, body = self.delete('/v2/repositories/bad_pie/importers/dummy-importer/')
#
#        # Verify
#        self.assertEqual(404, status)
#
#    def test_delete_missing_importer(self):
#        """
#        Tests deleting an importer from a repo that doesn't have one.
#        """
#
#        # Setup
#        self.repo_manager.create_repo('apple_pie')
#
#        # Test
#        status, body = self.delete('/v2/repositories/apple_pie/importers/dummy-importer/')
#
#        # Verify
#        self.assertEqual(404, status)
#
#    def test_update_importer_config(self):
#        """
#        Tests successfully updating an importer's config.
#        """
#
#        # Setup
#        self.repo_manager.create_repo('pumpkin_pie')
#        self.importer_manager.set_importer('pumpkin_pie', 'dummy-importer', {})
#
#        # Test
#        new_config = {'importer_config' : {'ice_cream' : True}}
#        status, body = self.put('/v2/repositories/pumpkin_pie/importers/dummy-importer/', params=new_config)
#
#        # Verify
#        self.assertEqual(200, status)
#        self.assertEqual(body['id'], 'dummy-importer')
#
#        importer = RepoImporter.get_collection().find_one({'repo_id' : 'pumpkin_pie'})
#        self.assertTrue(importer is not None)
#
#    def test_update_missing_repo(self):
#        """
#        Tests updating an importer config on a repo that doesn't exist.
#        """
#
#        # Test
#        status, body = self.put('/v2/repositories/foo/importers/dummy-importer/', params={'importer_config' : {}})
#
#        # Verify
#        self.assertEqual(404, status)
#
#    def test_update_missing_importer(self):
#        """
#        Tests updating a repo that doesn't have an importer.
#        """
#
#        # Setup
#        self.repo_manager.create_repo('pie')
#
#        # Test
#        status, body = self.put('/v2/repositories/pie/importers/dummy-importer/', params={'importer_config' : {}})
#
#        # Verify
#        self.assertEqual(404, status)
#
#    def test_update_bad_request(self):
#        """
#        Tests updating with incorrect parameters.
#        """
#
#        # Setup
#        self.repo_manager.create_repo('pie')
#        self.importer_manager.set_importer('pie', 'dummy-importer', {})
#
#        # Test
#        status, body = self.put('/v2/repositories/pie/importers/dummy-importer/', params={})
#
#        # Verify
#        self.assertEqual(400, status)

