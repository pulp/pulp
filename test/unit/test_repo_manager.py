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

import pulp.server.content.manager as content_manager
from pulp.server.db.model.gc_repository import Repo, RepoImporter, RepoDistributor
import pulp.server.managers.repo.cud as repo_manager

# -- mocks --------------------------------------------------------------------

class MockImporter:

    # Last Call State
    repo_data = None
    importer_config = None

    # Call Behavior
    is_valid_config = True
    raise_error = False

    def validate_config(self, repo_data, importer_config):
        MockImporter.repo_data = repo_data
        MockImporter.importer_config = importer_config

        if MockImporter.raise_error:
            raise Exception('Simulated exception from importer')

        return MockImporter.is_valid_config

    @classmethod
    def reset(cls):
        MockImporter.repo_data = None
        MockImporter.importer_config = None

        MockImporter.is_valid_config = True
        MockImporter.raise_error = False

class MockDistributor:
    pass

# -- test cases ---------------------------------------------------------------

class RepoManagerTests(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)

        content_manager._create_manager()

        # Configure content manager
        content_manager._MANAGER.add_importer('MockImporter', 1, MockImporter, None)
        content_manager._MANAGER.add_distributor('MockDistributor', 1, MockDistributor, None)

        # Create the manager instance to test
        self.manager = repo_manager.RepoManager()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)

        # Reset content manager
        content_manager._MANAGER.remove_importer('MockImporter', 1)
        content_manager._MANAGER.remove_distributor('MockDistributor', 1)

    def clean(self):
        testutil.PulpTest.clean(self)
        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoDistributor.get_collection().remove()
        MockImporter.reset()

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
        self.manager.create_repo(id, name, description, notes)

        # Verify
        repos = list(Repo.get_collection().find())
        self.assertEqual(1, len(repos))

        repo = repos[0]
        self.assertEqual(id, repo['id'])
        self.assertEqual(name, repo['display_name'])
        self.assertEqual(description, repo['description'])
        self.assertEqual(notes, repo['notes'])

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
        
    def test_create_invalid_id(self):
        """
        Tests creating a repo with an invalid ID raises the correct error.
        """

        # Test
        try:
            self.manager.create_repo('bad id')
            self.fail('Invalid ID did not raise an exception')
        except repo_manager.InvalidRepoId, e:
            self.assertEqual(e.invalid_repo_id, 'bad id')
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
        except repo_manager.DuplicateRepoId, e:
            self.assertEqual(e.duplicate_id, id)
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
        except repo_manager.InvalidRepoMetadata, e:
            self.assertEqual(e.invalid_data, notes)
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
        Tests that deleting a repo that doesn't exist does not throw an error.
        """

        # Test
        self.manager.delete_repo('fake repo') # should not error

    def test_delete_with_plugins(self):
        """
        Tests that deleting a repo that has importers and distributors configured deletes them as well.
        """

        # Setup
        self.manager.create_repo('doomed')
        self.manager.set_importer('doomed', 'MockImporter', {})
        self.manager.add_distributor('doomed', 'MockDistributor', {}, True, distributor_id='dist-1')
        self.manager.add_distributor('doomed', 'MockDistributor', {}, True, distributor_id='dist-2')

        self.assertEqual(1, len(list(RepoImporter.get_collection().find({'repo_id' : 'doomed'}))))
        self.assertEqual(2, len(list(RepoDistributor.get_collection().find({'repo_id' : 'doomed'}))))

        # Test
        self.manager.delete_repo('doomed')

        # Verify
        self.assertEqual(0, len(list(RepoImporter.get_collection().find({'repo_id' : 'doomed'}))))
        self.assertEqual(0, len(list(RepoDistributor.get_collection().find({'repo_id' : 'doomed'}))))

    def test_set_importer(self):
        """
        Tests setting an importer on a new repo (normal case).
        """

        # Setup
        self.manager.create_repo('importer-test')
        importer_config = {'foo' : 'bar'}

        # Test
        self.manager.set_importer('importer-test', 'MockImporter', importer_config)

        # Verify
        importer = RepoImporter.get_collection().find_one({'repo_id' : 'importer-test', 'id' : 'MockImporter'})
        self.assertEqual('importer-test', importer['repo_id'])
        self.assertEqual('MockImporter', importer['id'])
        self.assertEqual('MockImporter', importer['importer_type_id'])
        self.assertEqual(importer_config, importer['config'])

        self.assertEqual(importer_config, MockImporter.importer_config)
        self.assertEqual('importer-test', MockImporter.repo_data['id'])

    def test_set_importer_no_repo(self):
        """
        Tests setting the importer on a repo that doesn't exist correctly
        informs the user.
        """

        # Test
        try:
            self.manager.set_importer('fake', 'MockImporter', None)
        except repo_manager.MissingRepo, e:
            self.assertEqual(e.repo_id, 'fake')
            print(e) # for coverage

    def test_set_importer_no_importer(self):
        """
        Tests setting an importer that doesn't exist on a repo.
        """

        # Setup
        self.manager.create_repo('real-repo')

        # Test
        try:
            self.manager.set_importer('real-repo', 'fake-importer', None)
        except repo_manager.MissingImporter, e:
            self.assertEqual(e.importer_name, 'fake-importer')
            print(e) # for coverage

    def test_set_importer_with_existing(self):
        """
        Tests setting a different importer on a repo that already had one.
        """

        # Setup
        class MockImporter2:
            def validate_config(self, repo_data, importer_config):
                return True

        content_manager._MANAGER.add_importer('MockImporter2', 1, MockImporter2, None)

        self.manager.create_repo('change_me')
        self.manager.set_importer('change_me', 'MockImporter', None)

        # Test
        self.manager.set_importer('change_me', 'MockImporter2', None)

        # Verify
        all_importers = list(RepoImporter.get_collection().find())
        self.assertEqual(1, len(all_importers))
        self.assertEqual(all_importers[0]['id'], 'MockImporter2')

    def test_set_importer_validate_raises_error(self):
        """
        Tests simulating an error coming out of the importer's validate config method.
        """

        # Setup
        MockImporter.raise_error = True
        self.manager.create_repo('repo-1')

        # Test
        config = {'hobbit' : 'frodo'}
        try:
            self.manager.set_importer('repo-1', 'MockImporter', config)
            self.fail('Exception expected for importer plugin exception')
        except repo_manager.InvalidImporterConfiguration:
            pass

    def test_set_importer_invalid_config(self):
        """
        Tests the set_importer call properly errors when the config is invalid.
        """

        # Setup
        MockImporter.is_valid_config = False
        self.manager.create_repo('bad_config')

        # Test
        config = {'elf' : 'legolas'}
        try:
            self.manager.set_importer('bad_config', 'MockImporter', config)
            self.fail('Exception expected for bad config')
        except repo_manager.InvalidImporterConfiguration:
            pass

    def test_add_distributor(self):
        """
        Tests adding a distributor to a new repo.
        """

        # Setup
        self.manager.create_repo('test_me')

        config = {'foo' : 'bar'}

        # Test
        self.manager.add_distributor('test_me', 'MockDistributor', config, True, distributor_id='my_dist')

        # Verify
        all_distributors = list(RepoDistributor.get_collection().find())
        self.assertEqual(1, len(all_distributors))
        self.assertEqual('my_dist', all_distributors[0]['id'])
        self.assertEqual('MockDistributor', all_distributors[0]['distributor_type_id'])
        self.assertEqual('test_me', all_distributors[0]['repo_id'])
        self.assertEqual(config, all_distributors[0]['config'])
        self.assertTrue(all_distributors[0]['auto_distribute'])

    def test_add_distributor_multiple_distributors(self):
        """
        Tests adding a second distributor to a repository.
        """

        # Setup
        class MockDistributor2:
            pass
        content_manager._MANAGER.add_distributor('MockDistributor2', 1, MockDistributor2, None)

        self.manager.create_repo('test_me')
        self.manager.add_distributor('test_me', 'MockDistributor', None, True, distributor_id='dist_1')

        # Test
        self.manager.add_distributor('test_me', 'MockDistributor2', None, True, distributor_id='dist_2')

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
        self.manager.create_repo('test_me')

        self.manager.add_distributor('test_me', 'MockDistributor', None, True, distributor_id='dist_1')

        # Test
        config = {'foo' : 'bar'}
        self.manager.add_distributor('test_me', 'MockDistributor', config, False, distributor_id='dist_1')

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
        self.manager.create_repo('happy-repo')

        # Test
        generated_id = self.manager.add_distributor('happy-repo', 'MockDistributor', None, True)

        # Verify
        distributor = RepoDistributor.get_collection().find_one({'repo_id' : 'happy-repo', 'id' : generated_id})
        self.assertTrue(distributor is not None)

    def test_add_distributor_no_repo(self):
        """
        Tests adding a distributor to a repo that doesn't exist.
        """

        # Test
        try:
            self.manager.add_distributor('fake', 'MockDistributor', None, True)
            self.fail('No exception thrown for an invalid repo ID')
        except repo_manager.MissingRepo, e:
            self.assertEqual(e.repo_id, 'fake')
            print(e) # for coverage

    def test_add_distributor_no_distributor(self):
        """
        Tests adding a distributor that doesn't exist.
        """

        # Setup
        self.manager.create_repo('real-repo')

        # Test
        try:
            self.manager.add_distributor('real-repo', 'fake-distributor', None, True)
            self.fail('No exception thrown for an invalid distributor type')
        except repo_manager.MissingDistributor, e:
            self.assertEqual(e.distributor_name, 'fake-distributor')
            print(e) # for coverage

    def test_add_distributor_invalid_id(self):
        """
        Tests adding a distributor with an invalid ID raises the correct error.
        """

        # Setup
        self.manager.create_repo('repo')

        # Test
        bad_id = '!@#$%^&*()'
        try:
            self.manager.add_distributor('repo', 'MockDistributor', None, True, bad_id)
            self.fail('No exception thrown for an invalid distributor ID')
        except repo_manager.InvalidDistributorId, e:
            self.assertEqual(bad_id, e.invalid_distributor_id)
            print(e) # for coverage

    def test_remove_distributor(self):
        """
        Tests removing an existing distributor from a repository.
        """

        # Setup
        self.manager.create_repo('dist-repo')
        self.manager.add_distributor('dist-repo', 'MockDistributor', None, True, distributor_id='doomed')

        # Test
        self.manager.remove_distributor('dist-repo', 'doomed')

        # Verify
        distributor = RepoDistributor.get_collection().find_one({'repo_id' : 'dist-repo', 'id' : 'doomed'})
        self.assertTrue(distributor is None)

    def test_remove_distributor_no_distributor(self):
        """
        Tests that no exception is raised when requested to remove a distributor that doesn't exist.
        """

        # Setup
        self.manager.create_repo('empty')

        # Test
        self.manager.remove_distributor('empty', 'non-existent') # shouldn't error

    def test_remove_distributor_no_repo(self):
        """
        Tests the proper exception is raised when removing a distributor from a repo that doesn't exist.
        """

        # Test
        try:
            self.manager.remove_distributor('fake-repo', 'irrelevant')
            self.fail('No exception thrown for an invalid repo ID')
        except repo_manager.MissingRepo, e:
            self.assertEqual(e.repo_id, 'fake-repo')
            print(e) # for coverage

    def test_add_metadata_values(self):
        """
        Tests adding metadata to a repo under normal working conditions.
        """

        # Setup
        self.manager.create_repo('repo')

        # Test
        values_1 = {'key_1' : 'orig_1', 'key_2' : 'orig_2'}
        self.manager.add_metadata_values('repo', values_1)

        values_2 = {'key_2' : 'new_2', 'key_3' : 'new_3'}
        self.manager.add_metadata_values('repo', values_2)

        # Verify
        repo = Repo.get_collection().find_one({'id' : 'repo'})
        metadata = repo['metadata']

        self.assertTrue('key_1' in metadata)
        self.assertTrue('key_2' in metadata)
        self.assertTrue('key_3' in metadata)

        self.assertEqual('orig_1', metadata['key_1'])
        self.assertEqual('new_2', metadata['key_2'])
        self.assertEqual('new_3', metadata['key_3'])
        
    def test_add_metadata_values_no_repo(self):
        """
        Tests the correct error is raised when adding metadata to a repo that doesn't exist.
        """

        # Test
        try:
            self.manager.add_metadata_values('not-there', {1 : 2})
        except repo_manager.MissingRepo, e:
            self.assertEqual('not-there', e.repo_id)
            print(e) # for coverage

    def test_add_metadata_values_bad_values(self):
        """
        Tests the correct error is raised when passing in a bad argument for values.
        """

        # Setup
        self.manager.create_repo('repo')

        # Test
        try:
            self.manager.add_metadata_values('repo', 'bad-values')
        except repo_manager.InvalidRepoMetadata, e:
            self.assertEqual('bad-values', e.invalid_data)
            print(e) # for coverage

    def test_remove_metadata_values(self):
        """
        Tests removing metadata under normal working conditions.
        """

        # Setup
        self.manager.create_repo('repo')
        self.manager.add_metadata_values('repo', {'key_1' : 'value_1', 'key_2' : 'value_2'})

        # Test
        self.manager.remove_metadata_values('repo', ['key_1', 'non_existent'])

        # Verify
        repo = Repo.get_collection().find_one({'id' : 'repo'})
        metadata = repo['metadata']

        self.assertEqual(1, len(metadata))
        self.assertEqual('value_2', metadata['key_2'])

    def test_remove_metadata_values_no_repo(self):
        """
        Tests the correct error is raised when specifying a repo that doesn't exist.
        """

        # Test
        try:
            self.manager.remove_metadata_values('not-here', ['irrelevant'])
        except repo_manager.MissingRepo, e:
            self.assertEqual('not-here', e.repo_id)

    def test_get_set_importer_scratchpad(self):
        """
        Tests the retrieval and setting of a repo importer's scratchpad.
        """

        # Setup
        self.manager.create_repo('repo')
        self.manager.set_importer('repo', 'MockImporter', {})

        # Test - Unset Scratchpad
        scratchpad = self.manager.get_importer_scratchpad('repo')
        self.assertTrue(scratchpad is None)

        # Test - Set
        contents = ['yendor', 'sokoban']
        self.manager.set_importer_scratchpad('repo', contents)

        # Test - Get
        scratchpad = self.manager.get_importer_scratchpad('repo')
        self.assertEqual(contents, scratchpad)

    def test_get_set_importer_scratchpad_missing(self):
        """
        Tests no error is raised when getting or setting the scratchpad for missing cases.
        """

        # Setup
        self.manager.create_repo('empty')

        # Test - Get
        scratchpad = self.manager.get_importer_scratchpad('empty')
        self.assertTrue(scratchpad is None)

        # Test - Set No Importer
        self.manager.set_importer_scratchpad('empty', 'foo') # should not error

        # Test - Set Fake Repo
        self.manager.set_importer_scratchpad('fake', 'bar') # should not error

    def test_get_set_distributor_scratchpad(self):
        """
        Tests the retrieval and setting of a repo distributor's scratchpad.
        """

        # Setup
        self.manager.create_repo('repo')
        self.manager.add_distributor('repo', 'MockDistributor', {}, True, distributor_id='dist')

        # Test - Unset Scratchpad
        scratchpad = self.manager.get_distributor_scratchpad('repo', 'dist')
        self.assertTrue(scratchpad is None)

        # Test - Set
        contents = 'gnomish mines'
        self.manager.set_distributor_scratchpad('repo', 'dist', contents)

        # Test - Get
        scratchpad = self.manager.get_distributor_scratchpad('repo', 'dist')
        self.assertEqual(contents, scratchpad)

    def test_get_set_distributor_scratchpad_missing(self):
        """
        Tests no error is raised when getting or setting the scratchpad for missing cases.
        """

        # Setup
        self.manager.create_repo('empty')

        # Test - Get
        scratchpad = self.manager.get_distributor_scratchpad('empty', 'not_there')
        self.assertTrue(scratchpad is None)

        # Test - Set No Distributor
        self.manager.set_distributor_scratchpad('empty', 'fake_distributor', 'stuff')

        # Test - Set No Repo
        self.manager.set_distributor_scratchpad('fake', 'irrelevant', 'blah')

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
        