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

from pulp.server.db.model.gc_repository import Repo, RepoImporter, RepoDistributor
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.repo.query as query_manager

# -- test cases ---------------------------------------------------------------

class RepoQueryManagerTests(testutil.PulpTest):

    def clean(self):
        testutil.PulpTest.clean(self)

        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoDistributor.get_collection().remove()
        
    def setUp(self):
        testutil.PulpTest.setUp(self)

        self.repo_manager = repo_manager.RepoManager()
        self.query_manager = query_manager.RepoQueryManager()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)

    def test_find_all(self):
        """
        Tests finding all repos when there are results to return.
        """

        # Setup
        self.repo_manager.create_repo('repo-1')
        self.repo_manager.create_repo('repo-2')

        # Test
        results = self.query_manager.find_all()

        # Verify
        self.assertTrue(results is not None)
        self.assertEqual(2, len(results))

        ids = [r['id'] for r in results]
        self.assertTrue('repo-1' in ids)
        self.assertTrue('repo-2' in ids)

    def test_find_all_no_results(self):
        """
        Tests that finding all repos when none are present does not error and
        correctly returns an empty list.
        """

        # Test
        results = self.query_manager.find_all()

        # Verify
        self.assertTrue(results is not None)
        self.assertEqual(0, len(results))

    def test_find_by_id(self):
        """
        Tests finding an existing repository by its ID.
        """

        # Setup
        self.repo_manager.create_repo('repo-1')
        self.repo_manager.create_repo('repo-2')

        # Test
        repo = self.query_manager.find_by_id('repo-2')

        # Verify
        self.assertTrue(repo is not None)
        self.assertEqual('repo-2', repo['id'])

    def test_find_by_id_no_repo(self):
        """
        Tests attempting to find a repo that doesn't exist by its ID does not
        raise an error and correctly returns none.
        """

        # Setup
        self.repo_manager.create_repo('repo-1')

        # Test
        repo = self.query_manager.find_by_id('not-there')

        # Verify
        self.assertTrue(repo is None)

    def test_find_by_id_list(self):
        """
        Tests finding a list of repositories by ID.
        """

        # Setup
        self.repo_manager.create_repo('repo-a')
        self.repo_manager.create_repo('repo-b')
        self.repo_manager.create_repo('repo-c')
        self.repo_manager.create_repo('repo-d')

        # Test
        repos = self.query_manager.find_by_id_list(['repo-b', 'repo-c'])

        # Verify
        self.assertEqual(2, len(repos))

        ids = [r['id'] for r in repos]
        self.assertTrue('repo-b' in ids)
        self.assertTrue('repo-c' in ids)
