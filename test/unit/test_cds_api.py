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
import time
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.server.api.cds import CdsApi
from pulp.server.api.cds_history import CdsHistoryApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.consumer_history import ConsumerHistoryApi
from pulp.server.api.repo import RepoApi
from pulp.server.cds.dispatcher import CdsTimeoutException
import pulp.server.cds.round_robin as round_robin
from pulp.server.db.model import CDSHistoryEventType, CDSRepoRoundRobin
from pulp.server.pexceptions import PulpException

from mocks import MockRepoProxyFactory
import testutil

# -- mocks -------------------------------------------------------------------------------

class MockCdsDispatcher(object):

    # Strings to add to the call_log so the test can verify that the correct calls
    # were made into the dispatcher
    INIT = 'init'
    SYNC = 'sync'

    def __init__(self, error_to_throw=None):
        '''
        Creates a new mock dispatcher that should be added to any CDS classes that
        make dispatcher calls (likely just the CdsApi class). All method calls on
        this object will be added to a running list called call_log. All entries in
        that list will follow the format provided by the call_log_message method.

        @param error_to_throw: if this is specified, any calls into this object will
                               throw the given error, otherwise the method will appear
                               to execute correctly; defaults to None
        @type  error_to_throw: L{Exception} or subclass
        '''
        self.error_to_throw = error_to_throw
        self.call_log = []

        # Stores the values that were passed into calls
        self.cds = None
        self.repos = None

    def init_cds(self, cds):
        self.call_log.append(self.call_log_message(MockCdsDispatcher.INIT, cds))
        self.cds = cds

        if self.error_to_throw is not None:
            raise self.error_to_throw

    def sync(self, cds, repos):
        self.call_log.append(self.call_log_message(MockCdsDispatcher.SYNC, cds))
        self.cds = cds
        self.repos = repos

        if self.error_to_throw is not None:
            raise self.error_to_throw

    def call_log_message(self, type, cds):
        '''
        Generates the message that will be logged to call_log when a method is invoked.
        This is largely to ease the comparison between what's put in the log against
        what the test case wants to verify.

        @param type: string identifying the method called; will be a constant in this class
        @type  type: string

        @param cds: CDS domain object that was passed to the invoked method
        @type  cds: L{CDS}
        '''
        return type + '-' + cds['hostname']

    def clear(self):
        '''
        Resets the state of the dispatcher to as if it were never called.
        '''
        self.cds = None
        self.repos = None
        self.call_log = []

# -- test cases --------------------------------------------------------------------------------------

