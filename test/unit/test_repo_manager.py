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
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo._common as common_utils
import pulp.server.exceptions as exceptions

# -- test cases ---------------------------------------------------------------

class RepoManagerTests(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)

        plugin_loader._create_loader()
        mock_plugins.install()

        # Create the manager instance to test
        self.manager = repo_manager.RepoManager()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        testutil.PulpTest.clean(self)

        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoDistributor.get_collection().remove()

    def test_create(self):
        """
        Tests creating a repo with valid data is successful.
        """

        # Setup
        id = 'repo_1'
        name = 'Repository 1'
        description = 'Test Repository 1'
        notes = {'note1' : 'value1'}

        # Test
        created = self.manager.create_repo(id, name, description, notes)

        # Verify
        repos = list(Repo.get_collection().find())
        self.assertEqual(1, len(repos))

        repo = repos[0]
        self.assertEqual(id, repo['id'])
        self.assertEqual(name, repo['display_name'])
        self.assertEqual(description, repo['description'])
        self.assertEqual(notes, repo['notes'])

        self.assertEqual(id, created['id'])
        self.assertEqual(name, created['display_name'])
        self.assertEqual(description, created['description'])
        self.assertEqual(notes, created['notes'])

    def test_create_defaults(self):
        """
        Tests creating a repository with minimal information (ID) is successful.
        """

        # Test
        self.manager.create_repo('repo_1')

        # Verify
        repos = list(Repo.get_collection().find())
        self.assertEqual(1, len(repos))
        self.assertEqual('repo_1', repos[0]['id'])

        #   Assert the display name is defaulted to the id
        self.assertEqual('repo_1', repos[0]['display_name'])

    def _test_create_invalid_id(self):
        """
        Tests creating a repo with an invalid ID raises the correct error.
        """

        # Test
        try:
            self.manager.create_repo('bad id')
            self.fail('Invalid ID did not raise an exception')
        except exceptions.InvalidValue, e:
            self.assertTrue('bad id' in e)
            print(e) # for coverage

    def test_create_duplicate_id(self):
        """
        Tests creating a repo with an ID already being used by a repo raises
        the correct error.
        """

        # Setup
        id = 'duplicate'
        self.manager.create_repo(id)

        # Test
        try:
            self.manager.create_repo(id)
            self.fail('Repository with an existing ID did not raise an exception')
        except exceptions.DuplicateResource, e:
            self.assertTrue(id in e)
            print(e) # for coverage

    def test_create_invalid_notes(self):
        """
        Tests that creating a repo but passing a non-dict as the notes field
        raises the correct exception.
        """

        # Setup
        id = 'bad-notes'
        notes = 'not a dict'

        # Test
        try:
            self.manager.create_repo(id, notes=notes)
            self.fail('Invalid notes did not cause create to raise an exception')
        except exceptions.InvalidValue, e:
            self.assertTrue(notes in e)
            print(e) # for coverage

    def test_delete_repo(self):
        """
        Tests deleting a repo under normal circumstances.
        """

        # Setup
        id = 'doomed'
        self.manager.create_repo(id)

        # Test
        self.manager.delete_repo(id)

        # Verify
        repos = list(Repo.get_collection().find({'id' : id}))
        self.assertEqual(0, len(repos))

    def test_delete_repo_no_repo(self):
        """
        Tests that deleting a repo that doesn't exist raises the appropriate error.
        """

        # Test
        try:
            self.manager.delete_repo('fake repo')
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('fake repo' in e)

    def test_delete_with_plugins(self):
        """
        Tests that deleting a repo that has importers and distributors configured deletes them as well.
        """

        # Setup
        self.manager.create_repo('doomed')

        importer_manager = manager_factory.repo_importer_manager()
        distributor_manager = manager_factory.repo_distributor_manager()

        importer_manager.set_importer('doomed', 'mock-importer', {})
        distributor_manager.add_distributor('doomed', 'mock-distributor', {}, True, distributor_id='dist-1')
        distributor_manager.add_distributor('doomed', 'mock-distributor', {}, True, distributor_id='dist-2')

        self.assertEqual(1, len(list(RepoImporter.get_collection().find({'repo_id' : 'doomed'}))))
        self.assertEqual(2, len(list(RepoDistributor.get_collection().find({'repo_id' : 'doomed'}))))

        # Test
        self.manager.delete_repo('doomed')

        # Verify
        self.assertEqual(0, len(list(Repo.get_collection().find())))

        self.assertEqual(0, len(list(RepoImporter.get_collection().find({'repo_id' : 'doomed'}))))
        self.assertEqual(0, len(list(RepoDistributor.get_collection().find({'repo_id' : 'doomed'}))))

        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.importer_removed.call_count)
        self.assertEqual(2, mock_plugins.MOCK_DISTRIBUTOR.distributor_removed.call_count)

        repo_working_dir = common_utils.repository_working_dir('doomed', mkdir=False)
        self.assertTrue(not os.path.exists(repo_working_dir))
        
    def test_delete_with_plugin_error(self):
        """
        Tests deleting a repo where one (or more) of the plugins raises an error.
        """

        # Setup
        self.manager.create_repo('doomed')

        importer_manager = manager_factory.repo_importer_manager()
        distributor_manager = manager_factory.repo_distributor_manager()

        importer_manager.set_importer('doomed', 'mock-importer', {})
        distributor_manager.add_distributor('doomed', 'mock-distributor', {}, True, distributor_id='dist-1')

        #    Setup both mocks to raise errors on removal
        mock_plugins.MOCK_IMPORTER.importer_removed.side_effect = Exception('Splat')
        mock_plugins.MOCK_DISTRIBUTOR.distributor_removed.side_effect = Exception('Pow')

        # Test
        try:
            self.manager.delete_repo('doomed')
            self.fail('No exception raised during repo delete')
        except exceptions.OperationFailed, e:
            pass

        # Cleanup - need to manually clear the side effects
        mock_plugins.MOCK_IMPORTER.importer_removed.side_effect = None
        mock_plugins.MOCK_DISTRIBUTOR.distributor_removed.side_effect = None

    def test_update_repo(self):
        """
        Tests the case of successfully updating a repo.
        """

        # Setup
        self.manager.create_repo('update-me', display_name='display_name_1', description='description_1', notes={'a' : 'a'})

        delta = {
            'display_name' : 'display_name_2',
            'description'  : 'description_2',
            'notes'        : {'b' : 'b'},
            'disregard'    : 'ignored',
        }

        # Test
        updated = self.manager.update_repo('update-me', delta)

        # Verify
        repo = Repo.get_collection().find_one({'id' : 'update-me'})
        self.assertEqual(repo['display_name'], delta['display_name'])
        self.assertEqual(repo['description'], delta['description'])
        self.assertEqual(repo['notes'], delta['notes'])

        self.assertEqual(updated['display_name'], delta['display_name'])
        self.assertEqual(updated['description'], delta['description'])
        self.assertEqual(updated['notes'], delta['notes'])

    def test_update_missing_repo(self):
        """
        Tests updating a repo that isn't there raises the appropriate exception.
        """

        # Test
        try:
            self.manager.update_repo('not-there', {})
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('not-there' in e)

    def test_get_set_scratchpad(self):
        """
        Tests retrieving and setting a repository's scratchpad.
        """

        # Setup
        repo_id = 'scratch-test'
        self.manager.create_repo(repo_id)

        # Test - get default
        value = self.manager.get_repo_scratchpad(repo_id)
        self.assertEqual({}, value)

        # Test - set
        new_value = {'i' : 'importer', 'd' : 'distributor'}
        self.manager.set_repo_scratchpad(repo_id, new_value)

        value = self.manager.get_repo_scratchpad(repo_id)
        self.assertEqual(new_value, value)

class UtilityMethodsTests(testutil.PulpTest):

    def test_is_repo_id_valid(self):
        """
        Tests the repo ID validation with both valid and invalid IDs.
        """

        # Test
        self.assertTrue(repo_manager.is_repo_id_valid('repo'))
        self.assertTrue(repo_manager.is_repo_id_valid('repo1'))
        self.assertTrue(repo_manager.is_repo_id_valid('repo-1'))
        self.assertTrue(repo_manager.is_repo_id_valid('repo_1'))
        self.assertTrue(repo_manager.is_repo_id_valid('_repo'))

        self.assertTrue(not repo_manager.is_repo_id_valid('repo 1'))
        self.assertTrue(not repo_manager.is_repo_id_valid('repo#1'))
        self.assertTrue(not repo_manager.is_repo_id_valid('repo!'))
