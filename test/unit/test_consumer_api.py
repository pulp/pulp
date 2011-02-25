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

    def bind(self, bind_data):
        self.bind_data = bind_data

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
        testutil.common_cleanup()

    def setUp(self):
        self.config = testutil.load_test_config()

        self.repo_api = RepoApi()
        self.consumer_api = ConsumerApi()

        self.clean()

    def tearDown(self):
        self.clean()

    # -- bind test cases -----------------------------------------------------------------

    def test_consumer_bind(self):
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

    def test_consumer_bind_with_keys(self):
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


    def test_consumer_bind_invalid_consumer(self):
        '''
        Tests that an exception is properly thrown when the consumer doesn't exist.
        '''

        # Setup
        self.repo_api.create('test-repo', 'Test Repo', 'noarch')

        # Test
        self.assertRaises(PulpException, self.consumer_api.bind, 'fake-consumer', 'test-repo')

    def test_consumer_bind_invalid_repo(self):
        '''
        Tests that an exception is properly thrown when the repo doesn't exist.
        '''

        # Setup
        self.consumer_api.create('test-consumer', None)

        # Test
        self.assertRaises(PulpException, self.consumer_api.bind, 'test-consumer', 'fake-repo')