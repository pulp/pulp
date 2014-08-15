#!/usr/bin/python
#
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import base

from mock import patch

from pulp.devel import mock_plugins
from pulp.plugins.loader import api as plugin_api
from pulp.server.db.model.consumer import Consumer, Bind
from pulp.server.db.model.repository import Repo, RepoDistributor
from pulp.server.db.model.criteria import Criteria
from pulp.server.exceptions import MissingResource, InvalidValue
from pulp.server.managers import factory


# -- test cases ---------------------------------------------------------------


class BindManagerTests(base.PulpServerTests):

    CONSUMER_ID = 'test-consumer'
    EXTRA_CONSUMER_1 = 'extra_consumer_1'
    EXTRA_CONSUMER_2 = 'extra_consumer_2'
    ALL_CONSUMERS = [CONSUMER_ID, EXTRA_CONSUMER_1, EXTRA_CONSUMER_2]
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'test-distributor'
    NOTIFY_AGENT = True
    BINDING_CONFIG = {'a': 'a'}

    QUERY = dict(consumer_id=CONSUMER_ID, repo_id=REPO_ID, distributor_id=DISTRIBUTOR_ID)

    # The methods that use these expect strings, not ints
    ACTION_IDS = '1 2 3 4 5 6 7 8 9'.split()

    def setUp(self):
        super(BindManagerTests, self).setUp()
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_api._create_manager()
        mock_plugins.install()

    def tearDown(self):
        super(BindManagerTests, self).tearDown()
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        mock_plugins.reset()

    def populate(self):
        config = {'key1' : 'value1', 'key2' : None}
        manager = factory.repo_manager()
        repo = manager.create_repo(self.REPO_ID)
        manager = factory.repo_distributor_manager()
        manager.add_distributor(
            self.REPO_ID,
            'mock-distributor',
            config,
            True,
            distributor_id=self.DISTRIBUTOR_ID)
        manager = factory.consumer_manager()
        for consumer_id in self.ALL_CONSUMERS:
            manager.register(consumer_id)

    def test_bind(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Verify
        collection = Bind.get_collection()
        bind = collection.find_one(self.QUERY)
        self.assertTrue(bind is not None)
        self.assertEqual(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(bind['repo_id'], self.REPO_ID)
        self.assertEqual(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertEqual(bind['notify_agent'], self.NOTIFY_AGENT)
        self.assertEqual(bind['binding_config'], self.BINDING_CONFIG)

    def test_bind_non_bool_notify(self):
        # Setup
        self.populate()

        # Test
        manager = factory.consumer_bind_manager()
        try:
            manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                         'True', self.BINDING_CONFIG)
            self.fail(msg='Expected exception from bind was not raised')
        except InvalidValue, e:
            self.assertEqual(['notify_agent'], e.property_names)

    def test_unbind(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Test
        manager = factory.consumer_bind_manager()
        manager.unbind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)

        # Verify
        collection = Bind.get_collection()
        bind_id = dict(
            consumer_id=self.CONSUMER_ID,
            repo_id=self.REPO_ID,
            distributor_id=self.DISTRIBUTOR_ID)
        bind = collection.find_one(bind_id)
        self.assertTrue(bind is not None)
        self.assertTrue(bind['deleted'])

    def test_get_bind(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Test
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Verify
        self.assertTrue(bind is not None)
        self.assertEqual(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(bind['repo_id'], self.REPO_ID)
        self.assertEqual(bind['distributor_id'], self.DISTRIBUTOR_ID)

    def test_get_bind_not_found(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Test
        self.assertRaises(MissingResource, manager.get_bind, 'A', 'B', 'C')

    def test_get_bind_repo_gone(self):
        """
        Test that retrieving a consumer binding when the repo is gone is possible
        """
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        Repo.get_collection().remove({})

        # Test
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        self.assertEquals(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEquals(bind['repo_id'], self.REPO_ID)
        self.assertEquals(bind['distributor_id'], self.DISTRIBUTOR_ID)

    def test_find_all(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Test
        binds = manager.find_all()
        # Verify
        self.assertEqual(len(binds), 1)
        bind = binds[0]
        self.assertEqual(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(bind['repo_id'], self.REPO_ID)
        self.assertEqual(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertEqual(bind['notify_agent'], self.NOTIFY_AGENT)
        self.assertEqual(bind['binding_config'], self.BINDING_CONFIG)

    def test_find_by_consumer(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Test
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        # Verify
        self.assertEqual(len(binds), 1)
        bind = binds[0]
        self.assertEqual(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(bind['repo_id'], self.REPO_ID)
        self.assertEqual(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertEqual(bind['notify_agent'], self.NOTIFY_AGENT)
        self.assertEqual(bind['binding_config'], self.BINDING_CONFIG)

    def test_find_by_criteria(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Test
        criteria = Criteria({'consumer_id':self.CONSUMER_ID})
        bindings = manager.find_by_criteria(criteria)
        bind = bindings[0]
        self.assertEqual(len(bindings), 1)
        self.assertEqual(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(bind['repo_id'], self.REPO_ID)
        self.assertEqual(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertEqual(bind['notify_agent'], self.NOTIFY_AGENT)
        self.assertEqual(bind['binding_config'], self.BINDING_CONFIG)
        # Test ($in)
        criteria = Criteria({'consumer_id':{'$in':[self.CONSUMER_ID]}})
        bindings = manager.find_by_criteria(criteria)
        bind = bindings[0]
        self.assertEqual(len(bindings), 1)
        self.assertEqual(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(bind['repo_id'], self.REPO_ID)
        self.assertEqual(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertEqual(bind['notify_agent'], self.NOTIFY_AGENT)
        self.assertEqual(bind['binding_config'], self.BINDING_CONFIG)

    def test_find_by_repo(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Test
        binds = manager.find_by_repo(self.REPO_ID)
        # Verify
        self.assertEqual(len(binds), 1)
        bind = binds[0]
        self.assertEqual(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(bind['repo_id'], self.REPO_ID)
        self.assertEqual(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertEqual(bind['notify_agent'], self.NOTIFY_AGENT)
        self.assertEqual(bind['binding_config'], self.BINDING_CONFIG)

    def test_find_by_distributor(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Test
        binds = manager.find_by_distributor(self.REPO_ID, self.DISTRIBUTOR_ID)
        # Verify
        self.assertEqual(len(binds), 1)
        bind = binds[0]
        self.assertEqual(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(bind['repo_id'], self.REPO_ID)
        self.assertEqual(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertEqual(bind['notify_agent'], self.NOTIFY_AGENT)
        self.assertEqual(bind['binding_config'], self.BINDING_CONFIG)

    def test_consumer_deleted(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEqual(len(binds), 1)
        # Test
        manager.consumer_deleted(self.CONSUMER_ID)
        # Verify
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEqual(len(binds), 0)

    @patch('pulp.server.managers.factory.consumer_agent_manager')
    def test_consumer_unregister_cleanup(self, *unused):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        manager = factory.consumer_bind_manager()
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEqual(len(binds), 1)
        # Test
        manager = factory.consumer_manager()
        manager.unregister(self.CONSUMER_ID)
        # Verify
        manager = factory.consumer_bind_manager()
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEqual(len(binds), 0)

    def test_request_pending(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        self.assertEqual(bind['consumer_actions'], [])
        manager.action_pending(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            Bind.Action.BIND,
            self.ACTION_IDS[0])
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        actions = bind['consumer_actions']
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['id'], self.ACTION_IDS[0])
        self.assertEqual(actions[0]['action'], Bind.Action.BIND)
        self.assertEqual(actions[0]['status'], Bind.Status.PENDING)

    def test_bind_request_succeeded(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        self.assertEqual(bind['consumer_actions'], [])
        for action_id in self.ACTION_IDS:
            manager.action_pending(
                self.CONSUMER_ID,
                self.REPO_ID,
                self.DISTRIBUTOR_ID,
                Bind.Action.BIND,
                action_id)
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        actions = bind['consumer_actions']
        for i in range(0, len(self.ACTION_IDS)):
            self.assertEqual(actions[i]['id'], self.ACTION_IDS[i])
            self.assertEqual(actions[i]['action'], Bind.Action.BIND)
            self.assertEqual(actions[i]['status'], Bind.Status.PENDING)
        manager.action_succeeded(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            self.ACTION_IDS[4])
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        actions = bind['consumer_actions']
        self.assertEqual(len(actions), 4)

    def test_bind_action_failed(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        self.assertEqual(bind['consumer_actions'], [])
        for action_id in self.ACTION_IDS:
            manager.action_pending(
                self.CONSUMER_ID,
                self.REPO_ID,
                self.DISTRIBUTOR_ID,
                Bind.Action.BIND,
                action_id)
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        actions = bind['consumer_actions']
        for i in range(0, len(self.ACTION_IDS)):
            self.assertEqual(actions[i]['id'], self.ACTION_IDS[i])
            self.assertEqual(actions[i]['action'], Bind.Action.BIND)
            self.assertEqual(actions[i]['status'], Bind.Status.PENDING)
        manager.action_failed(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            self.ACTION_IDS[5])
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        actions = bind['consumer_actions']
        self.assertEqual(len(actions), 9)
        for i in range(0, len(self.ACTION_IDS)):
            if i == 5:
                status = Bind.Status.FAILED
            else:
                status = Bind.Status.PENDING
            self.assertEqual(actions[i]['id'], self.ACTION_IDS[i])
            self.assertEqual(actions[i]['action'], Bind.Action.BIND)
            self.assertEqual(actions[i]['status'], status)
        manager.action_succeeded(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            self.ACTION_IDS[6])
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        actions = bind['consumer_actions']
        self.assertEqual(len(actions), 2)

    def test_mark_deleted(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        bind = manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                            self.NOTIFY_AGENT, self.BINDING_CONFIG)
        self.assertFalse(bind['deleted'])
        # Test
        manager.mark_deleted(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Validate
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        self.assertTrue(bind['deleted'])

    def test_delete(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        for consumer_id in self.ALL_CONSUMERS:
            manager.bind(consumer_id, self.REPO_ID, self.DISTRIBUTOR_ID, self.NOTIFY_AGENT, self.BINDING_CONFIG)
        manager.action_pending(self.EXTRA_CONSUMER_1, self.REPO_ID, self.DISTRIBUTOR_ID, Bind.Action.BIND, '1')
        manager.action_pending(self.EXTRA_CONSUMER_2, self.REPO_ID, self.DISTRIBUTOR_ID, Bind.Action.BIND, '2')
        # Test
        manager.mark_deleted(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        manager.delete(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Verify
        self.assertRaises(MissingResource, manager.get_bind, self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        manager.get_bind(self.EXTRA_CONSUMER_1, self.REPO_ID, self.DISTRIBUTOR_ID)
        manager.get_bind(self.EXTRA_CONSUMER_2, self.REPO_ID, self.DISTRIBUTOR_ID)

    def test_delete_but_not_marked_for_delete(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        for consumer_id in self.ALL_CONSUMERS:
            manager.bind(consumer_id, self.REPO_ID, self.DISTRIBUTOR_ID, self.NOTIFY_AGENT, self.BINDING_CONFIG)
        manager.action_pending(self.EXTRA_CONSUMER_1, self.REPO_ID, self.DISTRIBUTOR_ID, Bind.Action.BIND, '1')
        manager.action_pending(self.EXTRA_CONSUMER_2, self.REPO_ID, self.DISTRIBUTOR_ID, Bind.Action.BIND, '2')
        # Test
        manager.delete(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Verify
        manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        manager.get_bind(self.EXTRA_CONSUMER_1, self.REPO_ID, self.DISTRIBUTOR_ID)
        manager.get_bind(self.EXTRA_CONSUMER_2, self.REPO_ID, self.DISTRIBUTOR_ID)

    def test_delete_with_actions(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Test
        manager.delete(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        manager.action_pending(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            Bind.Action.BIND,
            '0')
        self.assertRaises(
            Exception,
            manager.delete,
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID)

    def test_hard_delete(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Test
        manager.delete(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        manager.action_pending(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            Bind.Action.BIND,
            '0')
        manager.delete(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID, True)
        collection = Bind.get_collection()
        bind_id = manager.bind_id(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        bind = collection.find_one(bind_id)
        self.assertTrue(bind is None)

    def test_get_missing_bind(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        # Test
        try:
            manager.get_bind(
                self.CONSUMER_ID,
                self.REPO_ID,
                self.DISTRIBUTOR_ID)
            self.fail(msg='MissingResource <Bind>, expected')
        except MissingResource:
            # expected
            pass

    def test_bind_missing_consumer(self):
        # Setup
        self.populate()
        collection = Consumer.get_collection()
        collection.remove({})
        # Test
        manager = factory.consumer_bind_manager()
        try:
            manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                         self.NOTIFY_AGENT, self.BINDING_CONFIG)
            self.fail(msg='MissingResource <Consumer>, expected')
        except MissingResource:
            # expected
            pass
            # Verify
        collection = Bind.get_collection()
        binds = collection.find({})
        binds = [b for b in binds]
        self.assertEqual(len(binds), 0)

    def test_bind_missing_distributor(self):
        # Setup
        self.populate()
        collection = RepoDistributor.get_collection()
        collection.remove({})
        # Test
        manager = factory.consumer_bind_manager()
        self.assertRaises(InvalidValue, manager.bind, self.CONSUMER_ID, self.REPO_ID,
                          self.DISTRIBUTOR_ID, self.NOTIFY_AGENT, self.BINDING_CONFIG)
        collection = Bind.get_collection()
        binds = collection.find({})
        binds = [b for b in binds]
        self.assertEqual(len(binds), 0)
