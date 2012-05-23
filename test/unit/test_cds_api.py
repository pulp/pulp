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
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil
import mocks

from pulp.server.cds.dispatcher import CdsTimeoutException
import pulp.server.cds.round_robin as round_robin
from pulp.server.db.model import CDS, CDSHistoryEventType, CDSRepoRoundRobin
from pulp.server.db.model.persistence import TaskHistory, TaskSnapshot
from pulp.server.exceptions import PulpException
from pulp.server.agent import Agent, CdsAgent

from pulp.server.db.model.gc_repository import Repo
from pulp.server.db.model.gc_repository import RepoDistributor
from pulp.server.managers.repo.cud import RepoManager
from pulp.server.managers.repo.distributor import RepoDistributorManager


repo_manager = RepoManager()

FakeDistributor = {
    'config':{
        'http':0,
        'https':1,
        'relative_url':'foo/bar',
    }
}

class CdsApiTests(testutil.PulpAsyncTest):

    # -- preparation ---------------------------------------------------------

    def setUp(self):
        super(CdsApiTests, self).setUp()
        self.orig_get_distributors = RepoDistributorManager.get_distributors

        RepoDistributorManager.get_distributors = lambda self,repoid:[FakeDistributor,]

    def tearDown(self):
        super(CdsApiTests, self).tearDown()

        RepoDistributorManager.get_distributors = self.orig_get_distributors

    def clean(self):
        testutil.PulpAsyncTest.clean(self)
        TaskHistory.get_collection().remove()
        TaskSnapshot.get_collection().remove(safe=True)
        # Flush the assignment algorithm cache
        CDSRepoRoundRobin.get_collection().remove()
        Repo.get_collection().remove()

    # -- general cds test cases ----------------------------------------------

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
        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        self.assertEqual(1, len(cdsplugin.initialize.history()))
        self.assertEqual(0, len(cdsplugin.update_cluster_membership.history()))

    def test_register_full_attributes(self):
        '''
        Tests the register call specifying a value for all optional arguments.
        '''

        # Test
        self.cds_api.register('cds.example.com', name='Test CDS', description='Test CDS Description', cluster_id='test-group')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds is not None)

        self.assertEqual(cds['hostname'], 'cds.example.com')
        self.assertEqual(cds['name'], 'Test CDS')
        self.assertEqual(cds['description'], 'Test CDS Description')
        self.assertEqual(cds['cluster_id'], 'test-group')

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(history))
        self.assertEqual(CDSHistoryEventType.REGISTERED, history[0]['type_name'])

        # Verify
        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        self.assertEqual(1, len(cdsplugin.initialize.history()))

        self.assertEqual(1, len(cdsplugin.update_cluster_membership.history()))
        self.assertEqual('test-group', cdsplugin.cluster_name)
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

    def test_register_bad_cluster_id(self):
        '''
        Tests that an invalid cluster ID properly throws an exception.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_api.register, 'cds.example.com', cluster_id='@bad!')

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
        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        self.assertEqual(1, len(cdsplugin.initialize.history()))

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
        self.assertEqual(0, len(cdsplugin.update_cluster_membership.history()))

    def test_unregister_with_cluster(self):
        '''
        Tests that unregistering a CDS that belonged to the cluster triggers an
        update group message to other members.
        '''

        # Setup
        self.cds_api.register('cds1.example.com', cluster_id='test-multi-group')
        time.sleep(1)
        self.cds_api.register('cds2.example.com', cluster_id='test-multi-group')

        cds1 = self.cds_api.cds('cds1.example.com')
        uuid1 = CdsAgent.uuid(cds1)

        cds2 = self.cds_api.cds('cds2.example.com')
        uuid2 = CdsAgent.uuid(cds2)

        # Test
        self.cds_api.unregister('cds1.example.com')

        # Verify
        cdsplugin1 = Agent(uuid1).cdsplugin()
        self.assertEqual(2, len(cdsplugin1.update_cluster_membership.history())) # own register, cds2 register

        cdsplugin2 = Agent(uuid2).cdsplugin()
        self.assertEqual(2, len(cdsplugin2.update_cluster_membership.history())) # own register, cds1 unregister
        self.assertEqual('test-multi-group', cdsplugin2.cluster_name)
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
        # This test is failing intermittently on RHEL-5
        #   File "/home/hudson/workspace/pulp-dev-rhel5/test/unit/test_cds_api.py", line 314, in test_update_cds
        #   self.assertEqual('group-2', cds['cluster_id'])
        #   AssertionError: 'group-2' != u'group-1'
        # Skipping it for now
        # TODO: Why is this failing intermittently?
        return

        # Setup
        self.cds_api.register('update-cds', 'name-1', 'description-1', 'P1D', 'group-1')

        # Test
        delta = {
            'name'          : 'name-2',
            'description'   : 'description-2',
            'sync_schedule' : 'P2D',
            'cluster_id'    : 'group-2',
        }

        updated = self.cds_api.update('update-cds', delta)

        time.sleep(1) # seeing if this clears up issues with the group not always being updated

        # Verify
        self.assertTrue(updated is not None)

        cds = self.cds_api.cds('update-cds')

        self.assertEqual('update-cds', cds['hostname'])
        self.assertEqual('name-2', cds['name'])
        self.assertEqual('description-2', cds['description'])
        self.assertEqual('P2D', cds['sync_schedule'])
        self.assertEqual('group-2', cds['cluster_id'])

        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        self.assertEqual(2, len(cdsplugin.update_cluster_membership.history())) # register, update
        self.assertEqual('group-2', cdsplugin.cluster_name)
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
            'cluster_id'    : 'group-2',
        }

        self.assertRaises(PulpException, self.cds_api.update, 'update-cds', delta)

    def test_update_cds_bad_cluster_id(self):
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
            'cluster_id'    : 'b@d=id',
        }

        self.assertRaises(PulpException, self.cds_api.update, 'update-cds', delta)

    def test_update_remove_cluster(self):
        '''
        Tests removing a group ID is successful.
        '''

        # Setup
        self.cds_api.register('update-cds', 'name-1', 'description-1', 'P1D', 'group-1')

        # Test
        delta = {
            'cluster_id'      : None,
        }

        self.cds_api.update('update-cds', delta)

        # Verify
        cds = self.cds_api.cds('update-cds')

        self.assertTrue(cds['cluster_id'] is None)

        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        self.assertEqual(2, len(cdsplugin.update_cluster_membership.history())) # register, update
        self.assertEqual(None, cdsplugin.cluster_name)
        self.assertEqual(None, cdsplugin.member_hostnames)

    def test_update_add_cluster(self):
        '''
        Tests an update that adds a group to a CDS that did not previously have one.
        '''
        # Setup
        self.cds_api.register('update-cds')

        # Test
        delta = {
            'cluster_id'      : 'new-group',
        }

        self.cds_api.update('update-cds', delta)

        # Verify
        cds = self.cds_api.cds('update-cds')

        self.assertEqual('new-group', cds['cluster_id'])

        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        self.assertEqual(1, len(cdsplugin.update_cluster_membership.history())) # update only
        self.assertEqual('new-group', cdsplugin.cluster_name)
        self.assertEqual(1, len(cdsplugin.member_hostnames))
        self.assertEqual('update-cds', cdsplugin.member_hostnames[0])

    def test_update_change_cluster(self):
        '''
        Tests that changing a CDS' group will update both members of the old and new
        groups.
        '''

        # Setup
        cds_change = self.cds_api.register('update-cds-change-me', cluster_id='group-1')
        cds_1 = self.cds_api.register('update-cds-1', cluster_id='group-1')
        cds_2 = self.cds_api.register('update-cds-2', cluster_id='group-2')

        # Test
        delta = {
            'cluster_id'      : 'group-2',
        }

        self.cds_api.update('update-cds-change-me', delta)

        # Verify
        cdsplugin_change = CdsAgent(cds_change).cdsplugin()
        cdsplugin_1 = CdsAgent(cds_1).cdsplugin()
        cdsplugin_2 = CdsAgent(cds_2).cdsplugin()

        self.assertEqual(3, len(cdsplugin_change.update_cluster_membership.history())) # self register, cds_1 register, change event
        self.assertEqual(2, len(cdsplugin_1.update_cluster_membership.history())) # self register, change event
        self.assertEqual(2, len(cdsplugin_2.update_cluster_membership.history())) # self register, change event

        self.assertEqual('group-2', cdsplugin_change.cluster_name)
        self.assertEqual('group-1', cdsplugin_1.cluster_name)
        self.assertEqual('group-2', cdsplugin_2.cluster_name)

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
        repo_manager.create_repo('cds-test-repo', 'CDS Test Repo', 'x86_64')
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
        repo_manager.create_repo('cds-test-repo', 'CDS Test Repo', 'x86_64')
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
        repo_manager.create_repo('cds-test-repo', 'CDS Test Repo', 'x86_64')

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
        repo_manager.create_repo('cds-test-repo', 'CDS Test Repo', 'x86_64')
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
        repo_manager.create_repo('cds-test-repo', 'CDS Test Repo', 'x86_64')
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
        repo_manager.create_repo('cds-test-repo', 'CDS Test Repo', 'x86_64')

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

        repo_manager.create_repo('cds-test-repo', 'CDS Test Repo', 'x86_64')

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
        repo_manager.create_repo('cds-test-repo', 'CDS Test Repo', 'x86_64')

        # Test
        self.cds_api.unassociate_all_from_repo('cds-test-repo')

        # Verify
        # The call above should not have thrown an error

    def test_sync(self):
        '''
        Tests sync under normal circumstances.
        '''

        # Setup
        self.config.remove_option('security', 'ssl_ca_certificate')

        repo = repo_manager.create_repo('cds-test-repo', 'CDS Test Repo', 'x86_64')
        self.cds_api.register('cds.example.com')
        cds = self.cds_api.cds('cds.example.com')
        self.cds_api.associate_repo('cds.example.com', repo['id'])

        # Test
        self.cds_api.cds_sync('cds.example.com')

        # Verify
        agent = CdsAgent(cds)
        cdsplugin = agent.cdsplugin()
        calls = cdsplugin.sync.history()
        self.assertEqual(1, len(calls))

        sync_payload = cdsplugin.payload

        self.assertEqual(1, len(sync_payload['repos']))
        self.assertEqual('cds-test-repo', sync_payload['repos'][0]['id'])

        self.assertTrue(sync_payload['repo_base_url'] is not None)

        self.assertEqual(1, len(sync_payload['repo_cert_bundles']))
        self.assertTrue('cds-test-repo' in sync_payload['repo_cert_bundles'])
        self.assertTrue(sync_payload['repo_cert_bundles']['cds-test-repo'] is None)

        self.assertTrue('global_cert_bundle' in sync_payload)
        self.assertTrue(sync_payload['global_cert_bundle'] is None)

        self.assertTrue('cluster_id' in sync_payload)
        self.assertTrue(sync_payload['cluster_id'] is None)

        self.assertTrue('cluster_members' in sync_payload)
        self.assertTrue(sync_payload['cluster_members'] is None)

        self.assertTrue('server_ca_cert' in sync_payload)
        self.assertTrue(sync_payload['server_ca_cert'] is None)

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(4, len(history))

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
        repo = repo_manager.create_repo('cds-test-repo', 'CDS Test Repo', 'x86_64')
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

        history = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(4, len(history))

        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds['last_sync'] is not None)

    def test_cds_with_repo(self):
        '''
        Tests searching for CDS instances by a repo ID when there is at least one association
        to the given repo.
        '''

        # Setup
        repo = repo_manager.create_repo('cds-test-repo', 'CDS Test Repo', 'x86_64')
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
        repo = repo_manager.create_repo('cds-test-repo', 'CDS Test Repo', 'x86_64')
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

    def test_redistribute(self):
        '''
        Tests redistribute with multiple consumers bound to the repo and multiple CDS instances
        hosting it.
        '''

        CDS_HOSTNAMES = ('cds1', 'cds2')
        CONSUMERIDS = ('consumer1', 'consumer2', 'consumer3')
        REPOID = 'cds-test-repo'

        # Setup
        repo_manager.create_repo(REPOID, 'CDS Test Repo', 'noarch')

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
            repoproxy = agent.ConsumerXXX()
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
        repo = repo_manager.create_repo('cds-test-repo', 'CDS Test Repo', 'noarch')

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
        repo = repo_manager.create_repo('cds-test-repo', 'CDS Test Repo', 'noarch')

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

    # -- cds cluster test cases ------------------------------------------------

    def test_register_auto_associate(self):
        """
        Tests that registering a CDS to a group that already has CDS instances
        with repositories causes the newly registered CDS to get the same associations.
        """

        # Setup
        repo_manager.create_repo('test-repo-1', 'CDS Test Repo 1', 'noarch') # in the group
        repo_manager.create_repo('test-repo-x', 'CDS Test Repo X', 'noarch') # unused; make sure it doesn't sneak in

        self.cds_api.register('cds-existing', cluster_id='test-group')
        self.cds_api.associate_repo('cds-existing', 'test-repo-1')

        # Test
        self.cds_api.register('cds-new', cluster_id='test-group')

        # Verify
        cds = self.cds_api.cds('cds-new')
        self.assertEqual(['test-repo-1'], cds['repo_ids'])

    def test_register_auto_associate_no_repos(self):
        """
        Tests that registering a CDS to a group with a CDS instance that doesn't have
        repositories associated doesn't throw an error when resolving association
        differences.
        """

        # Setup
        repo_manager.create_repo('test-repo-x', 'CDS Test Repo X', 'noarch') # unused; make sure it doesn't sneak in
        self.cds_api.register('cds-existing', cluster_id='test-group')

        # Test
        self.cds_api.register('cds-new', cluster_id='test-group')

        # Verify
        cds = self.cds_api.cds('cds-new')
        self.assertEqual(0, len(cds['repo_ids']))

    def test_update_group_resolve_repo_associations(self):
        """
        Tests that updating a CDS that already has repo associations and putting it
        in a group causes the CDS to have its repo associations changed to meet the
        rest of the group. This test includes testing that repos are both added to
        and removed from the updated CDS.
        """

        # Setup
        repo_manager.create_repo('test-repo-1', 'CDS Test Repo 1', 'noarch') # in the group
        repo_manager.create_repo('test-repo-2', 'CDS Test Repo 2', 'noarch') # on the CDS before group membership
        repo_manager.create_repo('test-repo-x', 'CDS Test Repo X', 'noarch') # unused; make sure it doesn't sneak in

        self.cds_api.register('cds-existing', cluster_id='test-group')
        self.cds_api.associate_repo('cds-existing', 'test-repo-1')

        self.cds_api.register('cds-updated')
        self.cds_api.associate_repo('cds-updated', 'test-repo-2')

        # Test
        delta = {'cluster_id' : 'test-group'}
        self.cds_api.update('cds-updated', delta)

        # Verify
        cds = self.cds_api.cds('cds-updated')
        self.assertEqual(['test-repo-1'], cds['repo_ids'])

    def test_associate_repo_to_group_member(self):
        """
        Tests that associating a repo to a CDS in a group applies the association to
        all group members.
        """

        # Setup
        repo_manager.create_repo('test-repo-1', 'CDS Test Repo 1', 'noarch') # will be added to the group
        repo_manager.create_repo('test-repo-x', 'CDS Test Repo X', 'noarch') # unused; make sure it doesn't sneak in

        self.cds_api.register('cds-1', cluster_id='test-group')
        self.cds_api.register('cds-2', cluster_id='test-group')
        self.cds_api.register('cds-3', cluster_id='test-group')

        # Test
        self.cds_api.associate_repo('cds-1', 'test-repo-1')

        # Verify
        for i in range(1, 4):
            cds = self.cds_api.cds('cds-%d' % i)
            self.assertEqual(['test-repo-1'], cds['repo_ids'])

    def test_unassociate_repo_from_group_member(self):
        """
        Tests that unassociating a repo from a CDS in a group applies the removal to
        all group members.
        """

        # Setup
        repo_manager.create_repo('test-repo-1', 'CDS Test Repo 1', 'noarch') # will be added to the group
        repo_manager.create_repo('test-repo-x', 'CDS Test Repo X', 'noarch') # unused; make sure it doesn't sneak in

        self.cds_api.register('cds-1', cluster_id='test-group')
        self.cds_api.register('cds-2', cluster_id='test-group')
        self.cds_api.register('cds-3', cluster_id='test-group')

        self.cds_api.associate_repo('cds-1', 'test-repo-1')

        # Test
        self.cds_api.unassociate_repo('cds-1', 'test-repo-1')

        # Verify
        for i in range(1, 4):
            cds = self.cds_api.cds('cds-%d' % i)
            self.assertEqual([], cds['repo_ids'])
