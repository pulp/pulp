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
import pulp.server.managers.repo as repo_manager

# -- mocks --------------------------------------------------------------------

class MockImporter:
    pass

class MockDistributor:
    pass

# -- test cases ---------------------------------------------------------------

class RepoManagerCreateAndInitializeTests(testutil.PulpTest):

    def setUp(self):
        super(RepoManagerCreateAndInitializeTests, self).setUp()

        content_manager._create_manager()

        # Configure content manager
        content_manager._MANAGER.add_importer('MockImporter', 1, MockImporter, None)
        content_manager._MANAGER.add_distributor('MockDistributor', 1, MockDistributor, None)

    def tearDown(self):
        super(RepoManagerCreateAndInitializeTests, self).tearDown()

        # Reset content manager
        content_manager._MANAGER.remove_importer('MockImporter', 1)
        content_manager._MANAGER.remove_distributor('MockDistributor', 1)

    def clean(self):
        super(RepoManagerCreateAndInitializeTests, self).clean()
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
        manager = repo_manager.RepoManager()
        manager.create_repo(id, name, description, notes)

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
        manager = repo_manager.RepoManager()
        manager.create_repo('repo_1')

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
        manager = repo_manager.RepoManager()
        try:
            manager.create_repo('bad id')
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
        manager = repo_manager.RepoManager()

        manager.create_repo(id)

        # Test
        try:
            manager.create_repo(id)
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
        manager = repo_manager.RepoManager()

        try:
            manager.create_repo(id, notes=notes)
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
        manager = repo_manager.RepoManager()
        manager.create_repo(id)

        # Test
        manager.delete_repo(id)

        # Verify
        repos = list(Repo.get_collection().find({'id' : id}))
        self.assertEqual(0, len(repos))

    def test_delete_repo_no_repo(self):
        """
        Tests that deleting a repo that doesn't exist does not throw an error.
        """

        # Test
        manager = repo_manager.RepoManager()
        manager.delete_repo('fake repo')

    def test_set_importer(self):
        """
        Tests setting an importer on a new repo (normal case).
        """

        # Setup
        manager = repo_manager.RepoManager()
        manager.create_repo('importer-test')

        importer_config = {'foo' : 'bar'}

        # Test
        manager.set_importer('importer-test', 'MockImporter', importer_config)

        # Verify
        repo = Repo.get_collection().find_one({'id' : 'importer-test'})
        self.assertEqual(1, len(repo['importers']))
        self.assertTrue('MockImporter' in repo['importers'])

        importer = RepoImporter.get_collection().find_one({'repo_id' : 'importer-test', 'id' : 'MockImporter'})
        self.assertEqual('importer-test', importer['repo_id'])
        self.assertEqual('MockImporter', importer['id'])
        self.assertEqual('MockImporter', importer['importer_type_id'])
        self.assertEqual(importer_config, importer['config'])
        
    def test_set_importer_no_repo(self):
        """
        Tests setting the importer on a repo that doesn't exist correctly
        informs the user.
        """

        # Test
        manager = repo_manager.RepoManager()

        try:
            manager.set_importer('fake', 'MockImporter', None)
        except repo_manager.MissingRepo, e:
            self.assertEqual(e.repo_id, 'fake')
            print(e) # for coverage

    def test_set_importer_no_importer(self):
        """
        Tests setting an importer that doesn't exist on a repo.
        """

        # Setup
        manager = repo_manager.RepoManager()
        manager.create_repo('real-repo')

        # Test
        try:
            manager.set_importer('real-repo', 'fake-importer', None)
        except repo_manager.MissingImporter, e:
            self.assertEqual(e.importer_name, 'fake-importer')
            print(e) # for coverage

    def test_set_importer_with_existing(self):
        """
        Tests setting a different importer on a repo that already had one.
        """

        # Setup
        class MockImporter2:
            pass

        content_manager._MANAGER.add_importer('MockImporter2', 1, MockImporter2, None)

        manager = repo_manager.RepoManager()
        manager.create_repo('change_me')

        manager.set_importer('change_me', 'MockImporter', None)

        # Test
        manager.set_importer('change_me', 'MockImporter2', None)

        # Verify
        repo = Repo.get_collection().find_one({'id' : 'change_me'})
        self.assertEqual(1, len(repo['importers']))
        self.assertTrue('MockImporter2' in repo['importers'])

        all_importers = list(RepoImporter.get_collection().find())
        self.assertEqual(1, len(all_importers))
        self.assertEqual(all_importers[0]['id'], 'MockImporter2')

    def test_add_distributor(self):
        """
        Tests adding a distributor to a new repo.
        """

        # Setup
        manager = repo_manager.RepoManager()
        manager.create_repo('test_me')

        config = {'foo' : 'bar'}

        # Test
        manager.add_distributor('test_me', 'MockDistributor', config, True, distributor_id='my_dist')

        # Verify
        repo = Repo.get_collection().find_one({'id' : 'test_me'})
        self.assertEqual(1, len(repo['distributors']))
        self.assertTrue('my_dist' in repo['distributors'])

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

        manager = repo_manager.RepoManager()
        manager.create_repo('test_me')

        manager.add_distributor('test_me', 'MockDistributor', None, True, distributor_id='dist_1')

        # Test
        manager.add_distributor('test_me', 'MockDistributor2', None, True, distributor_id='dist_2')

        # Verify
        repo = Repo.get_collection().find_one({'id' : 'test_me'})
        self.assertEqual(2, len(repo['distributors']))
        self.assertTrue('dist_1' in repo['distributors'])
        self.assertTrue('dist_2' in repo['distributors'])

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
        manager = repo_manager.RepoManager()
        manager.create_repo('test_me')

        manager.add_distributor('test_me', 'MockDistributor', None, True, distributor_id='dist_1')

        # Test
        config = {'foo' : 'bar'}
        manager.add_distributor('test_me', 'MockDistributor', config, False, distributor_id='dist_1')

        # Verify
        repo = Repo.get_collection().find_one({'id' : 'test_me'})
        self.assertEqual(1, len(repo['distributors']))
        self.assertTrue('dist_1' in repo['distributors'])

        all_distributors = list(RepoDistributor.get_collection().find())
        self.assertEqual(1, len(all_distributors))
        self.assertTrue(not all_distributors[0]['auto_distribute'])
        self.assertEqual(config, all_distributors[0]['config'])

    def test_add_distributor_no_explicit_id(self):
        """
        Tests the ID generation when one is not specified for a distributor.
        """

        # Setup
        manager = repo_manager.RepoManager()
        manager.create_repo('happy-repo')

        # Test
        generated_id = manager.add_distributor('happy-repo', 'MockDistributor', None, True)

        # Verify - distributor ID will be random,
        repo = Repo.get_collection().find_one({'id' : 'happy-repo'})
        self.assertEqual(1, len(repo['distributors']))
        self.assertTrue(generated_id in repo['distributors'])

        distributor = RepoDistributor.get_collection().find_one({'repo_id' : 'happy-repo', 'id' : generated_id})
        self.assertTrue(distributor is not None)

    def test_add_distributor_no_repo(self):
        """
        Tests adding a distributor to a repo that doesn't exist.
        """

        # Test
        manager = repo_manager.RepoManager()

        try:
            manager.add_distributor('fake', 'MockDistributor', None, True)
        except repo_manager.MissingRepo, e:
            self.assertEqual(e.repo_id, 'fake')
            print(e) # for coverage

    def test_add_distributor_no_distributor(self):
        """
        Tests adding a distributor that doesn't exist.
        """

        # Setup
        manager = repo_manager.RepoManager()
        manager.create_repo('real-repo')

        # Test
        try:
            manager.add_distributor('real-repo', 'fake-distributor', None, True)
        except repo_manager.MissingDistributor, e:
            self.assertEqual(e.distributor_name, 'fake-distributor')
            print(e) # for coverage

    def test_add_distributor_invalid_id(self):
        """
        Tests adding a distributor with an invalid ID raises the correct error.
        """

        # Setup
        manager = repo_manager.RepoManager()
        manager.create_repo('repo')

        # Test
        bad_id = '!@#$%^&*()'
        try:
            manager.add_distributor('repo', 'MockDistributor', None, True, bad_id)
        except repo_manager.InvalidDistributorId, e:
            self.assertEqual(bad_id, e.invalid_distributor_id)
            print(e) # for coverage

    def test_remove_distributor(self):
        """
        Tests removing an existing distributor from a repository.
        """

        # Setup
        manager = repo_manager.RepoManager()
        manager.create_repo('dist-repo')
        manager.add_distributor('dist-repo', 'MockDistributor', None, True, distributor_id='doomed')

        # Test
        manager.remove_distributor('dist-repo', 'doomed')

        # Verify
        repo = Repo.get_collection().find_one({'id' : 'dist-repo'})
        self.assertEqual(0, len(repo['distributors']))

        distributor = RepoDistributor.get_collection().find_one({'repo_id' : 'dist-repo', 'id' : 'doomed'})
        self.assertTrue(distributor is None)

    def test_remove_distributor_no_distributor(self):
        """
        Tests that no exception is raised when requested to remove a distributor
        that doesn't exist.
        """

        # Setup
        manager = repo_manager.RepoManager()
        manager.create_repo('empty')

        # Test
        manager.remove_distributor('empty', 'non-existent') # shouldn't error

    def test_remove_distributor_no_repo(self):
        """
        Tests the proper exception is raised when removing a distributor from
        a repo that doesn't exist.
        """

        # Test
        manager = repo_manager.RepoManager()
        try:
            manager.remove_distributor('fake-repo', 'irrelevant')
        except repo_manager.MissingRepo, e:
            self.assertEqual(e.repo_id, 'fake-repo')
            print(e) # for coverage

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
        