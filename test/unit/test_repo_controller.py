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
import datetime
import mock
import os
import sys
from pprint import pformat

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")

import testutil
import mock_plugins

from pulp.common import dateutils
import pulp.server.content.loader as plugin_loader
from pulp.server.db.model.gc_repository import Repo, RepoImporter, RepoDistributor, RepoSyncResult, RepoPublishResult
from pulp.server.dispatch import constants as dispatch_constants
import pulp.server.managers.factory as manager_factory
from pulp.server.managers.repo.unit_association_query import Criteria

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
        self.assertEqual(201, status)

        self.assertEqual(body['id'], 'repo-1')

        repo = Repo.get_collection().find_one({'id' : 'repo-1'})
        self.assertTrue(repo is not None)

    def test_post_bad_data(self):
        """
        Tests a create repo with invalid data.
        """

        # Setup
        body = {'id' : 'HA! This looks so totally invalid, but we do allow this ID now :)'}

        # Test
        status, body = self.post('/v2/repositories/', params=body)

        # Verify
        self.assertEqual(201, status)
        self.assertEqual(body['id'], 'HA! This looks so totally invalid, but we do allow this ID now :)')

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

class RepoResourceTests(testutil.PulpV2WebServicesTest):

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
        self.assertEqual(202, status)

        while body['state'] not in dispatch_constants.CALL_COMPLETE_STATES:
            href = body['_href'][9:]
            status, body = self.get(href)
            if status != 200:
                self.fail('%s\n%d\n%s' % (href, status, pformat(body)))

        repo = Repo.get_collection().find_one({'id' : 'doomed'})
        self.assertTrue(repo is None)

    def test_delete_missing_repo(self):
        """
        Tests deleting a repo that isn't there.
        """

        # Test
        status, body = self.delete('/v2/repositories/fake/')

        # Verify
        self.assertEqual(202, status)

        while body['state'] not in dispatch_constants.CALL_COMPLETE_STATES:
            href = body['_href'][9:]
            status, body = self.get(href)
            if status != 200:
                self.fail('%s\n%d\n%s' % (href, status, pformat(body)))

        self.assertTrue(body['state'] == dispatch_constants.CALL_ERROR_STATE)

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

    def test_get_missing_repo(self):
        """
        Tests getting importers for a repo that doesn't exist.
        """

        # Test
        status, body = self.get('/v2/repositories/not_there/importers/')

        # Verify
        self.assertEqual(404, status)

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
        self.assertEqual(201, status)
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