class TestCdsApi(unittest.TestCase):

    def clean(self):
        self.cds_history_api.clean()
        self.cds_api.clean()
        self.repo_api.clean()
        self.consumer_api.clean()
        self.consumer_history_api.clean()

        # Flush the assignment algorithm cache
        CDSRepoRoundRobin.get_collection().remove()

        self.dispatcher.clear()

    def setUp(self):
        self.config = testutil.load_test_config()

        self.dispatcher = MockCdsDispatcher()
        self.cds_api = CdsApi()
        self.cds_api.dispatcher = self.dispatcher

        self.cds_history_api = CdsHistoryApi()
        self.repo_api = RepoApi()
        self.consumer_api = ConsumerApi()
        self.consumer_history_api = ConsumerHistoryApi()

        self.proxy_factory = MockRepoProxyFactory()
        self.proxy_factory.activate()

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

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(history))
        self.assertEqual(CDSHistoryEventType.REGISTERED, history[0]['type_name'])

        self.assertEqual(1, len(self.dispatcher.call_log))
        self.assertEqual(self.dispatcher.call_log[0], self.dispatcher.call_log_message(MockCdsDispatcher.INIT, cds))

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

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(history))
        self.assertEqual(CDSHistoryEventType.REGISTERED, history[0]['type_name'])

        self.assertEqual(1, len(self.dispatcher.call_log))
        self.assertEqual(self.dispatcher.call_log[0], self.dispatcher.call_log_message(MockCdsDispatcher.INIT, cds))

    def test_register_no_hostname(self):
        '''
        Tests the error condition where register is called without a hostname.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_api.register, None)

        # Verify
        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(0, len(history))

        self.assertEqual(0, len(self.dispatcher.call_log))

    def test_register_already_exists(self):
        '''
        Tests the error condition where a CDS already exists with the given hostname.
        '''

        # Setup
        self.cds_api.register('cds.example.com')

        # Test
        self.assertRaises(PulpException, self.cds_api.register, 'cds.example.com')

        # Verify
        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(history)) # from the first register call, not the second

        self.assertEqual(1, len(self.dispatcher.call_log)) # only from the original register

    def test_register_init_error(self):
        '''
        Tests attempting to register a CDS when the init call to the CDS fails.
        '''

        # Setup
        self.dispatcher.error_to_throw = CdsTimeoutException(None)

        # Test
        self.assertRaises(PulpException, self.cds_api.register, 'cds.example.com')

        # Verify
        self.assertTrue(self.cds_api.cds('cds.example.com') is None)
        
    def test_unregister(self):
        '''
        Tests the basic case where unregister is successful.
        '''

        # Setup
        self.cds_api.register('cds.example.com')
        time.sleep(1) # make sure the timestamps will be different
        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds is not None)

        # Test
        self.cds_api.unregister('cds.example.com')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds is None)

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(2, len(history))
        self.assertEqual(CDSHistoryEventType.UNREGISTERED, history[0]['type_name'])
        self.assertEqual(CDSHistoryEventType.REGISTERED, history[1]['type_name'])

    def test_unregister_no_hostname(self):
        '''
        Tests the error condition where unregister is called without a hostname.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_api.unregister, None)

        # Verify
        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(0, len(history))

    def test_unregister_invalid_hostname(self):
        '''
        Tests the error condition where the given hostname does not correspond to an existing
        CDS.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_api.unregister, 'foo.example.com')

        # Verify
        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(0, len(history))

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
        time.sleep(1) # make sure the timestamps will be different

        # Test
        self.cds_api.associate_repo('cds.example.com', 'cds-test-repo')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertEqual(1, len(cds['repo_ids']))

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(2, len(history)) # register and associate
        self.assertEqual(CDSHistoryEventType.REPO_ASSOCIATED, history[0]['type_name'])
        self.assertEqual(CDSHistoryEventType.REGISTERED, history[1]['type_name'])

        host_urls = round_robin.generate_cds_urls('cds-test-repo')
        self.assertEqual(1, len(host_urls))
        self.assertEqual('cds.example.com', host_urls[0])

    def test_associate_repo_already_associated(self):
        '''
        Tests that associating an already associated repo doesn't throw an error.
        '''

        # Setup
        self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')
        self.cds_api.register('cds.example.com')
        time.sleep(1) # make sure the timestamps will be different

        self.cds_api.associate_repo('cds.example.com', 'cds-test-repo')
        time.sleep(1) # make sure the timestamps will be different
        cds = self.cds_api.cds('cds.example.com')
        self.assertEqual(1, len(cds['repo_ids']))

        # Test
        self.cds_api.associate_repo('cds.example.com', 'cds-test-repo')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertEqual(1, len(cds['repo_ids']))

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(2, len(history)) # register and only first associate
        self.assertEqual(CDSHistoryEventType.REPO_ASSOCIATED, history[0]['type_name'])
        self.assertEqual(CDSHistoryEventType.REGISTERED, history[1]['type_name'])

        host_urls = round_robin.generate_cds_urls('cds-test-repo')
        self.assertEqual(1, len(host_urls))
        self.assertEqual('cds.example.com', host_urls[0])
        
    def test_associate_repo_invalid_cds(self):
        '''
        Tests that associating a repo with an invalid CDS hostname throws an error.
        '''

        # Setup
        self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')

        # Test
        self.assertRaises(PulpException, self.cds_api.associate_repo, 'foo.example.com', 'cds-test-repo')

        # Verify
        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(0, len(history))

    def test_associate_repo_invalid_repo(self):
        '''
        Tests that associating an invalid repo throws an error.
        '''

        # Setup
        self.cds_api.register('cds.example.com')

        # Test
        self.assertRaises(PulpException, self.cds_api.associate_repo, 'cds.example.com', 'foo')

        # Verify
        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(history)) # for the register

    def test_unassociate(self):
        '''
        Tests the unassociate repo call under normal conditions: the CDS exists and has the
        repo already associated.
        '''

        # Setup
        self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')
        self.cds_api.register('cds.example.com')
        time.sleep(1) # make sure the timestamps will be different

        self.cds_api.associate_repo('cds.example.com', 'cds-test-repo')
        time.sleep(1) # make sure the timestamps will be different
        cds = self.cds_api.cds('cds.example.com')
        self.assertEqual(1, len(cds['repo_ids']))

        # Test
        self.cds_api.unassociate_repo('cds.example.com', 'cds-test-repo')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertEqual(0, len(cds['repo_ids']))

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(3, len(history)) # register, associate. unassociate
        self.assertEqual(CDSHistoryEventType.REPO_UNASSOCIATED, history[0]['type_name'])
        self.assertEqual(CDSHistoryEventType.REPO_ASSOCIATED, history[1]['type_name'])
        self.assertEqual(CDSHistoryEventType.REGISTERED, history[2]['type_name'])

        host_urls = round_robin.generate_cds_urls('cds-test-repo')
        self.assertEqual(0, len(host_urls))

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

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(history)) # register only

    def test_unassociate_invalid_cds(self):
        '''
        Tests the call to unassociate throws an error when there is no CDS with the given
        hostname.
        '''

        # Setup
        self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')

        # Test
        self.assertRaises(PulpException, self.cds_api.unassociate_repo, 'foo.example.com', 'cds-test-repo')

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(0, len(history))

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

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(history)) # register only
        
    def test_unassociate_all_from_repo(self):
        '''
        Tests the unassociate_all_from_repo call under normal conditions: there is at least
        one CDS associated with the given repo.
        '''

        # Setup
        self.cds_api.register('cds-01.example.com')
        self.cds_api.register('cds-02.example.com')
        self.cds_api.register('cds-03.example.com')

        time.sleep(1) # make sure the timestamps will be different

        self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')

        self.cds_api.associate_repo('cds-01.example.com', 'cds-test-repo')
        self.cds_api.associate_repo('cds-02.example.com', 'cds-test-repo')
        self.cds_api.associate_repo('cds-03.example.com', 'cds-test-repo')

        time.sleep(1) # make sure the timestamps will be different

        self.assertEqual(1, len(self.cds_api.cds('cds-01.example.com')['repo_ids']))
        self.assertEqual(1, len(self.cds_api.cds('cds-02.example.com')['repo_ids']))
        self.assertEqual(1, len(self.cds_api.cds('cds-03.example.com')['repo_ids']))

        # Test
        self.cds_api.unassociate_all_from_repo('cds-test-repo')
        time.sleep(1) # make sure the timestamps will be different

        # Verify
        self.assertEqual(0, len(self.cds_api.cds('cds-01.example.com')['repo_ids']))
        self.assertEqual(0, len(self.cds_api.cds('cds-02.example.com')['repo_ids']))
        self.assertEqual(0, len(self.cds_api.cds('cds-03.example.com')['repo_ids']))

        history = self.cds_history_api.query(cds_hostname='cds-01.example.com')
        self.assertEqual(3, len(history)) # register, associate. unassociate
        self.assertEqual(CDSHistoryEventType.REPO_UNASSOCIATED, history[0]['type_name'])
        self.assertEqual(CDSHistoryEventType.REPO_ASSOCIATED, history[1]['type_name'])
        self.assertEqual(CDSHistoryEventType.REGISTERED, history[2]['type_name'])
    
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

    def test_sync(self):
        '''
        Tests sync under normal circumstances.
        '''

        # Setup
        repo = self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')
        self.cds_api.register('cds.example.com')
        self.cds_api.associate_repo('cds.example.com', repo['id'])

        #   Clear the dispatcher from what was called during register
        self.dispatcher.clear()

        # Test
        self.cds_api.cds_sync('cds.example.com')

        # Verify
        self.assertEqual(1, len(self.dispatcher.call_log)) # the call to sync
        self.assertEqual('cds.example.com', self.dispatcher.cds['hostname'])
        self.assertEqual(1, len(self.dispatcher.repos))
        self.assertEqual('cds-test-repo', self.dispatcher.repos[0]['id'])

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(4, len(history))
        # self.assertEqual(CDSHistoryEventType.SYNC_FINISHED, history[0]['type_name'])
        # self.assertEqual(CDSHistoryEventType.SYNC_STARTED, history[1]['type_name'])

        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds['last_sync'] is not None)

    def test_sync_invalid_cds(self):
        '''
        Tests attempting to sync a CDS that doesn't exist.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_api.cds_sync, 'foo.example.com')

    def test_sync_error(self):
        '''
        Tests sync when an error occurs. The error should be logged in the CDS history
        as well as returned to the caller.
        '''

        # Setup
        repo = self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')
        self.cds_api.register('cds.example.com')
        self.cds_api.associate_repo('cds.example.com', repo['id'])

        #   Clear the dispatcher from what was called during register
        self.dispatcher.clear()

        #   Configure the dispatcher to throw an error
        self.dispatcher.error_to_throw = CdsTimeoutException(None)

        # Test
        self.assertRaises(PulpException, self.cds_api.cds_sync, 'cds.example.com')

        # Verify
        self.assertEqual(1, len(self.dispatcher.call_log)) # the call to sync
        self.assertEqual('cds.example.com', self.dispatcher.cds['hostname'])
        self.assertEqual(1, len(self.dispatcher.repos))
        self.assertEqual('cds-test-repo', self.dispatcher.repos[0]['id'])

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(4, len(history))
        # self.assertEqual(CDSHistoryEventType.SYNC_FINISHED, history[0]['type_name'])
        # self.assertEqual(CDSHistoryEventType.SYNC_STARTED, history[1]['type_name'])

        #   Verify the history event contains the exception
        # self.assertTrue(history[0]['details']['error'] is not None)

        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds['last_sync'] is not None)

    def test_cds_with_repo(self):
        '''
        Tests searching for CDS instances by a repo ID when there is at least one association
        to the given repo.
        '''

        # Setup
        repo = self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')
        self.cds_api.register('cds1.example.com')
        self.cds_api.register('cds2.example.com')
        self.cds_api.register('cds3.example.com')

        self.cds_api.associate_repo('cds1.example.com', repo['id'])
        self.cds_api.associate_repo('cds2.example.com', repo['id'])

        # Test
        results = self.cds_api.cds_with_repo(repo['id'])

        self.assertEqual(2, len(results))
        for cds in results:
            self.assertTrue(cds['hostname'] in 'cds1.example.com cds2.example.com'.split())

    def test_cds_with_repo_no_cds(self):
        '''
        Tests searching for CDS instances associated with a valid repo but there are no
        instances associated.
        '''

        # Setup
        repo = self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')
        self.cds_api.register('cds1.example.com')
        self.cds_api.register('cds2.example.com')
        self.cds_api.register('cds3.example.com')

        # Test
        results = self.cds_api.cds_with_repo(repo['id'])

        # Verify
        self.assertEqual(0, len(results))

    def test_cds_with_repo_invalid_repo(self):
        '''
        Tests that searching for associated CDS instances with a repo that doesn't exist
        doesn't throw an error.
        '''

        # Setup
        self.cds_api.register('cds1.example.com')
        self.cds_api.register('cds2.example.com')
        self.cds_api.register('cds3.example.com')

        # Test
        results = self.cds_api.cds_with_repo('foo')

        # Verify
        self.assertEqual(0, len(results))

    def test_delete_repo_with_associated(self):
        '''
        Tests the RepoApi call to delete a repo that is currently associated with at least one CDS.
        The delete should not be allowed and the user informed to explicitly
        unassociate the repo from all CDS instances first.
        '''

        # Setup
        repo = self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'x86_64')
        self.cds_api.register('cds1.example.com')

        self.cds_api.associate_repo('cds1.example.com', repo['id'])

        # Test
        self.assertRaises(PulpException, self.repo_api.delete, repo['id'])

    def test_redistribute(self):
        '''
        Tests redistribute with multiple consumers bound to the repo and multiple CDS instances
        hosting it.
        '''

        # Setup
        self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'noarch')

        self.cds_api.register('cds1')
        self.cds_api.register('cds2')

        self.cds_api.associate_repo('cds1', 'cds-test-repo')
        self.cds_api.associate_repo('cds2', 'cds-test-repo')

        self.consumer_api.create('consumer1', None)
        self.consumer_api.create('consumer2', None)
        self.consumer_api.create('consumer3', None)

        self.consumer_api.bind('consumer1', 'cds-test-repo')
        self.consumer_api.bind('consumer2', 'cds-test-repo')
        self.consumer_api.bind('consumer3', 'cds-test-repo')

        # Test
        self.cds_api.redistribute('cds-test-repo')

        # Verify
        self.assertEqual(3, len(self.proxy_factory.proxies))

        #   Make sure the correct data is in the update call
        for proxy in self.proxy_factory.proxies.values():
            self.assertEqual('cds-test-repo', proxy.update_calls[0][0])

            bind_data = proxy.update_calls[0][1]

            self.assertTrue('repo' in bind_data)
            self.assertTrue('host_urls' in bind_data)
            self.assertTrue('gpg_keys' in bind_data)

            self.assertTrue(bind_data['repo'] is None)
            self.assertEqual(3, len(bind_data['host_urls'])) # 2 CDS + pulp server
            self.assertEqual(None, bind_data['gpg_keys']) # don't send keys on redistribute

    def test_redistribute_no_consumers(self):
        '''
        Tests that calling redistribute when there are no consumers bound to the repo does not
        throw an error.
        '''

        # Setup
        repo = self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'noarch')

        # Test
        self.cds_api.redistribute(repo['id'])

        # Verify

        #   Make sure no attempts to send an update call across the bus were made
        self.assertEqual(0, len(self.proxy_factory.proxies))

    def test_redistribution_no_cds(self):
        '''
        Tests that calling redistribute when there are no CDS instances hosting the repo does
        not throw an error.
        '''

        # Setup
        repo = self.repo_api.create('cds-test-repo', 'CDS Test Repo', 'noarch')

        self.cds_api.register('cds1')
        self.cds_api.register('cds2')

        self.cds_api.associate_repo('cds1', 'cds-test-repo')
        self.cds_api.associate_repo('cds2', 'cds-test-repo')
                
        # Test
        self.cds_api.redistribute(repo['id'])

        # Verify

        #   Make sure no attempts to send an update call across the bus were made
        self.assertEqual(0, len(self.proxy_factory.proxies))
