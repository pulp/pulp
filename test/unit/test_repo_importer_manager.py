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
from pulp.server.content.plugins.importer import Importer
from pulp.server.content.plugins.data import Repository
from pulp.server.content.plugins.config import PluginCallConfiguration
from pulp.server.db.model.gc_repository import Repo, RepoImporter
import pulp.server.managers.repo._exceptions as errors
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.repo.importer as importer_manager

# -- test cases ---------------------------------------------------------------

class RepoManagerTests(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)
        mock_plugins.install()

        # Create the manager instance to test
        self.repo_manager = repo_manager.RepoManager()
        self.importer_manager = importer_manager.RepoImporterManager()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        testutil.PulpTest.clean(self)

        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()

    # -- set ------------------------------------------------------------------

    def test_set_importer(self):
        """
        Tests setting an importer on a new repo (normal case).
        """

        # Setup
        self.repo_manager.create_repo('importer-test')
        importer_config = {'foo' : 'bar'}

        # Test
        created = self.importer_manager.set_importer('importer-test', 'mock-importer', importer_config)

        # Verify

        #   Database
        importer = RepoImporter.get_collection().find_one({'repo_id' : 'importer-test', 'id' : 'mock-importer'})
        self.assertEqual('importer-test', importer['repo_id'])
        self.assertEqual('mock-importer', importer['id'])
        self.assertEqual('mock-importer', importer['importer_type_id'])
        self.assertEqual(importer_config, importer['config'])

        #   Return Value
        self.assertEqual('importer-test', created['repo_id'])
        self.assertEqual('mock-importer', created['id'])
        self.assertEqual('mock-importer', created['importer_type_id'])
        self.assertEqual(importer_config, created['config'])

        #   Plugin - Validate Config
        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.importer_added.call_count)
        call_repo = mock_plugins.MOCK_IMPORTER.validate_config.call_args[0][0]
        call_config = mock_plugins.MOCK_IMPORTER.validate_config.call_args[0][1]

        self.assertTrue(isinstance(call_repo, Repository))
        self.assertEqual('importer-test', call_repo.id)

        self.assertTrue(isinstance(call_config, PluginCallConfiguration))
        self.assertTrue(call_config.plugin_config is not None)
        self.assertEqual(call_config.repo_plugin_config, importer_config)

        #   Plugin - Importer Added
        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.validate_config.call_count)
        call_repo = mock_plugins.MOCK_IMPORTER.validate_config.call_args[0][0]
        call_config = mock_plugins.MOCK_IMPORTER.validate_config.call_args[0][1]
        self.assertTrue(isinstance(call_repo, Repository))
        self.assertTrue(isinstance(call_config, PluginCallConfiguration))

    def test_set_importer_no_repo(self):
        """
        Tests setting the importer on a repo that doesn't exist correctly
        informs the user.
        """

        # Test
        try:
            self.importer_manager.set_importer('fake', 'mock-importer', None)
        except errors.MissingRepo, e:
            self.assertEqual(e.repo_id, 'fake')
            print(e) # for coverage

    def test_set_importer_no_importer(self):
        """
        Tests setting an importer that doesn't exist on a repo.
        """

        # Setup
        self.repo_manager.create_repo('real-repo')

        # Test
        try:
            self.importer_manager.set_importer('real-repo', 'fake-importer', None)
        except errors.InvalidImporterType, e:
            self.assertEqual(e.importer_type_id, 'fake-importer')
            print(e) # for coverage

    def test_set_importer_with_existing(self):
        """
        Tests setting a different importer on a repo that already had one.
        """

        # Setup
        class MockImporter2(Importer):
            @classmethod
            def metadata(cls):
                return {'types': ['mock_types_2']}

            def validate_config(self, repo_data, importer_config):
                return True

        mock_plugins.IMPORTER_MAPPINGS['mock-importer-2'] = MockImporter2()
        plugin_loader._LOADER.add_importer('mock-importer-2', MockImporter2, {})

        self.repo_manager.create_repo('change_me')
        self.importer_manager.set_importer('change_me', 'mock-importer', None)

        # Test
        self.importer_manager.set_importer('change_me', 'mock-importer-2', None)

        # Verify
        all_importers = list(RepoImporter.get_collection().find())
        self.assertEqual(1, len(all_importers))
        self.assertEqual(all_importers[0]['id'], 'mock-importer-2')

        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.importer_removed.call_count)

    def test_set_importer_added_raises_error(self):
        """
        Tests simulating an error coming out of the importer's validate config method.
        """

        # Setup
        mock_plugins.MOCK_IMPORTER.importer_added.side_effect = Exception()
        self.repo_manager.create_repo('repo-1')

        # Test
        config = {'hobbit' : 'frodo'}
        try:
            self.importer_manager.set_importer('repo-1', 'mock-importer', config)
            self.fail('Exception expected for importer plugin exception')
        except errors.ImporterInitializationException:
            pass

        # Cleanup
        mock_plugins.MOCK_IMPORTER.importer_added.side_effect = None

    def test_set_importer_validate_config_error(self):
        """
        Tests manager handling when the plugin raises an error while validating a config.
        """

        # Setup
        mock_plugins.MOCK_IMPORTER.validate_config.side_effect = Exception()
        self.repo_manager.create_repo('bad_config')

        # Test
        config = {}
        try:
            self.importer_manager.set_importer('bad_config', 'mock-importer', config)
            self.fail('Exception expected for bad config')
        except errors.InvalidImporterConfiguration:
            pass

        # Cleanup
        mock_plugins.MOCK_IMPORTER.validate_config.side_effect = None

    def test_set_importer_invalid_config(self):
        """
        Tests the set_importer call properly errors when the config is invalid.
        """

        # Setup
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = False
        self.repo_manager.create_repo('bad_config')

        # Test
        config = {'elf' : 'legolas'}
        try:
            self.importer_manager.set_importer('bad_config', 'mock-importer', config)
            self.fail('Exception expected for bad config')
        except errors.InvalidImporterConfiguration:
            pass

    # -- remove ---------------------------------------------------------------

    def test_remove_importer(self):
        """
        Tests the successful case of removing an importer.
        """

        # Setup
        self.repo_manager.create_repo('whiterun')
        self.importer_manager.set_importer('whiterun', 'mock-importer', {})

        # Test
        self.importer_manager.remove_importer('whiterun')

        # Verify
        importer = RepoImporter.get_collection().find_one({'repo_id' : 'whiterun', 'id' : 'mock-importer'})
        self.assertTrue(importer is None)

        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.importer_removed.call_count)
        
    def test_remove_importer_missing_repo(self):
        """
        Tests removing the importer from a repo that doesn't exist.
        """

        # Test
        try:
            self.importer_manager.remove_importer('not-there')
            self.fail('Exception expected')
        except errors.MissingRepo, e:
            self.assertEqual(e.repo_id, 'not-there')

    def test_remove_importer_missing_importer(self):
        """
        Tests removing an importer from a repo that doesn't have one.
        """

        # Setup
        self.repo_manager.create_repo('solitude')

        # Test
        try:
            self.importer_manager.remove_importer('solitude')
            self.fail('Exception expected')
        except errors.MissingImporter:
            pass

    # -- update ---------------------------------------------------------------

    def test_update_importer_config(self):
        """
        Tests the successful case of updating an importer's configuration.
        """

        # Setup
        self.repo_manager.create_repo('winterhold')
        self.importer_manager.set_importer('winterhold', 'mock-importer', {'key' : 'initial'})

        # Test
        new_config = {'key' : 'updated'}
        updated = self.importer_manager.update_importer_config('winterhold', new_config)

        # Verify

        #    Database
        importer = RepoImporter.get_collection().find_one({'repo_id' : 'winterhold', 'id' : 'mock-importer'})
        self.assertEqual(importer['config'], new_config)

        #    Return Value
        self.assertEqual(updated['config'], new_config)

        #    Plugin
        self.assertEqual(2, mock_plugins.MOCK_IMPORTER.validate_config.call_count) # initial and update
        self.assertEqual(new_config, mock_plugins.MOCK_IMPORTER.validate_config.call_args[0][1].repo_plugin_config) # returns args from last call

    def test_update_importer_missing_repo(self):
        """
        Tests the appropriate exception is raised when updating the importer on a non-existent repo.
        """

        # Test
        try:
            self.importer_manager.update_importer_config('not-there', 'mock-importer')
            self.fail('Exception expected')
        except errors.MissingRepo, e:
            self.assertEqual(e.repo_id, 'not-there')

    def test_update_importer_missing_importer(self):
        """
        Tests the appropriate exception is raised when updating a repo that has no importer.
        """

        # Setup
        self.repo_manager.create_repo('empty')

        # Test
        try:
            self.importer_manager.update_importer_config('empty', 'no-importer-here')
            self.fail('Exception expected')
        except errors.MissingImporter:
            pass

    def test_update_importer_plugin_exception(self):
        """
        Tests the appropriate exception is raised when the plugin throws an error during validation.
        """

        # Setup
        self.repo_manager.create_repo('riverwood')
        self.importer_manager.set_importer('riverwood', 'mock-importer', None)

        mock_plugins.MOCK_IMPORTER.validate_config.side_effect = Exception()

        # Test
        try:
            self.importer_manager.update_importer_config('riverwood', {})
            self.fail('Exception expected')
        except errors.InvalidImporterConfiguration:
            pass

        # Cleanup
        mock_plugins.MOCK_IMPORTER.validate_config.side_effect = None

    def test_update_importer_invalid_config(self):
        """
        Tests the appropriate exception is raised when the plugin indicates the config is invalid.
        """

        # Setup
        self.repo_manager.create_repo('restoration')
        self.importer_manager.set_importer('restoration', 'mock-importer', None)

        mock_plugins.MOCK_IMPORTER.validate_config.return_value = False

        # Test
        try:
            self.importer_manager.update_importer_config('restoration', {})
            self.fail('Exception expected')
        except errors.InvalidImporterConfiguration:
            pass

        # Cleanup
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = True

    # -- get ------------------------------------------------------------------

    def test_get_importer(self):
        """
        Tests retrieving a repo's importer in the successful case.
        """

        # Setup
        self.repo_manager.create_repo('trance')
        importer_config = {'volume' : 'two'}
        self.importer_manager.set_importer('trance', 'mock-importer', importer_config)

        # Test
        importer = self.importer_manager.get_importer('trance')

        # Verify
        self.assertTrue(importer is not None)
        self.assertEqual(importer['id'], 'mock-importer')
        self.assertEqual(importer['repo_id'], 'trance')
        self.assertEqual(importer['config'], importer_config)

    def test_get_importer_missing_repo(self):
        """
        Tests getting the importer for a repo that doesn't exist.
        """

        # Test
        self.assertRaises(errors.MissingImporter, self.importer_manager.get_importer, 'fake-repo')

    def test_get_importer_missing_importer(self):
        """
        Tests getting the importer for a repo that doesn't have one associated.
        """

        # Setup
        self.repo_manager.create_repo('empty')

        # Test
        self.assertRaises(errors.MissingImporter, self.importer_manager.get_importer, 'empty')

    def test_get_importers(self):
        """
        Tests the successful case of getting the importer list for a repo.
        """

        # Setup
        self.repo_manager.create_repo('trance')
        self.importer_manager.set_importer('trance', 'mock-importer', {})

        # Test
        importers = self.importer_manager.get_importers('trance')

        # Verify
        self.assertTrue(importers is not None)
        self.assertEqual(1, len(importers))
        self.assertEqual('mock-importer', importers[0]['id'])
        
    def test_get_importers_none(self):
        """
        Tests an empty list is returned for a repo that has none.
        """

        # Setup
        self.repo_manager.create_repo('trance')

        # Test
        importers = self.importer_manager.get_importers('trance')

        # Verify
        self.assertTrue(importers is not None)
        self.assertEqual(0, len(importers))

    def test_get_importers_missing_repo(self):
        """
        Tests an exception is raised when getting importers for a repo that doesn't exist.
        """

        # Test
        try:
            self.importer_manager.get_importers('fake')
            self.fail('Exception expected')
        except errors.MissingRepo, e:
            self.assertEqual('fake', e.repo_id)

    # -- scratchpad -----------------------------------------------------------

    def test_get_set_importer_scratchpad(self):
        """
        Tests the retrieval and setting of a repo importer's scratchpad.
        """

        # Setup
        self.repo_manager.create_repo('repo')
        self.importer_manager.set_importer('repo', 'mock-importer', {})

        # Test - Unset Scratchpad
        scratchpad = self.importer_manager.get_importer_scratchpad('repo')
        self.assertTrue(scratchpad is None)

        # Test - Set
        contents = ['yendor', 'sokoban']
        self.importer_manager.set_importer_scratchpad('repo', contents)

        # Test - Get
        scratchpad = self.importer_manager.get_importer_scratchpad('repo')
        self.assertEqual(contents, scratchpad)

    def test_get_set_importer_scratchpad_missing(self):
        """
        Tests no error is raised when getting or setting the scratchpad for missing cases.
        """

        # Setup
        self.repo_manager.create_repo('empty')

        # Test - Get
        scratchpad = self.importer_manager.get_importer_scratchpad('empty')
        self.assertTrue(scratchpad is None)

        # Test - Set No Importer
        self.importer_manager.set_importer_scratchpad('empty', 'foo') # should not error

        # Test - Set Fake Repo
        self.importer_manager.set_importer_scratchpad('fake', 'bar') # should not error

