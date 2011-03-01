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

import pulp.server.agent
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.repo import RepoApi
from pulp.server.pexceptions import PulpException
import testutil

# -- mocks ---------------------------------------------------------------------------

class MockRepoProxy(object):

    def __init__(self):
        self.bind_data = None
        self.unbind_repo_id = None

    def bind(self, bind_data):
        self.bind_data = bind_data

    def unbind(self, repo_id):
        self.unbind_repo_id = repo_id

    def clean(self):
        '''
        Removes all state from the mock. Meant to be run between test runs to ensure a
        common starting point.
        '''
        self.bind_data = None
        self.unbind_repo_id = None

MOCK_REPO_PROXY = MockRepoProxy()

def retrieve_mock_repo_proxy(uuid, **options):
    return MOCK_REPO_PROXY

pulp.server.agent.retrieve_repo_proxy = retrieve_mock_repo_proxy

# -- test cases ---------------------------------------------------------------------------

class TestConsumerApi(unittest.TestCase):

    def clean(self):
        '''
        Removes any entities written to the database in all used APIs.
        '''
        self.repo_api.clean()
        self.consumer_api.clean()

        MOCK_REPO_PROXY.clean()
        
        testutil.common_cleanup()

    def setUp(self):
        self.config = testutil.load_test_config()

        self.repo_api = RepoApi()
        self.consumer_api = ConsumerApi()

        self.clean()

    def tearDown(self):
        self.clean()

    # -- bind test cases -----------------------------------------------------------------

    def test_bind(self):
        '''
        Tests the happy path of binding a consumer to a repo.
        '''

        # Setup
        self.repo_api.create('test-repo', 'Test Repo', 'noarch')
        self.consumer_api.create('test-consumer', None)

        # Test
        returned_bind_data = self.consumer_api.bind('test-consumer', 'test-repo')

        # Verify

        #   Database
        consumer = self.consumer_api.consumer('test-consumer')
        self.assertTrue(consumer is not None)
        self.assertTrue('test-repo' in consumer['repoids'])

        #   Bind data validation
        def verify_bind_data(bind_data):
            self.assertTrue(bind_data is not None)

            # Verify repo
            data_repo = bind_data['repo']
            self.assertTrue(data_repo is not None)
            self.assertEqual(data_repo['id'], 'test-repo')
            self.assertEqual(data_repo['name'], 'Test Repo')

            # Verify repo URLs
            host_urls = bind_data['host_urls']
            self.assertTrue(host_urls is not None)
            self.assertEqual(1, len(host_urls))
            self.assertEqual('https://localhost/pulp/repos/test-repo', host_urls[0])

            # Verify key URLs
            key_urls = bind_data['key_urls']
            self.assertTrue(key_urls is not None)
            self.assertEqual(0, len(key_urls))

        #   Returned bind data
        verify_bind_data(returned_bind_data)

        #   Messaging bind data
        verify_bind_data(MOCK_REPO_PROXY.bind_data)

    def test_bind_with_keys(self):
        '''
        Tests that binding to a repo with GPG keys returns the URL to those keys as
        part of the bind data.
        '''

        # Setup
        self.repo_api.create('test-repo', 'Test Repo', 'noarch')
        keyA = ('key-1', 'key-1-content')
        keyB = ('key-2', 'key-2-content')
        keylist = [keyA, keyB]
        self.repo_api.addkeys('test-repo', keylist)

        self.consumer_api.create('test-consumer', None)

        # Test
        returned_bind_data = self.consumer_api.bind('test-consumer', 'test-repo')

        # Verify

        def verify_key_bind_data(bind_data):
            key_urls = bind_data['key_urls']
            self.assertTrue(key_urls is not None)
            self.assertEqual(2, len(key_urls))

            self.assertTrue('https://localhost/pulp/gpg/test-repo/key-1' in key_urls)
            self.assertTrue('https://localhost/pulp/gpg/test-repo/key-2' in key_urls)

        #   Returned bind data
        verify_key_bind_data(returned_bind_data)

        #   Messaging bind data
        verify_key_bind_data(MOCK_REPO_PROXY.bind_data)


    def test_bind_invalid_consumer(self):
        '''
        Tests that an exception is properly thrown when the consumer doesn't exist.
        '''

        # Setup
        self.repo_api.create('test-repo', 'Test Repo', 'noarch')

        # Test
        self.assertRaises(PulpException, self.consumer_api.bind, 'fake-consumer', 'test-repo')

        # Verify
        #   Make sure no messages were sent over the bus
        self.assertTrue(MOCK_REPO_PROXY.bind_data is None)

    def test_bind_invalid_repo(self):
        '''
        Tests that an exception is properly thrown when the repo doesn't exist.
        '''

        # Setup
        self.consumer_api.create('test-consumer', None)

        # Test
        self.assertRaises(PulpException, self.consumer_api.bind, 'test-consumer', 'fake-repo')

        # Verify
        #   Make sure no messages were sent over the bus
        self.assertTrue(MOCK_REPO_PROXY.bind_data is None)
                
    # -- unbind test cases -------------------------------------------------------------------

    def test_unbind(self):
        '''
        Tests the happy path of unbinding a repo that is bound to the consumer.
        '''

        # Setup
        self.consumer_api.create('test-consumer', None)
        self.repo_api.create('test-repo', 'Test Repo', 'noarch')

        self.consumer_api.bind('test-consumer', 'test-repo')

        consumer = self.consumer_api.consumer('test-consumer')
        self.assertTrue('test-repo' in consumer['repoids'])

        # Test
        self.consumer_api.unbind('test-consumer', 'test-repo')

        # Verify
        consumer = self.consumer_api.consumer('test-consumer')
        self.assertTrue('test-repo' not in consumer['repoids'])

        self.assertEqual(MOCK_REPO_PROXY.unbind_repo_id, 'test-repo')

    def test_unbind_existing_repos(self):
        '''
        Tests that calling unbind when there are other repos bound does not affect
        those bindings.
        '''

        # Setup
        self.consumer_api.create('test-consumer', None)
        self.repo_api.create('test-repo-1', 'Test Repo', 'noarch')
        self.repo_api.create('test-repo-2', 'Test Repo', 'noarch')

        self.consumer_api.bind('test-consumer', 'test-repo-1')
        self.consumer_api.bind('test-consumer', 'test-repo-2')

        consumer = self.consumer_api.consumer('test-consumer')
        self.assertTrue('test-repo-1' in consumer['repoids'])
        self.assertTrue('test-repo-2' in consumer['repoids'])

        # Test
        self.consumer_api.unbind('test-consumer', 'test-repo-1')

        # Verify
        consumer = self.consumer_api.consumer('test-consumer')
        self.assertTrue('test-repo-1' not in consumer['repoids'])
        self.assertTrue('test-repo-2' in consumer['repoids'])

        self.assertEqual(MOCK_REPO_PROXY.unbind_repo_id, 'test-repo-1')

    def test_unbind_repo_not_bound(self):
        '''
        Tests that calling unbind on a repo that isn't bound acts as a no-op.
        '''

        # Setup
        self.consumer_api.create('test-consumer', None)
        self.repo_api.create('test-repo', 'Test Repo', 'noarch')

        # Test
        self.consumer_api.unbind('test-consumer', 'test-repo') # should not error

        # Verify
        #   Make sure no messages were sent over the bus
        self.assertTrue(MOCK_REPO_PROXY.unbind_repo_id is None)

    def test_unbind_invalid_consumer(self):
        '''
        Tests that calling unbind on a consumer that does not exist throws an error
        correctly.
        '''

        # Setup
        self.repo_api.create('test-repo', 'Test Repo', 'noarch')

        # Test
        self.assertRaises(PulpException, self.consumer_api.unbind, 'fake-consumer', 'test-repo')

        # Verify
        #   Make sure no messages were sent over the bus
        self.assertTrue(MOCK_REPO_PROXY.unbind_repo_id is None)
