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
import sys
import os
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import pulp.server.api.consumer_utils as utils
from pulp.server.db.model.resource import Consumer, Repo
import testutil

# -- test cases -------------------------------------------------------------------------

class TestConsumerUtils(unittest.TestCase):

    def clean(self):
        Consumer.get_collection().remove(safe=True)

    def setUp(self):
        self.clean()

    def tearDown(self):
        self.clean()

    def test_consumers_bound_to_repo(self):
        '''
        Tests retrieving consumers bound to a repo when there are actually consumers for
        the repo.
        '''

        # Setup
        db = Consumer.get_collection()

        c1 = Consumer('c1', None)
        c1.repoids = ['repo1']
        db.save(c1)

        c2 = Consumer('c2', None)
        c2.repoids = ['repo1', 'repo2']
        db.save(c2)

        c3 = Consumer('c3', None)
        c3.repoids = ['repo2']
        db.save(c3)

        c4 = Consumer('c4', None)
        db.save(c4)

        # Test
        consumers = utils.consumers_bound_to_repo('repo1')

        # Verify
        self.assertTrue(consumers is not None)
        self.assertEqual(1, len(consumers))

        for c in consumers:
            self.assertTrue(c['id'] in ['c1', 'c2'])

    def test_consumers_bound_none_bound(self):
        '''
        Tests the correct return result is received when requesting consumers bound to a repo when
        there are no consumers bound.
        '''

        # Test
        consumers = utils.consumers_bound_to_repo('empty-repo')

        # Verify
        self.assertTrue(consumers is not None)
        self.assertEqual(0, len(consumers))

    def test_build_bind_data(self):
        '''
        Tests that assembling the data needed for a bind correctly includes all supplied data.
        '''

        # Setup
        repo = Repo('repo1', 'Repo 1', 'noarch')
        Repo.get_collection().save(repo)

        # Test
        bind_data = utils.build_bind_data(repo, ['cds1', 'cds2'], ['key1'])

        # Verify
        self.assertTrue(bind_data is not None)

        self.assertTrue('repo' in bind_data)
        self.assertTrue('host_urls' in bind_data)
        self.assertTrue('key_urls' in bind_data)

        data_repo = bind_data['repo']
        self.assertTrue(data_repo is not None)
        self.assertEqual(data_repo['id'], 'repo1')
        self.assertEqual(data_repo['name'], 'Repo 1')
        self.assertEqual(data_repo['arch'], 'noarch')

        data_hosts = bind_data['host_urls']
        self.assertTrue(data_hosts is not None)
        self.assertEqual(3, len(data_hosts)) # 2 CDS + pulp server

        data_keys = bind_data['key_urls']
        self.assertTrue(data_keys is not None)
        self.assertEqual(1, len(data_keys))

    def test_build_bind_data_no_hostnames_or_keys(self):
        '''
        Tests that pass in no hostnames and/or keys does not error and properly sets the values in
        the returned data.
        '''