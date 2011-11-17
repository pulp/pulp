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
import copy
import datetime
import os
import shutil
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil
import mock_plugins

from pulp.common import dateutils
import pulp.server.content.loader as plugin_loader
from pulp.server.db.model.gc_repository import Repo, RepoImporter
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.repo.importer as repo_importer_manager
import pulp.server.managers.repo.publish as repo_publish_manager
import pulp.server.managers.repo.sync as repo_sync_manager

# -- mocks --------------------------------------------------------------------

class MockRepoPublishManager:

    # Last call state
    repo_id = None

    # Call behavior
    raise_error = False

    def validate_config(self, repo_data, distributor_config):
        return True

    def auto_publish_for_repo(self, repo_id):
        MockRepoPublishManager.repo_id = repo_id

        if MockRepoPublishManager.raise_error:
            raise repo_publish_manager.AutoPublishException(repo_id, [])

    @classmethod
    def reset(cls):
        MockRepoPublishManager.repo_id = None
        MockRepoPublishManager.raise_error = False

# -- test cases ---------------------------------------------------------------

class RepoSyncManagerTests(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)
        mock_plugins.install()

        # Create the manager instances for testing
        self.repo_manager = repo_manager.RepoManager()
        self.importer_manager = repo_importer_manager.RepoImporterManager()
        self.sync_manager = repo_sync_manager.RepoSyncManager()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        mock_plugins.reset()

        # Reset the manager factory
        manager_factory.reset()

    def clean(self):
        testutil.PulpTest.clean(self)
        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()

        # Reset the state of the mock's tracker variables
        MockRepoPublishManager.reset()

    def test_sync(self):
        """
        Tests sync under normal conditions where everything is configured
        correctly. No importer config is specified.
        """

        # Setup
        sync_config = {'bruce' : 'hulk', 'tony' : 'ironman'}
        self.repo_manager.create_repo('repo-1')
        self.importer_manager.set_importer('repo-1', 'mock-importer', sync_config)

        # Test
        self.sync_manager.sync('repo-1', sync_config_override=None)

        # Verify
        repo = Repo.get_collection().find_one({'id' : 'repo-1'})
        repo_importer = RepoImporter.get_collection().find_one({'repo_id' : 'repo-1', 'id' : 'mock-importer'})

        #   Verify database
        self.assertTrue(not repo_importer['sync_in_progress'])
        self.assertTrue(repo_importer['last_sync'] is not None)
        self.assertTrue(assert_last_sync_time(repo_importer['last_sync']))

        #   Verify call into the importer
        sync_args = mock_plugins.MOCK_IMPORTER.sync_repo.call_args[0]

        self.assertEqual(repo['id'], sync_args[0].id)
        self.assertTrue(sync_args[1] is not None)
        self.assertEqual({}, sync_args[2].plugin_config)
        self.assertEqual(sync_config, sync_args[2].repo_plugin_config)
        self.assertEqual({}, sync_args[2].override_config)

    def test_sync_with_sync_config_override(self):
        """
        Tests a sync when passing in an individual config of override options.
        """

        # Setup
        importer_config = {'thor' : 'thor'}
        self.repo_manager.create_repo('repo-1')
        self.importer_manager.set_importer('repo-1', 'mock-importer', importer_config)

        # Test
        sync_config_override = {'clint' : 'hawkeye'}
        self.sync_manager.sync('repo-1', sync_config_override=sync_config_override)

        # Verify
        repo = Repo.get_collection().find_one({'id' : 'repo-1'})
        repo_importer = RepoImporter.get_collection().find_one({'repo_id' : 'repo-1', 'id' : 'mock-importer'})

        #   Verify database
        self.assertTrue(not repo_importer['sync_in_progress'])
        self.assertTrue(repo_importer['last_sync'] is not None)
        self.assertTrue(assert_last_sync_time(repo_importer['last_sync']))

        #   Verify call into the importer
        #   Verify call into the importer
        sync_args = mock_plugins.MOCK_IMPORTER.sync_repo.call_args[0]

        self.assertEqual(repo['id'], sync_args[0].id)
        self.assertTrue(sync_args[1] is not None)
        self.assertEqual({}, sync_args[2].plugin_config)
        self.assertEqual(importer_config, sync_args[2].repo_plugin_config)
        self.assertEqual(sync_config_override, sync_args[2].override_config)

    def test_sync_missing_repo(self):
        """
        Tests the proper error is raised when a non-existent repo is specified.
        """

        # Test
        try:
            self.sync_manager.sync('fake-repo')
        except repo_sync_manager.MissingRepo, e:
            self.assertEqual('fake-repo', e.repo_id)
            print(e) # for coverage

    def test_sync_no_importer_set(self):
        """
        Tests the proper error is raised when no importer is set for the repo.
        """

        # Setup
        self.repo_manager.create_repo('importer-less') # don't set importer

        # Test
        try:
            self.sync_manager.sync('importer-less')
        except repo_sync_manager.NoImporter, e:
            self.assertEqual('importer-less', e.repo_id)
            print(e) # for coverage

    def test_sync_bad_importer(self):
        """
        Tests the proper error is raised when an importer is set on the repo but
        the importer is no longer present as a plugin. This situation simulates
        a case where a repo was once successfully configured but the server
        has since been bounced and the importer plugin removed.
        """

        # Setup
        self.repo_manager.create_repo('old-repo')
        self.importer_manager.set_importer('old-repo', 'mock-importer', None)

        #   Simulate bouncing the server and removing the importer plugin
        plugin_loader._LOADER.remove_importer('mock-importer')

        # Test
        try:
            self.sync_manager.sync('old-repo')
        except repo_sync_manager.MissingImporterPlugin, e:
            self.assertEqual('old-repo', e.repo_id)
            print(e) # for coverage

    def test_sync_bad_database(self):
        """
        Tests the case where the database got itself in a bad state where the
        repo thinks it has an importer but the importer-repo relationship doc
        doesn't exist in the database.
        """

        # Setup
        self.repo_manager.create_repo('good-repo')
        self.importer_manager.set_importer('good-repo', 'mock-importer', None)

        RepoImporter.get_collection().remove()

        # Test
        try:
            self.sync_manager.sync('good-repo')
        except repo_sync_manager.NoImporter, e:
            self.assertEqual('good-repo', e.repo_id)
            print(e) # for coverage

    def test_sync_with_error(self):
        """
        Tests a sync when the plugin raises an error.
        """

        # Setup
        mock_plugins.MOCK_IMPORTER.sync_repo.side_effect = Exception()

        self.repo_manager.create_repo('gonna-bail')
        self.importer_manager.set_importer('gonna-bail', 'mock-importer', {})

        # Test
        try:
            self.sync_manager.sync('gonna-bail')
        except repo_sync_manager.RepoSyncException, e:
            self.assertEqual('gonna-bail', e.repo_id)
            print(e) # for coverage

        # Verify
        repo_importer = RepoImporter.get_collection().find_one({'repo_id' : 'gonna-bail', 'id' : 'mock-importer'})

        self.assertTrue(not repo_importer['sync_in_progress'])
        self.assertTrue(repo_importer['last_sync'] is not None)
        self.assertTrue(assert_last_sync_time(repo_importer['last_sync']))

        # Cleanup
        mock_plugins.MOCK_IMPORTER.sync_repo.side_effect = None

    def test_sync_in_progress(self):
        """
        Tests that trying to sync while one is in progress raises the correct
        error.
        """

        # Setup
        self.repo_manager.create_repo('busy')
        self.importer_manager.set_importer('busy', 'mock-importer', {})

        #   Trick the database into thinking it's synccing
        repo_importer = RepoImporter.get_collection().find_one({'repo_id' : 'busy'})
        repo_importer['sync_in_progress'] = True
        RepoImporter.get_collection().save(repo_importer)

        # Test
        try:
            self.sync_manager.sync('busy')
        except repo_sync_manager.SyncInProgress, e:
            self.assertEqual('busy', e.repo_id)
            print(e) # for coverage

    def test_sync_with_auto_publish(self):
        """
        Tests that the autodistribute call is properly called at the tail end
        of a successful sync.
        """

        # Setup
        manager_factory.register_manager(manager_factory.TYPE_REPO_PUBLISH, MockRepoPublishManager)

        self.repo_manager.create_repo('repo')
        self.importer_manager.set_importer('repo', 'mock-importer', {})

        # Test
        self.sync_manager.sync('repo')

        # Verify
        self.assertEqual('repo', MockRepoPublishManager.repo_id)

    def test_sync_with_auto_publish_error(self):
        """
        Tests that the autodistribute exception is propagated when one or more
        auto publish calls fail.
        """

        # Setup
        manager_factory.register_manager(manager_factory.TYPE_REPO_PUBLISH, MockRepoPublishManager)
        MockRepoPublishManager.raise_error = True

        self.repo_manager.create_repo('doa')
        self.importer_manager.set_importer('doa', 'mock-importer', {})

        # Test
        try:
            self.sync_manager.sync('doa')
            self.fail('Expected exception not thrown')
        except repo_publish_manager.AutoPublishException, e:
            self.assertEqual('doa', e.repo_id)

    def test_get_repo_storage_directory(self):
        """
        Tests a repo storage directory can be retrieved and is created in the process.
        """

        # Setup
        temp_dir = '/tmp/test-repo-storage-dir'

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        repo_sync_manager.REPO_STORAGE_DIR = temp_dir

        # Test
        dir = self.sync_manager.get_repo_storage_directory('test-repo')

        # Verify
        self.assertEqual(dir, temp_dir + '/test-repo')
        self.assertTrue(os.path.exists(dir))

# -- testing utilities --------------------------------------------------------

def assert_last_sync_time(time_in_iso):
    now = datetime.datetime.now(dateutils.local_tz())
    finished = dateutils.parse_iso8601_datetime(time_in_iso)

    # Compare them within a threshold since they won't be exact
    difference = now - finished
    return difference.seconds < 2
