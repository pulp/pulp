#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

# Python
import os
import sys
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"

sys.path.insert(0, srcdir)
commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'

sys.path.insert(0, commondir)

from pulp.server.api.cds import CdsApi
from pulp.server.api.cds_history import CdsHistoryApi
from pulp.server.api.repo import RepoApi
from pulp.server.pexceptions import PulpException

import testutil

class TestCdsApi(unittest.TestCase):

    def clean(self):
        self.repo_api.clean()
        self.cds_history_api.clean()
        self.cds_api.clean()

    def setUp(self):
        self.config = testutil.load_test_config()
        self.cds_api = CdsApi()
        self.cds_history_api = CdsHistoryApi()
        self.repo_api = RepoApi()
        self.clean()

    def tearDown(self):
        self.clean()
        testutil.common_cleanup()

    def test_register_simple_attributes(self):
        '''
        Tests the register call with only the required arguments.
        '''

        # Test
        self.cds_api.register('cds.example.com')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds is not None)
        self.assertEqual(cds['hostname'], 'cds.example.com')
        self.assertEqual(cds['name'], 'cds.example.com')
        self.assertEqual(cds['description'], None)

    def test_register_full_attributes(self):
        '''
        Tests the register call specifying a value for all optional arguments.
        '''

        # Test
        self.cds_api.register('cds.example.com', name='Test CDS', description='Test CDS Description')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds is not None)

        self.assertEqual(cds['hostname'], 'cds.example.com')
        self.assertEqual(cds['name'], 'Test CDS')
        self.assertEqual(cds['description'], 'Test CDS Description')

    def test_register_no_hostname(self):
        '''
        Tests the error condition where register is called without a hostname.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_api.register, None)

    def test_register_already_exists(self):
        '''
        Tests the error condition where a CDS already exists with the given hostname.
        '''

        # Setup
        self.cds_api.register('cds.example.com')

        # Test
        self.assertRaises(PulpException, self.cds_api.register, 'cds.example.com')

    def test_unregister(self):
        '''
        Tests the basic case where unregister is successful.
        '''

        # Setup
        self.cds_api.register('cds.example.com')
        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds is not None)

        # Test
        self.cds_api.unregister('cds.example.com')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds is None)

    def test_unregister_no_hostname(self):
        '''
        Tests the error condition where unregister is called without a hostname.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_api.unregister, None)

    def test_unregister_invalid_hostname(self):
        '''
        Tests the error condition where the given hostname does not correspond to an existing
        CDS.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_api.unregister, 'foo.example.com')

    def test_cds_lookup_successful(self):
        '''
        Tests the CDS lookup when a CDS exists with the given hostname.
        '''

        # Setup
        self.cds_api.register('findme.example.com')

        # Test
        cds = self.cds_api.cds('findme.example.com')

        # Verify
        self.assertTrue(cds is not None)

    def test_cds_lookup_failed(self):
        '''
        Tests the CDS lookup when no CDS exists with the given hostname conforms to the
        API documentation.
        '''

        # Test
        cds = self.cds_api.cds('fake.example.com')

        # Verify
        self.assertTrue(cds is None)

    def test_list(self):
        '''
        Tests the basic case of listing a series of CDS instances.
        '''

        # Setup
        self.cds_api.register('cds01.example.com')
        self.cds_api.register('cds02.example.com')
        self.cds_api.register('cds03.example.com')
        self.cds_api.register('cds04.example.com')

        # Test
        all_cds = self.cds_api.list()

        # Verify
        self.assertEqual(4, len(all_cds))


    def test_list_no_cds_instances(self):
        '''
        Tests the edge case of listing CDS instances when there are none.
        '''

        # Test
        all_cds = self.cds_api.list()

        # Verify
        self.assertEqual(0, len(all_cds))

    def test_associate_repo(self):
        '''
        Tests the associate repo under normal conditions: the CDS and repo both exist and are
        not currently associated.
        '''

        # Setup
        self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')
        self.cds_api.register('cds.example.com')

        # Test
        self.cds_api.associate_repo('cds.example.com', 'cds-test-repo')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertEqual(1, len(cds['repo_ids']))

    def test_associate_repo_already_associated(self):
        '''
        Tests that associating an already associated repo doesn't throw an error.
        '''

        # Setup
        self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')
        self.cds_api.register('cds.example.com')

        self.cds_api.associate_repo('cds.example.com', 'cds-test-repo')
        cds = self.cds_api.cds('cds.example.com')
        self.assertEqual(1, len(cds['repo_ids']))

        # Test
        self.cds_api.associate_repo('cds.example.com', 'cds-test-repo')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertEqual(1, len(cds['repo_ids']))


    def test_associate_repo_invalid_cds(self):
        '''
        Tests that associating a repo with an invalid CDS hostname throws an error.
        '''

        # Setup
        self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')

        # Test
        self.assertRaises(PulpException, self.cds_api.associate_repo, 'foo.example.com', 'cds-test-repo')

    def test_associate_repo_invalid_repo(self):
        '''
        Tests that associating an invalid repo throws an error.
        '''

        # Setup
        self.cds_api.register('cds.example.com')

        # Test
        self.assertRaises(PulpException, self.cds_api.associate_repo, 'cds.example.com', 'foo')

    def test_unassociate(self):
        '''
        Tests the unassociate repo call under normal conditions: the CDS exists and has the
        repo already associated.
        '''

        # Setup
        self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')
        self.cds_api.register('cds.example.com')

        self.cds_api.associate_repo('cds.example.com', 'cds-test-repo')
        cds = self.cds_api.cds('cds.example.com')
        self.assertEqual(1, len(cds['repo_ids']))

        # Test
        self.cds_api.unassociate_repo('cds.example.com', 'cds-test-repo')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertEqual(0, len(cds['repo_ids']))

    def test_unassociate_not_associated(self):
        '''
        Tests that the unassociate call does not throw an error when unassociating a repo
        that isn't currently associated.
        '''

        # Setup
        self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')
        self.cds_api.register('cds.example.com')

        # Test
        self.cds_api.unassociate_repo('cds.example.com', 'cds-test-repo')

        # Verify
        # The unassociate call should not have thrown an error
        cds = self.cds_api.cds('cds.example.com')
        self.assertEqual(0, len(cds['repo_ids']))

    def test_unassociate_invalid_cds(self):
        '''
        Tests the call to unassociate throws an error when there is no CDS with the given
        hostname.
        '''

        # Setup
        self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')

        # Test
        self.assertRaises(PulpException, self.cds_api.unassociate_repo, 'foo.example.com', 'cds-test-repo')

    def test_unassociate_invalid_repo(self):
        '''
        Tests that unassociating an invalid repo does not throw an error. This is the odd
        case where for some reason the repo was deleted before it was unassociated. The net
        result will be the same from the call: the association does not exist after it runs.
        '''

        # Setup
        self.cds_api.register('cds.example.com')

        # Test
        self.cds_api.unassociate_repo('cds.example.com', 'foo')

        # Verify
        # The unassociate call should not have thrown an error
        cds = self.cds_api.cds('cds.example.com')
        self.assertEqual(0, len(cds['repo_ids']))

    def test_unassociate_all_from_repo(self):
        '''
        Tests the unassociate_all_from_repo call under normal conditions: there is at least
        one CDS associated with the given repo.
        '''

        # Setup
        self.cds_api.register('cds-01.example.com')
        self.cds_api.register('cds-02.example.com')
        self.cds_api.register('cds-03.example.com')

        self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')

        self.cds_api.associate_repo('cds-01.example.com', 'cds-test-repo')
        self.cds_api.associate_repo('cds-02.example.com', 'cds-test-repo')
        self.cds_api.associate_repo('cds-03.example.com', 'cds-test-repo')

        self.assertEqual(1, len(self.cds_api.cds('cds-01.example.com')['repo_ids']))
        self.assertEqual(1, len(self.cds_api.cds('cds-02.example.com')['repo_ids']))
        self.assertEqual(1, len(self.cds_api.cds('cds-03.example.com')['repo_ids']))

        # Test
        self.cds_api.unassociate_all_from_repo('cds-test-repo')

        # Verify
        self.assertEqual(0, len(self.cds_api.cds('cds-01.example.com')['repo_ids']))
        self.assertEqual(0, len(self.cds_api.cds('cds-02.example.com')['repo_ids']))
        self.assertEqual(0, len(self.cds_api.cds('cds-03.example.com')['repo_ids']))
    
    def test_unassociate_all_from_repo_no_cds(self):
        '''
        Tests that an error is not thrown when calling unassociate_all_from_repo while there
        are no CDS instances associated with it.
        '''

        # Setup
        self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')

        # Test
        self.cds_api.unassociate_all_from_repo('cds-test-repo')

        # Verify
        # The call above should not have thrown an error
    