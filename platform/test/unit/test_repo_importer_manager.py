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

import base
import mock_plugins

import mock

import pulp.plugins.loader as plugin_loader
from pulp.plugins.importer import Importer
from pulp.plugins.model import Repository
from pulp.plugins.config import PluginCallConfiguration
from pulp.server.db.model.repository import Repo, RepoImporter
import pulp.server.exceptions as exceptions
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.repo.importer as importer_manager

# -- test cases ---------------------------------------------------------------

class RepoManagerTests(base.PulpServerTests):

    def setUp(self):
        super(RepoManagerTests, self).setUp()
        mock_plugins.install()

        # Create the manager instance to test
        self.repo_manager = repo_manager.RepoManager()
        self.importer_manager = importer_manager.RepoImporterManager()

    def tearDown(self):
        super(RepoManagerTests, self).tearDown()
        mock_plugins.reset()

    def clean(self):
        super(RepoManagerTests, self).clean()

        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()

    # -- set ------------------------------------------------------------------

    def test_set_importer(self):
        """
        Tests setting an importer on a new repo (normal case).
        """

        # Setup
        self.repo_manager.create_repo('importer-test')
        importer_config = {'key1' : 'value1', 'key2' : None}

        # Test
        created = self.importer_manager.set_importer('importer-test', 'mock-importer', importer_config)

        # Verify
        expected_config = {'key1' : 'value1'}

        #   Database
        importer = RepoImporter.get_collection().find_one({'repo_id' : 'importer-test', 'id' : 'mock-importer'})
        self.assertEqual('importer-test', importer['repo_id'])
        self.assertEqual('mock-importer', importer['id'])
        self.assertEqual('mock-importer', importer['importer_type_id'])
        self.assertEqual(expected_config, importer['config'])

        #   Return Value
        self.assertEqual('importer-test', created['repo_id'])
        self.assertEqual('mock-importer', created['id'])
        self.assertEqual('mock-importer', created['importer_type_id'])
        self.assertEqual(expected_config, created['config'])

        #   Plugin - Validate Config
        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.importer_added.call_count)
        call_repo = mock_plugins.MOCK_IMPORTER.validate_config.call_args[0][0]
        call_config = mock_plugins.MOCK_IMPORTER.validate_config.call_args[0][1]

        self.assertTrue(isinstance(call_repo, Repository))
        self.assertEqual('importer-test', call_repo.id)

        self.assertTrue(isinstance(call_config, PluginCallConfiguration))
        self.assertTrue(call_config.plugin_config is not None)
        self.assertEqual(call_config.repo_plugin_config, expected_config)

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
        except exceptions.MissingResource, e:
            self.assertTrue('fake' == e.resources['resource_id'])
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
        except exceptions.InvalidValue, e:
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

            def validate_config(self, repo_data, importer_config, related_repos):
                return True

        mock_plugins.IMPORTER_MAPPINGS['mock-importer-2'] = MockImporter2()
        plugin_loader._LOADER.add_importer('mock-importer-2', MockImporter2, {})

        self.repo_manager.create_repo('change_me')
        self.importer_manager.set_importer('change_me', 'mock-importer', {})

        # Test
        self.importer_manager.set_importer('change_me', 'mock-importer-2', {})

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
        except exceptions.PulpExecutionException:
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
        except exceptions.PulpDataException:
            pass

        # Cleanup
        mock_plugins.MOCK_IMPORTER.validate_config.side_effect = None

    def test_set_importer_invalid_config(self):
        """
        Tests the set_importer call properly errors when the config is invalid.
        """

        # Setup
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = (False, 'Invalid stuff')
        self.repo_manager.create_repo('bad_config')

        # Test
        config = {'elf' : 'legolas'}
        try:
            self.importer_manager.set_importer('bad_config', 'mock-importer', config)
            self.fail('Exception expected for bad config')
        except exceptions.PulpDataException, e:
            self.assertEqual(e[0], 'Invalid stuff')

    def test_set_importer_invalid_config_backward_compatibility(self):
        """
        Tests the set_importer call properly errors when the config is invalid
        and the importer still returns a single boolean.
        """

        # Setup
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = False
        self.repo_manager.create_repo('bad_config')

        # Test
        config = {'elf' : 'legolas'}
        try:
            self.importer_manager.set_importer('bad_config', 'mock-importer', config)
            self.fail('Exception expected for bad config')
        except exceptions.PulpDataException:
            pass

    def test_set_importer_with_related(self):
        # Setup
        self.repo_manager.create_repo('repo-a')
        self.repo_manager.create_repo('repo-b')

        self.importer_manager.set_importer('repo-a', 'mock-importer', {'a' : 'a'})

        # Test
        self.importer_manager.set_importer('repo-b', 'mock-importer', {'b' : 'b'})

        # Verify
        args = mock_plugins.MOCK_IMPORTER.validate_config.call_args[0]
        self.assertEqual(args[1].repo_plugin_config, {'b' : 'b'})

        related_repos = args[2]
        self.assertEqual(1, len(related_repos))
        self.assertEqual(related_repos[0].id, 'repo-a')
        self.assertEqual(1, len(related_repos[0].plugin_configs))
        self.assertEqual(related_repos[0].plugin_configs[0], {'a' : 'a'})

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
        except exceptions.MissingResource, e:
            self.assertTrue('not-there' == e.resources['resource_id'])

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
        except exceptions.MissingResource:
            pass

    # -- update ---------------------------------------------------------------

    def test_update_importer_config(self):
        """
        Tests the successful case of updating an importer's configuration.
        """

        # Setup
        self.repo_manager.create_repo('winterhold')

        orig_config = {'key1' : 'initial1',
                       'key2' : 'initial2',
                       'key3' : 'initial3',}
        self.importer_manager.set_importer('winterhold', 'mock-importer', orig_config)

        # Test
        config_delta = {'key1' : 'updated1',
                        'key2' : None}
        updated = self.importer_manager.update_importer_config('winterhold', config_delta)

        # Verify
        expected_config = {'key1' : 'updated1',
                           'key3' : 'initial3'}

        #    Database
        importer = RepoImporter.get_collection().find_one({'repo_id' : 'winterhold', 'id' : 'mock-importer'})
        self.assertEqual(importer['config'], expected_config)

        #    Return Value
        self.assertEqual(updated['config'], expected_config)

        #    Plugin
        self.assertEqual(2, mock_plugins.MOCK_IMPORTER.validate_config.call_count) # initial and update
        self.assertEqual(expected_config, mock_plugins.MOCK_IMPORTER.validate_config.call_args[0][1].repo_plugin_config) # returns args from last call

    def test_update_importer_missing_repo(self):
        """
        Tests the appropriate exception is raised when updating the importer on a non-existent repo.
        """

        # Test
        try:
            self.importer_manager.update_importer_config('not-there', {})
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('not-there' == e.resources['resource_id'])

    def test_update_importer_missing_importer(self):
        """
        Tests the appropriate exception is raised when updating a repo that has no importer.
        """

        # Setup
        self.repo_manager.create_repo('empty')

        # Test
        try:
            self.importer_manager.update_importer_config('empty', {})
            self.fail('Exception expected')
        except exceptions.MissingResource:
            pass

    def test_update_importer_plugin_exception(self):
        """
        Tests the appropriate exception is raised when the plugin throws an error during validation.
        """

        # Setup
        self.repo_manager.create_repo('riverwood')
        self.importer_manager.set_importer('riverwood', 'mock-importer', {})

        mock_plugins.MOCK_IMPORTER.validate_config.side_effect = Exception()

        # Test
        try:
            self.importer_manager.update_importer_config('riverwood', {})
            self.fail('Exception expected')
        except exceptions.PulpDataException:
            pass

        # Cleanup
        mock_plugins.MOCK_IMPORTER.validate_config.side_effect = None

    def test_update_importer_invalid_config(self):
        """
        Tests the appropriate exception is raised when the plugin indicates the config is invalid.
        """

        # Setup
        self.repo_manager.create_repo('restoration')
        self.importer_manager.set_importer('restoration', 'mock-importer', {})

        mock_plugins.MOCK_IMPORTER.validate_config.return_value = (False, 'Invalid stuff')

        # Test
        try:
            self.importer_manager.update_importer_config('restoration', {})
            self.fail('Exception expected')
        except exceptions.PulpDataException, e:
            self.assertEqual('Invalid stuff', e[0])

        # Cleanup
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = True

    def test_update_importer_invalid_config_backward_compatibility(self):
        """
        Tests the appropriate exception is raised when the plugin indicates the config is invalid.
        """

        # Setup
        self.repo_manager.create_repo('restoration')
        self.importer_manager.set_importer('restoration', 'mock-importer', {})

        mock_plugins.MOCK_IMPORTER.validate_config.return_value = False

        # Test
        try:
            self.importer_manager.update_importer_config('restoration', {})
            self.fail('Exception expected')
        except exceptions.PulpDataException:
            pass

        # Cleanup
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = True

    def test_update_importer_with_related(self):
        # Setup
        self.repo_manager.create_repo('repo-a')
        self.repo_manager.create_repo('repo-b')

        self.importer_manager.set_importer('repo-a', 'mock-importer', {'a' : 'a'})
        self.importer_manager.set_importer('repo-b', 'mock-importer', {'b' : 'b1'})

        # Test
        self.importer_manager.update_importer_config('repo-b', {'b' : 'b2'})

        # Verify
        args = mock_plugins.MOCK_IMPORTER.validate_config.call_args[0]
        self.assertEqual(args[1].repo_plugin_config, {'b' : 'b2'})

        related_repos = args[2]
        self.assertEqual(1, len(related_repos))
        self.assertEqual(related_repos[0].id, 'repo-a')
        self.assertEqual(1, len(related_repos[0].plugin_configs))
        self.assertTrue(related_repos[0].plugin_configs[0], {'a' : 'a'})

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
        self.assertRaises(exceptions.MissingResource, self.importer_manager.get_importer, 'fake-repo')

    def test_get_importer_missing_importer(self):
        """
        Tests getting the importer for a repo that doesn't have one associated.
        """

        # Setup
        self.repo_manager.create_repo('empty')

        # Test
        self.assertRaises(exceptions.MissingResource, self.importer_manager.get_importer, 'empty')

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
        except exceptions.MissingResource, e:
            self.assertTrue('fake' == e.resources['resource_id'])

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

    # -- sync schedules --------------------------------------------------------

    def test_sync_schedule(self):

        # setup
        repo_id = 'scheduled_repo'
        importer_type_id = 'mock-importer'
        schedule_id = 'scheduled_repo_sync'
        self.repo_manager.create_repo(repo_id)
        self.importer_manager.set_importer(repo_id, importer_type_id, {})

        # pre-condition
        self.assertEqual(len(self.importer_manager.list_sync_schedules(repo_id)), 0)

        # add the schedule
        self.importer_manager.add_sync_schedule(repo_id, schedule_id)
        self.assertTrue(schedule_id in self.importer_manager.list_sync_schedules(repo_id))
        self.assertEqual(len(self.importer_manager.list_sync_schedules(repo_id)), 1)

        # idempotent add
        self.importer_manager.add_sync_schedule(repo_id, schedule_id)
        self.assertEqual(len(self.importer_manager.list_sync_schedules(repo_id)), 1)

        # remove the schedule
        self.importer_manager.remove_sync_schedule(repo_id, schedule_id)
        self.assertFalse(schedule_id in self.importer_manager.list_sync_schedules(repo_id))
        self.assertEqual(len(self.importer_manager.list_sync_schedules(repo_id)), 0)

        # idempotent remove
        self.importer_manager.remove_sync_schedule(repo_id, schedule_id)
        self.assertEqual(len(self.importer_manager.list_sync_schedules(repo_id)), 0)

        # errors
        self.importer_manager.remove_importer(repo_id)
        self.assertRaises(exceptions.MissingResource,
                          self.importer_manager.add_sync_schedule,
                          repo_id, schedule_id)
        self.assertRaises(exceptions.MissingResource,
                          self.importer_manager.remove_sync_schedule,
                          repo_id, schedule_id)

    @mock.patch.object(RepoImporter, 'get_collection')
    def test_find_by_repo_list(self, mock_get_collection):
        EXPECT = {'repo_id': {'$in': ['repo-1']}}
        self.importer_manager.find_by_repo_list(['repo-1'])
        self.assertTrue(mock_get_collection.return_value.find.called)
        mock_get_collection.return_value.find.assert_called_once_with(EXPECT)