class RepoDistributorsTest(testutil.PulpWebserviceTest):

    def setUp(self):
        testutil.PulpWebserviceTest.setUp(self)

        plugin_loader._create_loader()
        mock_plugins.install()

        self.repo_manager = manager_factory.repo_manager()
        self.distributor_manager = manager_factory.repo_distributor_manager()

    def tearDown(self):
        testutil.PulpWebserviceTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        testutil.PulpTest.clean(self)

        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()

    def test_get_distributors(self):
        """
        Tests retrieving all distributors for a repo.
        """

        # Setup
        self.repo_manager.create_repo('coffee')
        self.distributor_manager.add_distributor('coffee', 'mock-distributor', {}, True, distributor_id='dist-1')
        self.distributor_manager.add_distributor('coffee', 'mock-distributor', {}, True, distributor_id='dist-2')

        # Test
        status, body = self.get('/v2/repositories/coffee/distributors/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(2, len(body))

    def test_get_distributors_no_distributors(self):
        """
        Tests retrieving distributors for a repo that has none.
        """

        # Setup
        self.repo_manager.create_repo('dark-roast')

        # Test
        status, body = self.get('/v2/repositories/dark-roast/distributors/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(0, len(body))

    def test_get_distributors_missing_repo(self):
        """
        Tests retrieving distributors for a repo that doesn't exist.
        """

        # Test
        status, body = self.get('/v2/repositories/not-there/distributors/')

        # Verify
        self.assertEqual(404, status)

    def test_create_distributor(self):
        """
        Tests creating a distributor on a repo.
        """

        # Setup
        self.repo_manager.create_repo('tea')

        req_body = {
            'distributor_type_id' : 'mock-distributor',
            'distributor_config' : {'a' : 'b'},
        }

        # Test
        status, body = self.post('/v2/repositories/tea/distributors/', params=req_body)

        # Verify
        self.assertEqual(201, status)
        self.assertEqual(body['repo_id'], 'tea')
        self.assertEqual(body['config'], req_body['distributor_config'])
        self.assertEqual(body['auto_publish'], False)
        self.assertTrue('id' in body)

    def test_create_distributor_missing_repo(self):
        """
        Tests creating a distributor on a repo that doesn't exist.
        """

        # Test
        req_body = {
            'distributor_type_id' : 'mock-distributor',
            'distributor_config' : {'a' : 'b'},
        }
        status, body = self.post('/v2/repositories/not_there/distributors/', params=req_body)

        # Verify
        self.assertEqual(404, status)

    def test_create_distributor_invalid_data(self):
        """
        Tests creating a distributor but not passing in all the required data.
        """

        # Setup
        self.repo_manager.create_repo('invalid')

        # Test
        status, body = self.post('/v2/repositories/invalid/distributors/', params={})

        # Verify
        self.assertEqual(400, status)

class RepoDistributorTest(testutil.PulpWebserviceTest):

    def setUp(self):
        testutil.PulpWebserviceTest.setUp(self)

        plugin_loader._create_loader()
        mock_plugins.install()

        self.repo_manager = manager_factory.repo_manager()
        self.distributor_manager = manager_factory.repo_distributor_manager()

    def tearDown(self):
        testutil.PulpWebserviceTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        testutil.PulpTest.clean(self)

        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()

    def test_get(self):
        """
        Tests getting a single repo distributor.
        """

        # Setup
        self.repo_manager.create_repo('repo')
        self.distributor_manager.add_distributor('repo', 'mock-distributor', {}, True, 'dist-1')

        # Test
        status, body = self.get('/v2/repositories/repo/distributors/dist-1/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(body['id'], 'dist-1')

    def test_get_missing_distributor(self):
        """
        Tests getting a distributor that doesn't exist.
        """

        # Setup
        self.repo_manager.create_repo('repo-1')

        # Test
        status, body = self.get('/v2/repositories/repo-1/distributors/foo/')

        # Verify
        self.assertEqual(404, status)

    def test_delete(self):
        """
        Tests unassociating a distributor from a repo.
        """

        # Setup
        self.repo_manager.create_repo('repo-1')
        self.distributor_manager.add_distributor('repo-1', 'mock-distributor', {}, True, 'dist-1')

        # Test
        status, body = self.delete('/v2/repositories/repo-1/distributors/dist-1/')

        # Verify
        self.assertEqual(200, status)

        dist = RepoDistributor.get_collection().find_one({'repo_id' : 'repo-1'})
        self.assertTrue(dist is None)

    def test_delete_missing_distributor(self):
        """
        Tests deleting a distributor that isn't there.
        """

        # Setup
        self.repo_manager.create_repo('repo-1')

        # Test
        status, body = self.delete('/v2/repositories/repo-1/distributors/foo/')

        # Verify
        self.assertEqual(404, status)

    def test_update(self):
        """
        Tests updating a distributor's configuration.
        """

        # Setup
        self.repo_manager.create_repo('repo-1')
        self.distributor_manager.add_distributor('repo-1', 'mock-distributor', {'key' : 'orig'}, True, 'dist-1')

        # Test
        req_body = {'distributor_config' : {'key' : 'updated'}}
        status, body = self.put('/v2/repositories/repo-1/distributors/dist-1/', params=req_body)

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(body['config'], req_body['distributor_config'])

        dist = RepoDistributor.get_collection().find_one({'repo_id' : 'repo-1'})
        self.assertEqual(dist['config'], req_body['distributor_config'])

    def test_update_bad_request(self):
        """
        Tests updating a distributor with a bad request.
        """

        # Setup
        self.repo_manager.create_repo('repo-1')
        self.distributor_manager.add_distributor('repo-1', 'mock-distributor', {'key' : 'orig'}, True, 'dist-1')

        # Test
        status, body = self.put('/v2/repositories/repo-1/distributors/dist-1/', params={})

        # Verify
        self.assertEqual(400, status)

    def test_update_missing_repo(self):
        """
        Tests updating a distributor on a repo that doesn't exist.
        """

        # Test
        req_body = {'distributor_config' : {'key' : 'updated'}}
        status, body = self.put('/v2/repositories/foo/distributors/dist-1/', params=req_body)

        # Verify
        self.assertEqual(404, status)

class RepoSyncHistoryTest(testutil.PulpWebserviceTest):

    def setUp(self):
        testutil.PulpWebserviceTest.setUp(self)

        plugin_loader._create_loader()
        mock_plugins.install()

        self.repo_manager = manager_factory.repo_manager()
        self.sync_manager = manager_factory.repo_sync_manager()

    def tearDown(self):
        testutil.PulpWebserviceTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        testutil.PulpTest.clean(self)

        Repo.get_collection().remove()
        RepoSyncResult.get_collection().remove()

    def test_get(self):
        """
        Tests getting sync history for a repo.
        """

        # Setup
        self.repo_manager.create_repo('sync-test')
        for i in range(0, 10):
            self.add_success_result('sync-test', i)

        # Test
        status, body = self.get('/v2/repositories/sync-test/history/sync/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(10, len(body))

    def test_get_no_entries(self):
        """
        Tests getting sync history entries for a repo that exists but hasn't been syncced.
        """

        # Setup
        self.repo_manager.create_repo('boring')

        # Test
        status, body = self.get('/v2/repositories/boring/history/sync/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(0, len(body))

    def test_get_missing_repo(self):
        """
        Tests getting sync history for a repo that doesn't exist.
        """

        # Test
        status, body = self.get('/v2/repositories/no/history/sync/')

        # Verify
        self.assertEqual(404, status)

    def test_get_bad_limit(self):
        """
        Tests getting with an invalid limit query parameter.
        """

        # Setup
        self.repo_manager.create_repo('sync-test')
        self.add_success_result('sync-test', 0)

        # Test
        status, body = self.get('/v2/repositories/sync-test/history/sync/?limit=unparsable')

        # Verify
        self.assertEqual(400, status)

    def add_success_result(self, repo_id, offset):
        started = datetime.datetime.now(dateutils.local_tz())
        completed = started + datetime.timedelta(days=offset)
        r = RepoSyncResult.expected_result(repo_id, 'foo', 'bar', dateutils.format_iso8601_datetime(started), dateutils.format_iso8601_datetime(completed), 1, 1, 1, '', '', RepoSyncResult.RESULT_SUCCESS)
        RepoSyncResult.get_collection().save(r, safe=True)

class RepoPublishHistoryTest(testutil.PulpWebserviceTest):

    def setUp(self):
        testutil.PulpWebserviceTest.setUp(self)

        plugin_loader._create_loader()
        mock_plugins.install()

        self.repo_manager = manager_factory.repo_manager()
        self.distributor_manager = manager_factory.repo_distributor_manager()
        self.publish_manager = manager_factory.repo_publish_manager()

    def tearDown(self):
        testutil.PulpWebserviceTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        testutil.PulpTest.clean(self)

        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoPublishResult.get_collection().remove()

    def test_get(self):
        """
        Tests getting the publish history for a repo.
        """

        # Setup
        self.repo_manager.create_repo('pub-test')
        self.distributor_manager.add_distributor('pub-test', 'mock-distributor', {}, True, distributor_id='dist-1')
        for i in range(0, 10):
            self._add_success_result('pub-test', 'dist-1', i)

        # Test
        status, body = self.get('/v2/repositories/pub-test/history/publish/dist-1/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(10, len(body))

    def test_get_no_entries(self):
        """
        Tests an empty list is returned for a distributor that has not published.
        """

        # Setup
        self.repo_manager.create_repo('foo')
        self.distributor_manager.add_distributor('foo', 'mock-distributor', {}, True, distributor_id='empty')

        # Test
        status, body = self.get('/v2/repositories/foo/history/publish/empty/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(0, len(body))

    def test_get_missing_repo(self):
        """
        Tests getting history for a repo that doesn't exist.
        """

        # Test
        status, body = self.get('/v2/repositories/foo/history/publish/irrlevant/')

        # Verify
        self.assertEqual(404, status)

    def test_get_missing_distributor(self):
        """
        Tests getting history for a distributor that doesn't exist on the repo.
        """

        # Setup
        self.repo_manager.create_repo('foo')

        # Test
        status, body = self.get('/v2/repositories/foo/history/publish/irrlevant/')

        # Verify
        self.assertEqual(404, status)

    def test_get_bad_limit(self):
        """
        Tests getting with an invalid limit query parameter.
        """

        # Test
        status, body = self.get('/v2/repositories/foo/history/publish/empty/?limit=unparsable')

        # Verify
        self.assertEqual(400, status)

    def _add_success_result(self, repo_id, distributor_id, offset):
        started = datetime.datetime.now(dateutils.local_tz())
        completed = started + datetime.timedelta(days=offset)
        r = RepoPublishResult.expected_result(repo_id, distributor_id, 'bar', dateutils.format_iso8601_datetime(started), dateutils.format_iso8601_datetime(completed), '', '', RepoPublishResult.RESULT_SUCCESS)
        RepoPublishResult.get_collection().save(r, safe=True)

class RepoUnitAssociationQueryTest(testutil.PulpWebserviceTest):

    def setUp(self):
        testutil.PulpWebserviceTest.setUp(self)
        self.repo_manager = manager_factory.repo_manager()
        self.repo_manager.create_repo('repo-1')

        self.association_query_mock = mock.Mock()
        manager_factory._INSTANCES[manager_factory.TYPE_REPO_ASSOCIATION_QUERY] = self.association_query_mock

    def clean(self):
        testutil.PulpWebserviceTest.clean(self)
        Repo.get_collection().remove()
        manager_factory.reset()

    def test_post_single_type(self):
        """
        Passes in a full query document to test the parsing into criteria.
        """

        # Setup
        self.association_query_mock.get_units_by_type.return_value = []

        query = {
            'type_ids' : ['rpm'],
            'filters' : {
                'unit' : {'key' : {'$in' : 'zsh'}},
                'association' : {'owner_type' : 'importer'}
            },
            'sort' : {
                'unit' : [ ['name', 'ascending'], ['version', '-1'] ],
                'association' : [ ['created', '-1'], ['updated', '1'] ]
            },
            'limit' : '100',
            'skip' : '200',
            'fields' : {
                'unit' : ['name', 'version', 'arch'],
                'association' : ['created']
            },
            'remove_duplicates' : 'True'
        }

        params = {'query' : query}
        status, body = self.post('/v2/repositories/repo-1/search/units/', params=params)

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(0, self.association_query_mock.get_units_across_types.call_count)
        self.assertEqual(1, self.association_query_mock.get_units_by_type.call_count)

        criteria = self.association_query_mock.get_units_by_type.call_args[1]['criteria']
        self.assertTrue(isinstance(criteria, Criteria))
        self.assertEqual(query['type_ids'], criteria.type_ids)
        self.assertEqual(query['filters']['association'], criteria.association_filters)
        self.assertEqual(query['filters']['unit'], criteria.unit_filters)
        self.assertEqual([('created', Criteria.SORT_DESCENDING), ('updated', Criteria.SORT_ASCENDING)], criteria.association_sort)
        self.assertEqual([('name', Criteria.SORT_ASCENDING), ('version', Criteria.SORT_DESCENDING)], criteria.unit_sort)
        self.assertEqual(int(query['limit']), criteria.limit)
        self.assertEqual(int(query['skip']), criteria.skip)
        self.assertEqual(query['fields']['unit'], criteria.unit_fields)
        self.assertEqual(query['fields']['association'] + ['unit_id', 'unit_type_id'], criteria.association_fields)
        self.assertEqual(bool(query['remove_duplicates']), criteria.remove_duplicates)

    def test_post_multiple_type(self):
        """
        Passes in a multiple typed query to ensure the correct manager method is called.
        """

        # Setup
        self.association_query_mock.get_units_across_types.return_value = []

        query = {'type_ids' : ['rpm', 'errata']}

        params = {'query' : query}
        status, body = self.post('/v2/repositories/repo-1/search/units/', params=params)

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(0, self.association_query_mock.get_units_by_type.call_count)
        self.assertEqual(1, self.association_query_mock.get_units_across_types.call_count)
        self.assertTrue(isinstance(self.association_query_mock.get_units_across_types.call_args[1]['criteria'], Criteria))

    def test_post_missing_query(self):
        # Test
        status, body = self.post('/v2/repositories/repo-1/search/units/')

        # Verify
        self.assertEqual(status, 400)

    def test_post_bad_query(self):
        # Test
        params = {'query' : {'limit' : 'fus'}}
        status, body = self.post('/v2/repositories/repo-1/search/units/', params=params)

        # Verify
        self.assertEqual(400, status)

class RepoAssociateTest(testutil.PulpWebserviceTest):

    def setUp(self):
        testutil.PulpWebserviceTest.setUp(self)

        self.repo_manager = manager_factory.repo_manager()
        self.repo_manager.create_repo('source-repo-1')
        self.repo_manager.create_repo('dest-repo-1')

        self.association_manager_mock = mock.Mock()
        manager_factory._INSTANCES[manager_factory.TYPE_REPO_ASSOCIATION] = self.association_manager_mock

    def clean(self):
        testutil.PulpWebserviceTest.clean(self)
        Repo.get_collection().remove()
        manager_factory.reset()

    def test_post_no_criteria(self):

        # Test
        params = {'source_repo_id' : 'source-repo-1'}
        status, body = self.post('/v2/repositories/dest-repo-1/actions/associate/', params=params)

        # Verify
        self.assertEqual(200, status)

        args, kwargs = self.association_manager_mock.associate_from_repo.call_args
        self.assertEqual(2, len(args))
        self.assertEqual(1, len(kwargs))
        self.assertEqual('source-repo-1', args[0])
        self.assertEqual('dest-repo-1', args[1])
        self.assertEqual(None, kwargs['criteria'])

    def test_post_with_criteria(self):

        # Test
        criteria = {'filters' : {'unit' : {'key-1' : 'fus'}}}
        params = {'source_repo_id' : 'source-repo-1',
                  'criteria' : criteria}

        status, body = self.post('/v2/repositories/dest-repo-1/actions/associate/', params=params)

        # Verify
        self.assertEqual(200, status)

        args, kwargs = self.association_manager_mock.associate_from_repo.call_args
        self.assertEqual(2, len(args))
        self.assertEqual(1, len(kwargs))
        self.assertEqual('source-repo-1', args[0])
        self.assertEqual('dest-repo-1', args[1])
        self.assertEqual({'key-1' : 'fus'}, kwargs['criteria'].unit_filters)

    def test_post_missing_source_repo(self):

        # Test
        status, body = self.post('/v2/repositories/dest-repo-1/actions/associate/')

        # Verify
        self.assertEqual(400, status)

    def test_post_unparsable_criteria(self):

        # Test
        params = {'source_repo_id' : 'source-repo-1',
                  'criteria' : 'unparsable'}
        status, body = self.post('/v2/repositories/dest-repo-1/actions/associate/', params=params)

        # Verify
        self.assertEqual(400, status)
