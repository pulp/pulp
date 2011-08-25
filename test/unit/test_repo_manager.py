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

from pulp.server.db.model.gc_repository import Repo
import pulp.server.managers.repo as repo_manager

# -- test cases --------------------------------------------------------------

class RepoManagerTests(testutil.PulpTest):

    def clean(self):
        super(RepoManagerTests, self).clean()
        Repo.get_collection().remove()

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
            print(e)
        
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
            print(e)

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
            print(e)

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
        