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

    def test_add_distributor(self):
        """
        Tests adding a distributor to a new repo.
        """

        # Setup
        self.repo_manager.create_repo('test_me')
        config = {'foo' : 'bar'}

        # Test
        self.distributor_manager.add_distributor('test_me', 'mock-distributor', config, True, distributor_id='my_dist')

        # Verify
        all_distributors = list(RepoDistributor.get_collection().find())
        self.assertEqual(1, len(all_distributors))
        self.assertEqual('my_dist', all_distributors[0]['id'])
        self.assertEqual('mock-distributor', all_distributors[0]['distributor_type_id'])
        self.assertEqual('test_me', all_distributors[0]['repo_id'])
        self.assertEqual(config, all_distributors[0]['config'])
        self.assertTrue(all_distributors[0]['auto_distribute'])

    def test_add_distributor_multiple_distributors(self):
        """
        Tests adding a second distributor to a repository.
        """

        # Setup
        class MockDistributor2:
            @classmethod
            def metadata(cls):
                return {'types': ['mock_type_2']}
            def validate_config(self, repo_data, distributor_config):
                return True
        plugin_loader._LOADER.add_distributor('MockDistributor2', MockDistributor2, {})

        self.repo_manager.create_repo('test_me')
        self.distributor_manager.add_distributor('test_me', 'mock-distributor', None, True, distributor_id='dist_1')

        # Test
        self.distributor_manager.add_distributor('test_me', 'MockDistributor2', None, True, distributor_id='dist_2')

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
        all_distributors = list(RepoDistributor.get_collection().find())
        self.assertEqual(1, len(all_distributors))
        self.assertTrue(not all_distributors[0]['auto_distribute'])
        self.assertEqual(config, all_distributors[0]['config'])

    def test_add_distributor_no_explicit_id(self):
        """
        Tests the ID generation when one is not specified for a distributor.
        """

        # Setup
        self.repo_manager.create_repo('happy-repo')

        # Test
        generated_id = self.distributor_manager.add_distributor('happy-repo', 'mock-distributor', None, True)

        # Verify
        distributor = RepoDistributor.get_collection().find_one({'repo_id' : 'happy-repo', 'id' : generated_id})
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
        except distributor_manager.MissingDistributor, e:
            self.assertEqual(e.distributor_name, 'fake-distributor')
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

    def test_add_distributor_raises_error(self):
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
        except distributor_manager.InvalidDistributorConfiguration:
            pass

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.distributor_added.side_effect = None

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
        self.distributor_manager.remove_distributor('empty', 'non-existent') # shouldn't error

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
