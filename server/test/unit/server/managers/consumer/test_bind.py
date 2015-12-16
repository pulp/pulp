from mock import patch

from .... import base
from pulp.devel import mock_plugins
from pulp.plugins.loader import api as plugin_api
from pulp.server.controllers import distributor as dist_controller
from pulp.server.db import model
from pulp.server.db.model.consumer import Bind, Consumer, ConsumerHistoryEvent
from pulp.server.db.model.criteria import Criteria
from pulp.server.exceptions import MissingResource, InvalidValue
from pulp.server.managers import factory


@patch('pulp.server.managers.consumer.bind.model.Repository.objects')
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
    DETAILS = {'repo_id': REPO_ID, 'distributor_id': DISTRIBUTOR_ID}
    QUERY1 = dict(consumer_id=CONSUMER_ID, originator='SYSTEM', type='repo_bound',
                  details=DETAILS)
    QUERY2 = dict(consumer_id=CONSUMER_ID, originator='SYSTEM', type='repo_unbound',
                  details=DETAILS)

    # The methods that use these expect strings, not ints
    ACTION_IDS = '1 2 3 4 5 6 7 8 9'.split()

    def setUp(self):
        super(BindManagerTests, self).setUp()
        Consumer.get_collection().remove()
        model.Distributor.objects.delete()
        Bind.get_collection().remove()
        ConsumerHistoryEvent.get_collection().remove()
        plugin_api._create_manager()
        mock_plugins.install()

    def tearDown(self):
        super(BindManagerTests, self).tearDown()
        Consumer.get_collection().remove()
        model.Repository.objects.delete()
        model.Distributor.objects.delete()
        Bind.get_collection().remove()
        ConsumerHistoryEvent.get_collection().remove()
        mock_plugins.reset()

    def populate(self):
        config = {'key1': 'value1', 'key2': None}
        dist_controller.add_distributor(
            self.REPO_ID,
            'mock-distributor',
            config,
            True,
            distributor_id=self.DISTRIBUTOR_ID)
        manager = factory.consumer_manager()
        for consumer_id in self.ALL_CONSUMERS:
            manager.register(consumer_id)

    def test_bind(self, mock_repo_qs):
        self.populate()
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

    def test_bind_consumer_history(self, mock_repo_qs):
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Verify
        collection = ConsumerHistoryEvent.get_collection()
        history = collection.find_one(self.QUERY1)
        self.assertTrue(history is not None)
        self.assertEqual(history['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(history['type'], 'repo_bound')
        self.assertEqual(history['originator'], 'SYSTEM')
        self.assertEqual(history['details'], self.DETAILS)

    def test_bind_non_bool_notify(self, mock_repo_qs):
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

    def test_unbind(self, mock_repo_qs):
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

    def test_unbind_consumer_history(self, mock_repo_qs):
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Test
        manager.unbind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Verify
        collection = ConsumerHistoryEvent.get_collection()
        history = collection.find_one(self.QUERY2)
        self.assertTrue(history is not None)
        self.assertEqual(history['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(history['type'], 'repo_unbound')
        self.assertEqual(history['originator'], 'SYSTEM')
        self.assertEqual(history['details'], self.DETAILS)

    def test_get_bind(self, mock_repo_qs):
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

    def test_get_bind_not_found(self, mock_repo_qs):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Test
        self.assertRaises(MissingResource, manager.get_bind, 'A', 'B', 'C')

    def test_get_bind_repo_gone(self, mock_repo_qs):
        """
        Test that retrieving a consumer binding when the repo is gone is possible
        """
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        self.assertEquals(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEquals(bind['repo_id'], self.REPO_ID)
        self.assertEquals(bind['distributor_id'], self.DISTRIBUTOR_ID)

    def test_find_all(self, mock_repo_qs):
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

    def test_find_by_consumer(self, mock_repo_qs):
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

    def test_find_by_criteria(self, mock_repo_qs):
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        # Test
        criteria = Criteria({'consumer_id': self.CONSUMER_ID})
        bindings = manager.find_by_criteria(criteria)
        bind = bindings[0]
        self.assertEqual(len(bindings), 1)
        self.assertEqual(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(bind['repo_id'], self.REPO_ID)
        self.assertEqual(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertEqual(bind['notify_agent'], self.NOTIFY_AGENT)
        self.assertEqual(bind['binding_config'], self.BINDING_CONFIG)
        # Test ($in)
        criteria = Criteria({'consumer_id': {'$in': [self.CONSUMER_ID]}})
        bindings = manager.find_by_criteria(criteria)
        bind = bindings[0]
        self.assertEqual(len(bindings), 1)
        self.assertEqual(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(bind['repo_id'], self.REPO_ID)
        self.assertEqual(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertEqual(bind['notify_agent'], self.NOTIFY_AGENT)
        self.assertEqual(bind['binding_config'], self.BINDING_CONFIG)

    def test_find_by_repo(self, mock_repo_qs):
        self.populate()
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

    def test_find_by_distributor(self, mock_repo_qs):
        self.populate()
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

    def test_consumer_deleted(self, mock_repo_qs):
        self.populate()
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
        self.populate()
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

    def test_request_pending(self, mock_repo_qs):
        self.populate()
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

    def test_bind_request_succeeded(self, mock_repo_qs):
        self.populate()
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

    def test_bind_action_failed(self, mock_repo_qs):
        self.populate()
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

    def test_mark_deleted(self, mock_repo_qs):
        self.populate()
        manager = factory.consumer_bind_manager()
        bind = manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                            self.NOTIFY_AGENT, self.BINDING_CONFIG)
        self.assertFalse(bind['deleted'])

        manager.mark_deleted(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Validate
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        self.assertTrue(bind['deleted'])

    def test_delete(self, mock_repo_qs):
        self.populate()
        manager = factory.consumer_bind_manager()
        for consumer_id in self.ALL_CONSUMERS:
            manager.bind(consumer_id, self.REPO_ID, self.DISTRIBUTOR_ID, self.NOTIFY_AGENT,
                         self.BINDING_CONFIG)
        manager.action_pending(self.EXTRA_CONSUMER_1, self.REPO_ID, self.DISTRIBUTOR_ID,
                               Bind.Action.BIND, '1')
        manager.action_pending(self.EXTRA_CONSUMER_2, self.REPO_ID, self.DISTRIBUTOR_ID,
                               Bind.Action.BIND, '2')

        manager.mark_deleted(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        manager.delete(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)

        self.assertRaises(MissingResource, manager.get_bind, self.CONSUMER_ID, self.REPO_ID,
                          self.DISTRIBUTOR_ID)
        manager.get_bind(self.EXTRA_CONSUMER_1, self.REPO_ID, self.DISTRIBUTOR_ID)
        manager.get_bind(self.EXTRA_CONSUMER_2, self.REPO_ID, self.DISTRIBUTOR_ID)

    def test_delete_but_not_marked_for_delete(self, mock_repo_qs):
        self.populate()
        manager = factory.consumer_bind_manager()
        for consumer_id in self.ALL_CONSUMERS:
            manager.bind(consumer_id, self.REPO_ID, self.DISTRIBUTOR_ID, self.NOTIFY_AGENT,
                         self.BINDING_CONFIG)
        manager.action_pending(self.EXTRA_CONSUMER_1, self.REPO_ID, self.DISTRIBUTOR_ID,
                               Bind.Action.BIND, '1')
        manager.action_pending(self.EXTRA_CONSUMER_2, self.REPO_ID, self.DISTRIBUTOR_ID,
                               Bind.Action.BIND, '2')

        manager.delete(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)

        manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        manager.get_bind(self.EXTRA_CONSUMER_1, self.REPO_ID, self.DISTRIBUTOR_ID)
        manager.get_bind(self.EXTRA_CONSUMER_2, self.REPO_ID, self.DISTRIBUTOR_ID)

    def test_delete_with_actions(self, mock_repo_qs):
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

    def test_hard_delete(self, mock_repo_qs):
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

    def test_get_missing_bind(self, mock_repo_qs):
        self.populate()
        manager = factory.consumer_bind_manager()
        try:
            manager.get_bind(
                self.CONSUMER_ID,
                self.REPO_ID,
                self.DISTRIBUTOR_ID)
            self.fail(msg='MissingResource <Bind>, expected')
        except MissingResource:
            # expected
            pass

    def test_bind_missing_consumer(self, mock_repo_qs):
        self.populate()
        collection = Consumer.get_collection()
        collection.remove({})
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

    def test_bind_missing_distributor(self, mock_repo_qs):
        self.populate()
        model.Distributor.objects.delete()
        manager = factory.consumer_bind_manager()
        self.assertRaises(InvalidValue, manager.bind, self.CONSUMER_ID, self.REPO_ID,
                          self.DISTRIBUTOR_ID, self.NOTIFY_AGENT, self.BINDING_CONFIG)
        collection = Bind.get_collection()
        binds = collection.find({})
        binds = [b for b in binds]
        self.assertEqual(len(binds), 0)
