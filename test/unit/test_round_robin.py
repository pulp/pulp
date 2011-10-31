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
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import pulp.server.cds.round_robin as round_robin
from pulp.server.db.model.cds import CDSRepoRoundRobin

# -- test cases ------------------------------------------------------------------------------

class TestRoundRobin(testutil.PulpAsyncTest):

    def clean(self):
        testutil.PulpAsyncTest.clean(self)
        for doomed in CDSRepoRoundRobin.get_collection().find():
            CDSRepoRoundRobin.get_collection().remove({'repo_id' : doomed['repo_id']}, safe=True)

    def test_three_cds_instances(self):
        '''
        Tests that the round robin algorithm correctly balances across three CDS instances.
        '''

        # Setup
        round_robin.add_cds_repo_association('cds1', 'repo1')
        round_robin.add_cds_repo_association('cds2', 'repo1')
        round_robin.add_cds_repo_association('cds3', 'repo1')

        # Test
        perm1 = round_robin.generate_cds_urls('repo1')
        perm2 = round_robin.generate_cds_urls('repo1')
        perm3 = round_robin.generate_cds_urls('repo1')
        perm4 = round_robin.generate_cds_urls('repo1')

        # Verify

        # Newly added CDS entries go at the front of the list, so since they were added 1, 2, 3, they
        # will be returned in reverse order
        self.assertEqual(perm1, ['cds3', 'cds2', 'cds1'])
        self.assertEqual(perm2, ['cds2', 'cds1', 'cds3'])
        self.assertEqual(perm3, ['cds1', 'cds3', 'cds2'])
        self.assertEqual(perm4, ['cds3', 'cds2', 'cds1'])

    def test_one_cds_instance(self):
        '''
        Tests that the round robin algorithm functions when there is only one CDS for a given repo.
        '''

        # Setup
        round_robin.add_cds_repo_association('cds1', 'repo1')

        # Test
        perm1 = round_robin.generate_cds_urls('repo1')
        perm2 = round_robin.generate_cds_urls('repo1')
        perm3 = round_robin.generate_cds_urls('repo1')

        # Verify

        # Newly added CDS entries go at the front of the list, so since they were added 1, 2, 3, they
        # will be returned in reverse order
        self.assertEqual(perm1, ['cds1'])
        self.assertEqual(perm2, ['cds1'])
        self.assertEqual(perm3, ['cds1'])
        

    def test_zero_cds_instances(self):
        '''
        Tests that the round robin algorithm functions when no CDS instances are available to serve
        a given repo.
        '''

        # Test
        perm = round_robin.generate_cds_urls('repo1')

        # Verify
        self.assertEqual([], perm)

    def test_add_new_cds_existing_association(self):
        '''
        Tests adding a new CDS instance to a repo that already has at least one CDS associated with it.
        '''

        # Setup
        round_robin.add_cds_repo_association('cds1', 'repo1')

        # Test
        added = round_robin.add_cds_repo_association('cds2', 'repo1')

        # Verify
        self.assertTrue(added)

        association = round_robin._find_association('repo1')
        self.assertTrue(association is not None)
        self.assertEqual(2, len(association['next_permutation']))
        self.assertEqual('cds2', association['next_permutation'][0])
        self.assertEqual('cds1', association['next_permutation'][1])

    def test_add_new_cds_new_association(self):
        '''
        Tests adding a new CDS instance for a repo that does not already have a CDS instance associated
        with it.
        '''

        # Test
        added = round_robin.add_cds_repo_association('cds1', 'repo1')

        # Verify
        self.assertTrue(added)

        association = round_robin._find_association('repo1')
        self.assertTrue(association is not None)
        self.assertEqual(1, len(association['next_permutation']))
        self.assertEqual('cds1', association['next_permutation'][0])

    def test_iterator_with_save(self):
        '''
        Tests that returning an iterator returns a properly configured and functioning iterator.
        '''

        # Setup
        round_robin.add_cds_repo_association('cds1', 'repo1')
        round_robin.add_cds_repo_association('cds2', 'repo1')
        round_robin.add_cds_repo_association('cds3', 'repo1')

        # Test
        iterator = round_robin.iterator('repo1')

        perm1 = iterator.next()
        perm2 = iterator.next()
        perm3 = iterator.next()
        perm4 = iterator.next()

        iterator.save()

        #   The following should generate the next in the sequence after the iterator was saved
        perm5 = round_robin.generate_cds_urls('repo1')

        # Verify

        # Newly added CDS entries go at the front of the list, so since they were added 1, 2, 3, they
        # will be returned in reverse order
        self.assertEqual(perm1, ['cds3', 'cds2', 'cds1'])
        self.assertEqual(perm2, ['cds2', 'cds1', 'cds3'])
        self.assertEqual(perm3, ['cds1', 'cds3', 'cds2'])
        self.assertEqual(perm4, ['cds3', 'cds2', 'cds1'])
        self.assertEqual(perm5, ['cds2', 'cds1', 'cds3']) # next sequence since iterator was saved

    def test_iterator_with_no_save(self):
        '''
        Tests that returning an iterator returns a properly configured and functioning iterator.
        '''

        # Setup
        round_robin.add_cds_repo_association('cds1', 'repo1')
        round_robin.add_cds_repo_association('cds2', 'repo1')
        round_robin.add_cds_repo_association('cds3', 'repo1')

        # Test
        iterator = round_robin.iterator('repo1')

        perm1 = iterator.next()
        perm2 = iterator.next()
        perm3 = iterator.next()
        perm4 = iterator.next()

        #   Since the iterator wasn't saved, this call should return the first in the sequence
        perm5 = round_robin.generate_cds_urls('repo1')

        # Verify

        # Newly added CDS entries go at the front of the list, so since they were added 1, 2, 3, they
        # will be returned in reverse order
        self.assertEqual(perm1, ['cds3', 'cds2', 'cds1'])
        self.assertEqual(perm2, ['cds2', 'cds1', 'cds3'])
        self.assertEqual(perm3, ['cds1', 'cds3', 'cds2'])
        self.assertEqual(perm4, ['cds3', 'cds2', 'cds1'])
        self.assertEqual(perm5, ['cds3', 'cds2', 'cds1']) # first since iterator wasn't saved

    def test_iterator_no_associations(self):
        '''
        Tests the correct return result when requesting the iterator with no associations.
        '''

        # Test
        iterator = round_robin.iterator('fake-repo')

        # Verify
        self.assertTrue(iterator is None)

    def test_add_existing_cds_to_association(self):
        '''
        Tests adding a CDS that has already been added.
        '''

        # Setup
        round_robin.add_cds_repo_association('cds1', 'repo1')

        # Test
        added = round_robin.add_cds_repo_association('cds1', 'repo1')

        # Verify
        self.assertTrue(not added)

        association = round_robin._find_association('repo1')
        self.assertEqual(1, len(association['next_permutation']))

    def test_remove_cds_existing_assoication(self):
        '''
        Tests removing a CDS from a previously associated repo.
        '''

        # Setup
        round_robin.add_cds_repo_association('cds1', 'repo1')

        # Test
        removed = round_robin.remove_cds_repo_association('cds1', 'repo1')

        # Verify
        self.assertTrue(removed)

        association = round_robin._find_association('repo1')
        self.assertTrue(association is None)

    def test_remove_unassociated_cds(self):
        '''
        Tests removing a CDS that was not assoicated with the repo.
        '''

        # Setup
        round_robin.add_cds_repo_association('cds1', 'repo1')

        # Test
        removed = round_robin.remove_cds_repo_association('fake-cds', 'repo1')

        # Verify
        self.assertTrue(not removed)

        association = round_robin._find_association('repo1')
        self.assertEqual(1, len(association['next_permutation']))

    def test_remove_no_associations_for_repo(self):
        '''
        Tests removing a CDS from a repo that has no assoications.        
        '''

        # Test
        removed = round_robin.remove_cds_repo_association('fake-cds', 'fake-repo')

        # Verify
        self.assertTrue(not removed)

    def test_multiple_repos(self):
        '''
        Tests having multiple repos in consideration for round robin calculation.
        The idea here is to make sure the IDs of the DB entities are correctly using
        the ID.
        '''

        # Setup
        round_robin.add_cds_repo_association('cds1', 'repo1')
        round_robin.add_cds_repo_association('cds2', 'repo1')

        round_robin.add_cds_repo_association('cds1', 'repo2')
        round_robin.add_cds_repo_association('cds2', 'repo2')
        round_robin.add_cds_repo_association('cds3', 'repo2')

        
