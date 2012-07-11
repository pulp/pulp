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

import mock

import base
import mock_plugins
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.repository import Repo, RepoImporter, RepoDistributor
import pulp.server.managers.factory as manager_factory

# -- test cases ---------------------------------------------------------------

class RepoQueryManagerTests(base.PulpServerTests):

    def clean(self):
        super(RepoQueryManagerTests, self).clean()

        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoDistributor.get_collection().remove()
        
    def setUp(self):
        super(RepoQueryManagerTests, self).setUp()
        mock_plugins.install()

        self.repo_manager = manager_factory.repo_manager()
        self.importer_manager = manager_factory.repo_importer_manager()
        self.distributor_manager = manager_factory.repo_distributor_manager()
        self.query_manager = manager_factory.repo_query_manager()

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

    def test_find_with_distributor_type(self):
        # Setup
        self.repo_manager.create_repo('repo-a')
        self.repo_manager.create_repo('repo-b')
        self.repo_manager.create_repo('repo-c')
        self.repo_manager.create_repo('repo-d')

        self.distributor_manager.add_distributor('repo-a', 'mock-distributor', {'a1' : 'a1'}, True, distributor_id='dist-1')
        self.distributor_manager.add_distributor('repo-a', 'mock-distributor', {'a2' : 'a2'}, True, distributor_id='dist-2')
        self.distributor_manager.add_distributor('repo-b', 'mock-distributor', {'b' : 'b'}, True)
        self.distributor_manager.add_distributor('repo-c', 'mock-distributor-2', {}, True)

        # Test
        repos = self.query_manager.find_with_distributor_type('mock-distributor')

        # Verify
        self.assertEqual(2, len(repos))

        repo_a = repos[0]
        self.assertEqual(repo_a['id'], 'repo-a')
        self.assertEqual(2, len(repo_a['distributors']))

        dist_1 = [d for d in repo_a['distributors'] if d['id'] == 'dist-1'][0]
        self.assertEqual(dist_1['distributor_type_id'], 'mock-distributor')
        self.assertEqual(dist_1['config'], {'a1' : 'a1'})

        dist_2 = [d for d in repo_a['distributors'] if d['id'] == 'dist-2'][0]
        self.assertEqual(dist_2['distributor_type_id'], 'mock-distributor')
        self.assertEqual(dist_2['config'], {'a2' : 'a2'})

        repo_b = repos[1]
        self.assertEqual(repo_b['id'], 'repo-b')
        self.assertEqual(1, len(repo_b['distributors']))
        self.assertEqual(repo_b['distributors'][0]['distributor_type_id'], 'mock-distributor')
        self.assertEqual(repo_b['distributors'][0]['config'], {'b' : 'b'})

    def test_find_with_distributor_type_no_matches(self):
        # Setup
        self.repo_manager.create_repo('repo-a')
        self.repo_manager.create_repo('repo-b')

        # Test
        repos = self.query_manager.find_with_distributor_type('mock-distributor')

        # Verify
        self.assertEqual(0, len(repos))
        self.assertTrue(isinstance(repos, list))

    def test_find_with_importer_type(self):
        # Setup
        self.repo_manager.create_repo('repo-a')
        self.repo_manager.create_repo('repo-b')
        self.repo_manager.create_repo('repo-c')
        self.repo_manager.create_repo('repo-d')

        self.importer_manager.set_importer('repo-a', 'mock-importer', {'a' : 'a'})

        # Test
        repos = self.query_manager.find_with_importer_type('mock-importer')

        # Verify
        self.assertEqual(1, len(repos))

        repo_a = repos[0]
        self.assertEqual(repo_a['id'], 'repo-a')
        self.assertEqual(1, len(repo_a['importers']))
        self.assertEqual(repo_a['importers'][0]['importer_type_id'], 'mock-importer')
        self.assertEqual(repo_a['importers'][0]['config'], {'a' : 'a'})

    def test_find_with_importer_type_no_matches(self):
        # Setup
        self.repo_manager.create_repo('repo-a')
        self.repo_manager.create_repo('repo-b')

        # Test
        repos = self.query_manager.find_with_importer_type('mock-importer')

        # Verify
        self.assertEqual(0, len(repos))
        self.assertTrue(isinstance(repos, list))

    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_find_by_criteria(self, mock_query):
        criteria = Criteria()
        self.query_manager.find_by_criteria(criteria)
        mock_query.assert_called_once_with(criteria)