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

import mocks
from pulp.server.api.cds import CdsApi
from pulp.server.api.cds_history import CdsHistoryApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.consumer_history import ConsumerHistoryApi
from pulp.server.api.repo import RepoApi
from pulp.server.cds.dispatcher import CdsTimeoutException
import pulp.server.cds.round_robin as round_robin
from pulp.server.db.model import CDS, CDSHistoryEventType, CDSRepoRoundRobin
from pulp.server.pexceptions import PulpException
from pulp.server.agent import Agent, CdsAgent

import testutil


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
        mocks.reset()

    def setUp(self):
        mocks.install()
        self.config = testutil.load_test_config()
        self.cds_api = CdsApi()
        self.cds_history_api = CdsHistoryApi()
        self.repo_api = RepoApi()
        self.consumer_api = ConsumerApi()
        self.consumer_history_api = ConsumerHistoryApi()
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

        # Verify
        # initialize() and set_global_repo_auth() were send to agent.
        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        self.assertEqual(1, len(cdsplugin.initialize.history()))
        self.assertEqual(1, len(cdsplugin.set_global_repo_auth.history()))
        self.assertEqual(0, len(cdsplugin.update_group_membership.history()))
       
    def test_register_full_attributes(self):
        '''
        Tests the register call specifying a value for all optional arguments.
        '''

        # Test
        self.cds_api.register('cds.example.com', name='Test CDS', description='Test CDS Description', group_id='test-group')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds is not None)

        self.assertEqual(cds['hostname'], 'cds.example.com')
        self.assertEqual(cds['name'], 'Test CDS')
        self.assertEqual(cds['description'], 'Test CDS Description')
        self.assertEqual(cds['group_id'], 'test-group')

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(history))
        self.assertEqual(CDSHistoryEventType.REGISTERED, history[0]['type_name'])

        # Verify
        # initialize() and set_global_repo_auth() were send to agent.
        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        self.assertEqual(1, len(cdsplugin.initialize.history()))
        self.assertEqual(1, len(cdsplugin.set_global_repo_auth.history()))

        self.assertEqual(1, len(cdsplugin.update_group_membership.history()))
        self.assertEqual('test-group', cdsplugin.group_name)
        self.assertEqual(1, len(cdsplugin.member_hostnames))
        self.assertEqual('cds.example.com', cdsplugin.member_hostnames[0])

    def test_register_no_hostname(self):
        '''
        Tests the error condition where register is called without a hostname.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_api.register, None)

        # Verify
        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(0, len(history))

        # Verify
        # initialize() and set_global_repo_auth() were NOT send to agent.
        self.assertEqual(0, len(mocks.all()))

    def test_register_bad_group_id(self):
        '''
        Tests that an invalid group ID properly throws an exception.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_api.register, 'cds.example.com', group_id='@bad!')

        # Verify
        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(0, len(history))

    def test_register_already_exists(self):
        '''
        Tests the error condition where a CDS already exists with the given hostname.
        '''

        # Setup
        cds = self.cds_api.register('cds.example.com')

        # Test
        self.assertRaises(PulpException, self.cds_api.register, 'cds.example.com')

        # Verify
        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(history)) # from the first register call, not the second

        # Verify
        # initialize() and set_global_repo_auth() were sent once to agent.
        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        self.assertEqual(1, len(cdsplugin.initialize.history()))
        self.assertEqual(1, len(cdsplugin.set_global_repo_auth.history()))

    def test_register_init_error(self):
        '''
        Tests attempting to register a CDS when the init call to the CDS fails.
        '''

        # Setup
        cds = dict(hostname='cds.example.com')
        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        cdsplugin.initialize.push(CdsTimeoutException(None))

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
        uuid = CdsAgent.uuid(cds)

        # Test
        self.cds_api.unregister('cds.example.com')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds is None)

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(2, len(history))
        self.assertEqual(CDSHistoryEventType.UNREGISTERED, history[0]['type_name'])
        self.assertEqual(CDSHistoryEventType.REGISTERED, history[1]['type_name'])

        # Verify
        # release() was sent to agent.
        agent = Agent(uuid)
        cdsplugin = agent.cdsplugin()
        self.assertEqual(1, len(cdsplugin.release.history()))
        self.assertEqual(0, len(cdsplugin.update_group_membership.history()))

    def test_unregister_with_group(self):
        '''
        Tests that unregistering a CDS that belonged to the group triggers an
        update group message to other members.
        '''

        # Setup
        self.cds_api.register('cds1.example.com', group_id='test-multi-group')
        time.sleep(1)
        self.cds_api.register('cds2.example.com', group_id='test-multi-group')

        cds1 = self.cds_api.cds('cds1.example.com')
        uuid1 = CdsAgent.uuid(cds1)

        cds2 = self.cds_api.cds('cds2.example.com')
        uuid2 = CdsAgent.uuid(cds2)

        # Test
        self.cds_api.unregister('cds1.example.com')

        # Verify
        cdsplugin1 = Agent(uuid1).cdsplugin()
        self.assertEqual(2, len(cdsplugin1.update_group_membership.history())) # own register, cds2 register

        cdsplugin2 = Agent(uuid2).cdsplugin()
        self.assertEqual(2, len(cdsplugin2.update_group_membership.history())) # own register, cds1 unregister
        self.assertEqual('test-multi-group', cdsplugin2.group_name)
        self.assertEqual(1, len(cdsplugin2.member_hostnames)) # only itself after cds1 unregister
        self.assertEqual('cds2.example.com', cdsplugin2.member_hostnames[0])

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

    def test_update_cds(self):
        '''
        Tests that updating a CDS with valid data succeeds and correctly stores the changes.
        '''

        # Setup
        self.cds_api.register('update-cds', 'name-1', 'description-1', 'P1D', 'group-1')

        # Test
        delta = {
            'name'          : 'name-2',
            'description'   : 'description-2',
            'sync_schedule' : 'P2D',
            'group_id'      : 'group-2',
        }

        updated = self.cds_api.update('update-cds', delta)

        # Verify
        self.assertTrue(updated is not None)

        cds = self.cds_api.cds('update-cds')

        self.assertEqual('update-cds', cds['hostname'])
        self.assertEqual('name-2', cds['name'])
        self.assertEqual('description-2', cds['description'])
        self.assertEqual('P2D', cds['sync_schedule'])
        self.assertEqual('group-2', cds['group_id'])

        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        self.assertEqual(2, len(cdsplugin.update_group_membership.history())) # register, update
        self.assertEqual('group-2', cdsplugin.group_name)
        self.assertEqual(1, len(cdsplugin.member_hostnames))
        self.assertEqual('update-cds', cdsplugin.member_hostnames[0])

    def test_update_cds_bad_sync_schedule(self):
        '''
        Tests that specifying a bad sync schedule raises the proper error.
        '''

        # Setup
        self.cds_api.register('update-cds', 'name-1', 'description-1', 'P1D', 'group-1')

        # Test
        delta = {
            'name'          : 'name-2',
            'description'   : 'description-2',
            'sync_schedule' : 'spiderman',
            'group_id'      : 'group-2',
        }

        self.assertRaises(PulpException, self.cds_api.update, 'update-cds', delta)

    def test_update_cds_bad_group_id(self):
        '''
        Tests that specifying an invalid group ID raises the proper error.
        '''

        # Setup
        self.cds_api.register('update-cds', 'name-1', 'description-1', 'P1D', 'group-1')

        # Test
        delta = {
            'name'          : 'name-2',
            'description'   : 'description-2',
            'sync_schedule' : 'P2D',
            'group_id'      : 'b@d=id',
        }

        self.assertRaises(PulpException, self.cds_api.update, 'update-cds', delta)

    def test_update_remove_group(self):
        '''
        Tests removing a group ID is successful.
        '''

        # Setup
        self.cds_api.register('update-cds', 'name-1', 'description-1', 'P1D', 'group-1')

        # Test
        delta = {
            'group_id'      : None,
        }

        self.cds_api.update('update-cds', delta)

        # Verify
        cds = self.cds_api.cds('update-cds')

        self.assertTrue(cds['group_id'] is None)

        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        self.assertEqual(2, len(cdsplugin.update_group_membership.history())) # register, update
        self.assertEqual(None, cdsplugin.group_name)
        self.assertEqual(None, cdsplugin.member_hostnames)

    def test_update_add_group(self):
        '''
        Tests an update that adds a group to a CDS that did not previously have one.
        '''
        # Setup
        self.cds_api.register('update-cds')

        # Test
        delta = {
            'group_id'      : 'new-group',
        }

        self.cds_api.update('update-cds', delta)

        # Verify
        cds = self.cds_api.cds('update-cds')

        self.assertEqual('new-group', cds['group_id'])

        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        self.assertEqual(1, len(cdsplugin.update_group_membership.history())) # update only
        self.assertEqual('new-group', cdsplugin.group_name)
        self.assertEqual(1, len(cdsplugin.member_hostnames))
        self.assertEqual('update-cds', cdsplugin.member_hostnames[0])

    def test_update_change_group(self):
        '''
        Tests that changing a CDS' group will update both members of the old and new
        groups.
        '''

        # Setup
        cds_change = self.cds_api.register('update-cds-change-me', group_id='group-1')
        cds_1 = self.cds_api.register('update-cds-1', group_id='group-1')
        cds_2 = self.cds_api.register('update-cds-2', group_id='group-2')

        # Test
        delta = {
            'group_id'      : 'group-2',
        }

        self.cds_api.update('update-cds-change-me', delta)

        # Verify
        cdsplugin_change = CdsAgent(cds_change).cdsplugin()
        cdsplugin_1 = CdsAgent(cds_1).cdsplugin()
        cdsplugin_2 = CdsAgent(cds_2).cdsplugin()

        self.assertEqual(3, len(cdsplugin_change.update_group_membership.history())) # self register, cds_1 register, change event
        self.assertEqual(2, len(cdsplugin_1.update_group_membership.history())) # self register, change event
        self.assertEqual(2, len(cdsplugin_2.update_group_membership.history())) # self register, change event

        self.assertEqual('group-2', cdsplugin_change.group_name)
        self.assertEqual('group-1', cdsplugin_1.group_name)
        self.assertEqual('group-2', cdsplugin_2.group_name)

        self.assertEqual(2, len(cdsplugin_change.member_hostnames)) # change and cds 2
        self.assertEqual(1, len(cdsplugin_1.member_hostnames)) # cds 1
        self.assertEqual(2, len(cdsplugin_2.member_hostnames)) # change and cds 2

    def test_update_remove_sync_schedule(self):
        '''
        Tests that removing a sync schedule is successful.
        '''

        # Setup
        self.cds_api.register('update-cds', 'name-1', 'description-1', 'P1D', 'group-1')

        # Test
        delta = {
            'sync_schedule'      : None,
        }

        self.cds_api.update('update-cds', delta)

        # Verify
        cds = self.cds_api.cds('update-cds')

        self.assertTrue(cds['sync_schedule'] is None)

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
        cds = self.cds_api.cds('cds.example.com')
        self.cds_api.associate_repo('cds.example.com', repo['id'])

        # Test
        self.cds_api.cds_sync('cds.example.com')

        # Verify
        # sync() was sent to the agent with correct repoid.
        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        calls = cdsplugin.sync.history()
        self.assertEqual(1, len(calls))
        lastsync = calls[-1]
        syncargs = lastsync[0]
        self.assertEqual('cds-test-repo', syncargs[1][0]['id'])

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
        cds = self.cds_api.cds('cds.example.com')
        self.cds_api.associate_repo('cds.example.com', repo['id'])

        #   Configure the agent to throw an error
        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        cdsplugin.sync.push(CdsTimeoutException(None))

        # Test
        self.assertRaises(PulpException, self.cds_api.cds_sync, 'cds.example.com')

        # Verify
        calls = cdsplugin.sync.history()
        self.assertEqual(1, len(calls))
        lastsync = calls[-1]
        syncargs = lastsync[0]
        self.assertEqual('cds-test-repo', syncargs[1][0]['id'])

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
        repoid = 'cds-test-repo'
        hostname = 'cds1.example.com'
        repo = self.repo_api.create(repoid, 'CDS Test Repo', 'x86_64')
        self.cds_api.register(hostname)
        self.cds_api.associate_repo(hostname, repoid)
        # Delete
        succeeded, failed = self.repo_api.delete(repoid)
        # Verify
        self.assertTrue(hostname in succeeded)
        cds = self.cds_api.cds(hostname)
        self.assertEqual(0, len(cds['repo_ids']))


    def test_redistribute(self):
        '''
        Tests redistribute with multiple consumers bound to the repo and multiple CDS instances
        hosting it.
        '''

        CDS_HOSTNAMES = ('cds1', 'cds2')
        CONSUMERIDS = ('consumer1', 'consumer2', 'consumer3')
        REPOID = 'cds-test-repo'

        # Setup
        self.repo_api.create(REPOID, 'CDS Test Repo', 'noarch')

        # Create the CDS(s) and assocate with repo
        for hostname in CDS_HOSTNAMES:
            self.cds_api.register(hostname)
            self.cds_api.associate_repo(hostname, REPOID)

        # Create consumers and bind to repo
        for id in CONSUMERIDS:
            self.consumer_api.create(id, None)
            self.consumer_api.bind(id, REPOID)

        # Test
        self.cds_api.redistribute(REPOID)

        # Verify
        #   bind() were sent to the correct agent with the
        #   expected bind data
        for uuid in CONSUMERIDS:
            agent = Agent(uuid)
            repoproxy = agent.Repo()
            updatecalls = repoproxy.update.history()
            lastupdate = updatecalls[-1]
            repoid = lastupdate[0][0]
            bind_data = lastupdate[0][1]
            self.assertEqual(REPOID, repoid)
            self.assertTrue('repo' in bind_data)
            self.assertTrue('host_urls' in bind_data)
            self.assertTrue('gpg_keys' in bind_data)
            self.assertTrue(bind_data['repo'] is None)
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
        self.assertEqual(0, len(mocks.all()))

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

        # Clear the call history
        mocks.reset()
                
        # Test
        self.cds_api.redistribute(repo['id'])

        # Verify

        #   Make sure no attempts to send an update call across the bus were made
        self.assertEqual(0, len(mocks.all()))
