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
import mock_plugins

import pulp.server.consumer_utils as utils
from pulp.server.api.consumer import ConsumerApi
from pulp.server.managers.repo.cud import RepoManager
from pulp.server.managers.repo.distributor import RepoDistributorManager
from pulp.server.db.model.resource import Consumer
from pulp.server.db.model.gc_repository import Repo, RepoDistributor

# -- test cases -------------------------------------------------------------------------

class TestConsumerUtils(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)

        mock_plugins.install()

        # Create the manager instance to test
        self.repo_manager = RepoManager()
        self.repo_distributor_manager = RepoDistributorManager()

    def tearDown(self):
        testutil.PulpAsyncTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        testutil.PulpAsyncTest.clean(self)

        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()

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
        print(consumers)
        self.assertEqual(2, len(consumers))

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
        repo = self.repo_manager.create_repo('repo1', 'Repo 1')
        distributor_config = {'random' : 'config'}
        self.repo_distributor_manager.add_distributor('repo1', 'mock-distributor', distributor_config, True, distributor_id='test-distributor')

        # Test
        bind_data = utils.build_bind_data(repo, ['cds1', 'cds2'], ['key1'])

        # Verify
        self.assertTrue(bind_data is not None)

        self.assertTrue('repo' in bind_data)
        self.assertTrue('host_urls' in bind_data)
        self.assertTrue('gpg_keys' in bind_data)

        data_repo = bind_data['repo']
        self.assertTrue(data_repo is not None)
        self.assertEqual(data_repo['id'], 'repo1')
        self.assertEqual(data_repo['display_name'], 'Repo 1')

        data_hosts = bind_data['host_urls']
        self.assertTrue(data_hosts is not None)
        self.assertEqual(3, len(data_hosts)) # 2 CDS + pulp server

        data_keys = bind_data['gpg_keys']
        self.assertTrue(data_keys is not None)
        self.assertEqual(1, len(data_keys))

    def test_build_bind_data_no_hostnames_or_keys(self):
        '''
        Tests that pass in no hostnames and/or keys does not error and properly sets the values in
        the returned data.
        '''

        # Setup
        repo = self.repo_manager.create_repo('repo1', 'Repo 1')
        distributor_config = {'random' : 'config'}
        self.repo_distributor_manager.add_distributor('repo1', 'mock-distributor', distributor_config, True, distributor_id='test-distributor')

        # Test
        bind_data = utils.build_bind_data(repo, None, None)

        # Verify
        self.assertTrue(bind_data is not None)

        self.assertTrue('repo' in bind_data)
        self.assertTrue('host_urls' in bind_data)
        self.assertTrue('gpg_keys' in bind_data)

        self.assertEqual(1, len(bind_data['host_urls'])) # pulp server itself
        self.assertEqual(0, len(bind_data['gpg_keys']))
