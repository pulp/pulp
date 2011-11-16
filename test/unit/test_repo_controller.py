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

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")

import testutil
import mock_plugins

import pulp.server.content.loader as plugin_loader
from pulp.server.db.model.gc_repository import Repo, RepoImporter, RepoDistributor
import pulp.server.managers.factory as manager_factory

class RepoCollectionTest(testutil.PulpWebserviceTest):

    def setUp(self):
        testutil.PulpWebserviceTest.setUp(self)
        self.repo_manager = manager_factory.repo_manager()

    def clean(self):
        testutil.PulpWebserviceTest.clean(self)
        Repo.get_collection().remove()

    def test_get(self):
        """
        Tests retrieving a list of repositories.
        """

        # Setup
        self.repo_manager.create_repo('dummy-1')
        self.repo_manager.create_repo('dummy-2')

        # Test
        status, body = self.get('/v2/repositories/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(2, len(body))

    def test_get_no_repos(self):
        """
        Tests that an empty list is returned when no repos are present.
        """

        # Test
        status, body = self.get('/v2/repositories/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(0, len(body))

    def test_post(self):
        """
        Tests using post to create a repo.
        """

        # Setup
        body = {
            'id' : 'repo-1',
            'display_name' : 'Repo 1',
            'description' : 'Repository',
        }

        # Test
        status, body = self.post('/v2/repositories/', params=body)

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(body['id'], 'repo-1')

        repo = Repo.get_collection().find_one({'id' : 'repo-1'})
        self.assertTrue(repo is not None)

    def test_post_bad_data(self):
        """
        Tests a create repo with invalid data.
        """

        # Setup
        body = {'id' : 'HA! This is so totally invalid'}

        # Test
        status, body = self.post('/v2/repositories/', params=body)

        # Verify
        self.assertEqual(400, status)

    def test_post_conflict(self):
        """
        Tests creating a repo with an existing ID.
        """

        # Setup
        self.repo_manager.create_repo('existing')

        body = {'id' : 'existing'}

        # Test
        status, body = self.post('/v2/repositories/', params=body)

        # Verify
        self.assertEqual(409, status)

class RepoResourceTests(testutil.PulpWebserviceTest):

    def setUp(self):
        testutil.PulpWebserviceTest.setUp(self)
        self.repo_manager = manager_factory.repo_manager()

    def clean(self):
        testutil.PulpWebserviceTest.clean(self)
        Repo.get_collection().remove()

    def test_get(self):
        """
        Tests retrieving a valid repo.
        """

        # Setup
        self.repo_manager.create_repo('repo-1')

        # Test
        status, body = self.get('/v2/repositories/repo-1/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual('repo-1', body['id'])

    def test_get_missing_repo(self):
        """
        Tests that a 404 is returned when getting a repo that doesn't exist.
        """

        # Test
        status, body = self.get('/v2/repositories/foo/')

        # Verify
        self.assertEqual(404, status)

    def test_delete(self):
        """
        Tests deleting an existing repository.
        """

        # Setup
        self.repo_manager.create_repo('doomed')

        # Test
        status, body = self.delete('/v2/repositories/doomed/')

        # Verify
        self.assertEqual(200, status)

        repo = Repo.get_collection().find_one({'id' : 'doomed'})
        self.assertTrue(repo is None)

    def test_delete_missing_repo(self):
        """
        Tests deleting a repo that isn't there.
        """

        # Test
        status, body = self.delete('/v2/repositories/fake/')

        # Verify
        self.assertEqual(404, status)

    def test_put(self):
        """
        Tests using put to update a repo.
        """

        # Setup
        self.repo_manager.create_repo('turkey', display_name='hungry')

        req_body = {'delta' : {'display_name' : 'thanksgiving'}}

        # Test
        status, body = self.put('/v2/repositories/turkey/', params=req_body)

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(body['display_name'], req_body['delta']['display_name'])

        repo = Repo.get_collection().find_one({'id' : 'turkey'})
        self.assertEqual(repo['display_name'], req_body['delta']['display_name'])

    def test_put_invalid_body(self):
        """
        Tests updating a repo without passing the delta.
        """

        # Setup
        self.repo_manager.create_repo('pie')

        # Test
        status, body = self.put('/v2/repositories/pie/', params={})

        # Verify
        self.assertEqual(400, status)

    def test_put_missing_repo(self):
        """
        Tests updating a repo that doesn't exist.
        """

        # Test
        req_body = {'delta' : {'pie' : 'apple'}}
        status, body = self.put('/v2/repositories/not-there/', params=req_body)

        # Verify
        self.assertEqual(404, status)

class RepoImportersTest(testutil.PulpWebserviceTest):

    def setUp(self):
        testutil.PulpWebserviceTest.setUp(self)

        plugin_loader._create_loader()
        mock_plugins.install()

        self.repo_manager = manager_factory.repo_manager()
        self.importer_manager = manager_factory.repo_importer_manager()

    def tearDown(self):
        testutil.PulpWebserviceTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        testutil.PulpTest.clean(self)

        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()

    def test_get(self):
        """
        Tests getting the list of importers for a valid repo with importers.
        """

        # Setup
        self.repo_manager.create_repo('stuffing')
        self.importer_manager.set_importer('stuffing', 'mock-importer', {})

        # Test
        status, body = self.get('/v2/repositories/stuffing/importers/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(1, len(body))

    def test_get_no_importers(self):
        """
        Tests an empty list is returned for a repo with no importers.
        """

        # Setup
        self.repo_manager.create_repo('potatoes')

        # Test
        status, body = self.get('/v2/repositories/potatoes/importers/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(0, len(body))

    def test_post(self):
        """
        Tests adding an importer to a repo.
        """

        # Setup
        self.repo_manager.create_repo('gravy')

        req_body = {
            'importer_type_id' : 'mock-importer',
            'importer_config' : {'foo' : 'bar'},
        }

        # Test
        status, body = self.post('/v2/repositories/gravy/importers/', params=req_body)

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(body['importer_type_id'], req_body['importer_type_id'])
        self.assertEqual(body['repo_id'], 'gravy')
        self.assertEqual(body['config'], req_body['importer_config'])

        importer = RepoImporter.get_collection().find_one({'repo_id' : 'gravy'})
        self.assertTrue(importer is not None)
        self.assertEqual(importer['importer_type_id'], req_body['importer_type_id'])
        self.assertEqual(importer['config'], req_body['importer_config'])

    def test_post_missing_repo(self):
        """
        Tests adding an importer to a repo that doesn't exist.
        """

        # Test
        req_body = {
            'importer_type_id' : 'mock-importer',
            'importer_config' : {'foo' : 'bar'},
        }
        status, body = self.post('/v2/repositories/blah/importers/', params=req_body)

        # Verify
        self.assertEqual(404, status)

    def test_post_bad_request_missing_data(self):
        """
        Tests adding an importer but not specifying the required data.
        """

        # Setup
        self.repo_manager.create_repo('icecream')

        # Test
        status, body = self.post('/v2/repositories/icecream/importers/', params={})

        # Verify
        self.assertEqual(400, status)

    def test_post_bad_request_invalid_data(self):
        """
        Tests adding an importer but specifying incorrect metadata.
        """

        # Setup
        self.repo_manager.create_repo('walnuts')
        req_body = {
            'importer_type_id' : 'not-a-real-importer'
        }

        # Test
        status, body = self.post('/v2/repositories/walnuts/importers/', params=req_body)

        # Verify
        self.assertEqual(400, status)

class RepoImporterTest(testutil.PulpWebserviceTest):

    def setUp(self):
        testutil.PulpWebserviceTest.setUp(self)

        plugin_loader._create_loader()
        mock_plugins.install()

        self.repo_manager = manager_factory.repo_manager()
        self.importer_manager = manager_factory.repo_importer_manager()

    def tearDown(self):
        testutil.PulpWebserviceTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        testutil.PulpTest.clean(self)

        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()

    def test_get(self):
        """
        Tests getting an importer that exists.
        """

        # Setup
        self.repo_manager.create_repo('pie')
        self.importer_manager.set_importer('pie', 'mock-importer', {})

        # Test
        status, body = self.get('/v2/repositories/pie/importers/mock-importer/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(body['id'], 'mock-importer')

    def test_get_missing_repo(self):
        """
        Tests getting the importer for a repo that doesn't exist.
        """

        # Test
        status, body = self.get('/v2/repositories/not-there/importers/irrelevant')
        
        # Verify
        self.assertEqual(404, status)

    def test_get_missing_importer(self):
        """
        Tests getting the importer for a repo that doesn't have one.
        """

        # Setup
        self.repo_manager.create_repo('cherry_pie')

        # Test
        status, body = self.get('/v2/repositories/cherry_pie/importers/not_there/')
        
        # Verify
        self.assertEqual(404, status)

    def test_delete(self):
        """
        Tests removing an importer from a repo.
        """

        # Setup
        self.repo_manager.create_repo('blueberry_pie')
        self.importer_manager.set_importer('blueberry_pie', 'mock-importer', {})

        # Test
        status, body = self.delete('/v2/repositories/blueberry_pie/importers/mock-importer/')

        # Verify
        self.assertEqual(200, status)
        
        importer = RepoImporter.get_collection().find_one({'repo_id' : 'blueberry_pie'})
        self.assertTrue(importer is None)

    def test_delete_missing_repo(self):
        """
        Tests deleting the importer from a repo that doesn't exist.
        """

        # Test
        status, body = self.delete('/v2/repositories/bad_pie/importers/mock-importer/')

        # Verify
        self.assertEqual(404, status)

    def test_delete_missing_importer(self):
        """
        Tests deleting an importer from a repo that doesn't have one.
        """

        # Setup
        self.repo_manager.create_repo('apple_pie')

        # Test
        status, body = self.delete('/v2/repositories/apple_pie/importers/mock-importer/')

        # Verify
        self.assertEqual(404, status)

    def test_update_importer_config(self):
        """
        Tests successfully updating an importer's config.
        """

        # Setup
        self.repo_manager.create_repo('pumpkin_pie')
        self.importer_manager.set_importer('pumpkin_pie', 'mock-importer', {})

        # Test
        new_config = {'importer_config' : {'ice_cream' : True}}
        status, body = self.put('/v2/repositories/pumpkin_pie/importers/mock-importer/', params=new_config)

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(body['id'], 'mock-importer')

        importer = RepoImporter.get_collection().find_one({'repo_id' : 'pumpkin_pie'})
        self.assertTrue(importer is not None)

    def test_update_missing_repo(self):
        """
        Tests updating an importer config on a repo that doesn't exist.
        """

        # Test
        status, body = self.put('/v2/repositories/foo/importers/mock-importer/', params={'importer_config' : {}})

        # Verify
        self.assertEqual(404, status)

    def test_update_missing_importer(self):
        """
        Tests updating a repo that doesn't have an importer.
        """

        # Setup
        self.repo_manager.create_repo('pie')

        # Test
        status, body = self.put('/v2/repositories/pie/importers/mock-importer/', params={'importer_config' : {}})

        # Verify
        self.assertEqual(404, status)

    def test_update_bad_request(self):
        """
        Tests updating with incorrect parameters.
        """

        # Setup
        self.repo_manager.create_repo('pie')
        self.importer_manager.set_importer('pie', 'mock-importer', {})

        # Test
        status, body = self.put('/v2/repositories/pie/importers/mock-importer/', params={})

        # Verify
        self.assertEqual(400, status)

    