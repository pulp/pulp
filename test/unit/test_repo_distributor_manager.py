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
from pulp.server.content.plugins.data import Repository
from pulp.server.content.plugins.config import PluginCallConfiguration
from pulp.server.db.model.gc_repository import Repo, RepoDistributor
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.repo.distributor as distributor_manager

# -- test cases ---------------------------------------------------------------

class RepoManagerTests(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)

        plugin_loader._create_loader()
        mock_plugins.install()

        # Create the manager instance to test
        self.repo_manager = repo_manager.RepoManager()
        self.distributor_manager = distributor_manager.RepoDistributorManager()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        testutil.PulpTest.clean(self)

        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()

    # -- add ------------------------------------------------------------------

    def test_add_distributor(self):
        """
        Tests adding a distributor to a new repo.
        """

        # Setup
        self.repo_manager.create_repo('test_me')
        config = {'foo' : 'bar'}

        # Test
        added = self.distributor_manager.add_distributor('test_me', 'mock-distributor', config, True, distributor_id='my_dist')

        # Verify

        #    Database
        all_distributors = list(RepoDistributor.get_collection().find())
        self.assertEqual(1, len(all_distributors))
        self.assertEqual('my_dist', all_distributors[0]['id'])
        self.assertEqual('mock-distributor', all_distributors[0]['distributor_type_id'])
        self.assertEqual('test_me', all_distributors[0]['repo_id'])
        self.assertEqual(config, all_distributors[0]['config'])
        self.assertTrue(all_distributors[0]['auto_distribute'])

        #   Returned Value
        self.assertEqual('my_dist', added['id'])
        self.assertEqual('mock-distributor', added['distributor_type_id'])
        self.assertEqual('test_me', added['repo_id'])
        self.assertEqual(config, added['config'])
        self.assertTrue(added['auto_distribute'])

        #   Plugin - Validate Config
        self.assertEqual(1, mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_count)
        call_repo = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0][0]
        call_config = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0][1]

        self.assertTrue(isinstance(call_repo, Repository))
        self.assertEqual('test_me', call_repo.id)

        self.assertTrue(isinstance(call_config, PluginCallConfiguration))
        self.assertTrue(call_config.plugin_config is not None)
        self.assertEqual(call_config.repo_plugin_config, config)

        #   Plugin - Distributor Added
        self.assertEqual(1, mock_plugins.MOCK_DISTRIBUTOR.distributor_added.call_count)
        call_repo = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0][0]
        call_config = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0][1]
        self.assertTrue(isinstance(call_repo, Repository))
        self.assertTrue(isinstance(call_config, PluginCallConfiguration))

    def test_add_distributor_multiple_distributors(self):
        """
        Tests adding a second distributor to a repository.
        """

        self.repo_manager.create_repo('test_me')
        self.distributor_manager.add_distributor('test_me', 'mock-distributor', None, True, distributor_id='dist_1')

        # Test
        self.distributor_manager.add_distributor('test_me', 'mock-distributor-2', None, True, distributor_id='dist_2')

        # Verify
        all_distributors = list(RepoDistributor.get_collection().find())
        self.assertEqual(2, len(all_distributors))

        dist_ids = [d['id'] for d in all_distributors]
        self.assertTrue('dist_1' in dist_ids)
        self.assertTrue('dist_2' in dist_ids)

    def test_add_distributor_replace_existing(self):
        """
        Tests adding a distributor under the same ID as an existing distributor.
        """

        # Setup
        self.repo_manager.create_repo('test_me')

        self.distributor_manager.add_distributor('test_me', 'mock-distributor', None, True, distributor_id='dist_1')

        # Test
        config = {'foo' : 'bar'}
        self.distributor_manager.add_distributor('test_me', 'mock-distributor', config, False, distributor_id='dist_1')

        # Verify

        #    Database
        all_distributors = list(RepoDistributor.get_collection().find())
        self.assertEqual(1, len(all_distributors))
        self.assertTrue(not all_distributors[0]['auto_distribute'])
        self.assertEqual(config, all_distributors[0]['config'])

        #    Plugin Calls
        self.assertEqual(2, mock_plugins.MOCK_DISTRIBUTOR.distributor_added.call_count)
        self.assertEqual(1, mock_plugins.MOCK_DISTRIBUTOR.distributor_removed.call_count)

    def test_add_distributor_no_explicit_id(self):
        """
        Tests the ID generation when one is not specified for a distributor.
        """

        # Setup
        self.repo_manager.create_repo('happy-repo')

        # Test
        added = self.distributor_manager.add_distributor('happy-repo', 'mock-distributor', None, True)

        # Verify
        distributor = RepoDistributor.get_collection().find_one({'repo_id' : 'happy-repo', 'id' : added['id']})
        self.assertTrue(distributor is not None)

    def test_add_distributor_no_repo(self):
        """
        Tests adding a distributor to a repo that doesn't exist.
        """

        # Test
        try:
            self.distributor_manager.add_distributor('fake', 'mock-distributor', None, True)
            self.fail('No exception thrown for an invalid repo ID')
        except repo_manager.MissingRepo, e:
            self.assertEqual(e.repo_id, 'fake')
            print(e) # for coverage

    def test_add_distributor_no_distributor(self):
        """
        Tests adding a distributor that doesn't exist.
        """

        # Setup
        self.repo_manager.create_repo('real-repo')

        # Test
        try:
            self.distributor_manager.add_distributor('real-repo', 'fake-distributor', None, True)
            self.fail('No exception thrown for an invalid distributor type')
        except distributor_manager.InvalidDistributorType, e:
            self.assertEqual(e.distributor_type_id, 'fake-distributor')
            print(e) # for coverage

    def test_add_distributor_invalid_id(self):
        """
        Tests adding a distributor with an invalid ID raises the correct error.
        """

        # Setup
        self.repo_manager.create_repo('repo')

        # Test
        bad_id = '!@#$%^&*()'
        try:
            self.distributor_manager.add_distributor('repo', 'mock-distributor', None, True, bad_id)
            self.fail('No exception thrown for an invalid distributor ID')
        except distributor_manager.InvalidDistributorId, e:
            self.assertEqual(bad_id, e.invalid_distributor_id)
            print(e) # for coverage

    def test_add_distributor_initialize_raises_error(self):
        """
        Tests the correct error is raised when the distributor raises an error during validation.
        """

        # Setup
        mock_plugins.MOCK_DISTRIBUTOR.distributor_added.side_effect = Exception()
        self.repo_manager.create_repo('repo')

        # Test
        try:
            self.distributor_manager.add_distributor('repo', 'mock-distributor', None, True)
            self.fail('Exception expected for error during validate')
        except distributor_manager.DistributorInitializationException:
            pass

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.distributor_added.side_effect = None

    def test_add_distributor_validate_raises_error(self):
        """
        Tests the correct error is raised when the distributor raises an error during config validation.
        """

        # Setup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.side_effect = Exception()
        self.repo_manager.create_repo('rohan')

        # Test
        try:
            self.distributor_manager.add_distributor('rohan', 'mock-distributor', None, True)
            self.fail('Exception expected')
        except distributor_manager.InvalidDistributorConfiguration:
            pass

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.side_effect = None

    def test_add_distributor_invalid_config(self):
        """
        Tests the correct error is raised when the distributor is handed an invalid configuration.
        """

        # Setup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = False
        self.repo_manager.create_repo('error_repo')

        # Test
        try:
            self.distributor_manager.add_distributor('error_repo', 'mock-distributor', None, True)
            self.fail('Exception expected for invalid configuration')
        except distributor_manager.InvalidDistributorConfiguration:
            pass

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = True

    # -- remove ---------------------------------------------------------------

    def test_remove_distributor(self):
        """
        Tests removing an existing distributor from a repository.
        """

        # Setup
        self.repo_manager.create_repo('dist-repo')
        self.distributor_manager.add_distributor('dist-repo', 'mock-distributor', None, True, distributor_id='doomed')

        # Test
        self.distributor_manager.remove_distributor('dist-repo', 'doomed')

        # Verify
        distributor = RepoDistributor.get_collection().find_one({'repo_id' : 'dist-repo', 'id' : 'doomed'})
        self.assertTrue(distributor is None)

    def test_remove_distributor_no_distributor(self):
        """
        Tests that no exception is raised when requested to remove a distributor that doesn't exist.
        """

        # Setup
        self.repo_manager.create_repo('empty')

        # Test
        try:
            self.distributor_manager.remove_distributor('empty', 'non-existent')
        except distributor_manager.MissingDistributor, e:
            self.assertEqual('non-existent', e.distributor_id)

    def test_remove_distributor_no_repo(self):
        """
        Tests the proper exception is raised when removing a distributor from a repo that doesn't exist.
        """

        # Test
        try:
            self.distributor_manager.remove_distributor('fake-repo', 'irrelevant')
            self.fail('No exception thrown for an invalid repo ID')
        except repo_manager.MissingRepo, e:
            self.assertEqual(e.repo_id, 'fake-repo')
            print(e) # for coverage

    # -- update ---------------------------------------------------------------

    def test_update_distributor_config(self):
        """
        Tests the successful case of updating a distributor's config.
        """

        # Setup
        self.repo_manager.create_repo('dawnstar')
        distributor = self.distributor_manager.add_distributor('dawnstar', 'mock-distributor', {'key' : 'orig'}, True)
        dist_id = distributor['id']

        # Test
        new_config = {'key' : 'updated'}
        self.distributor_manager.update_distributor_config('dawnstar', dist_id, new_config)

        # Verify

        #    Database
        repo_dist = RepoDistributor.get_collection().find_one({'repo_id' : 'dawnstar'})
        self.assertEqual(repo_dist['config'], new_config)

        #    Plugin
        self.assertEqual(2, mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_count)
        call_config = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0][1]
        self.assertEqual(new_config, call_config.repo_plugin_config)

    def test_update_missing_repo(self):
        """
        Tests updating the distributor config on a repo that doesn't exist.
        """

        # Test
        try:
            self.distributor_manager.update_distributor_config('not-there', 'doesnt-matter', {})
            self.fail('Exception expected')
        except distributor_manager.MissingRepo, e:
            self.assertEqual(e.repo_id, 'not-there')

    def test_update_missing_distributor(self):
        """
        Tests updating the config on a distributor that doesn't exist on the repo.
        """

        # Setup
        self.repo_manager.create_repo('empty')

        # Test
        try:
            self.distributor_manager.update_distributor_config('empty', 'missing', {})
            self.fail('Exception expected')
        except distributor_manager.MissingDistributor, e:
            self.assertEqual('missing', e.distributor_id)

    def test_update_validate_exception(self):
        """
        Tests updating a config when the plugin raises an exception during validate.
        """

        # Setup
        self.repo_manager.create_repo('elf')
        distributor = self.distributor_manager.add_distributor('elf', 'mock-distributor', {}, True)
        dist_id = distributor['id']

        mock_plugins.MOCK_DISTRIBUTOR.validate_config.side_effect = Exception()

        # Test
        try:
            self.distributor_manager.update_distributor_config('elf', dist_id, {})
            self.fail('Exception expected')
        except distributor_manager.InvalidDistributorConfiguration:
            pass

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.side_effect = None

    def test_update_invalid_config(self):
        """
        Tests updating a config when the plugin indicates the config is invalid.
        """

        # Setup
        self.repo_manager.create_repo('dwarf')
        distributor = self.distributor_manager.add_distributor('dwarf', 'mock-distributor', {}, True)
        dist_id = distributor['id']

        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = False

        # Test
        try:
            self.distributor_manager.update_distributor_config('dwarf', dist_id, {})
            self.fail('Exception expected')
        except distributor_manager.InvalidDistributorConfiguration:
            pass

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = True

    # -- scratchpad -----------------------------------------------------------

    def test_get_set_distributor_scratchpad(self):
        """
        Tests the retrieval and setting of a repo distributor's scratchpad.
        """

        # Setup
        self.repo_manager.create_repo('repo')
        self.distributor_manager.add_distributor('repo', 'mock-distributor', {}, True, distributor_id='dist')

        # Test - Unset Scratchpad
        scratchpad = self.distributor_manager.get_distributor_scratchpad('repo', 'dist')
        self.assertTrue(scratchpad is None)

        # Test - Set
        contents = 'gnomish mines'
        self.distributor_manager.set_distributor_scratchpad('repo', 'dist', contents)

        # Test - Get
        scratchpad = self.distributor_manager.get_distributor_scratchpad('repo', 'dist')
        self.assertEqual(contents, scratchpad)

    def test_get_set_distributor_scratchpad_missing(self):
        """
        Tests no error is raised when getting or setting the scratchpad for missing cases.
        """

        # Setup
        self.repo_manager.create_repo('empty')

        # Test - Get
        scratchpad = self.distributor_manager.get_distributor_scratchpad('empty', 'not_there')
        self.assertTrue(scratchpad is None)

        # Test - Set No Distributor
        self.distributor_manager.set_distributor_scratchpad('empty', 'fake_distributor', 'stuff')

        # Test - Set No Repo
        self.distributor_manager.set_distributor_scratchpad('fake', 'irrelevant', 'blah')
