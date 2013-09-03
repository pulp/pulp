# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


from mock import patch

from base import PulpItineraryTests
from pulp.devel import mock_plugins
from pulp.devel import mock_agent
from pulp.plugins.loader import api as plugin_api
from pulp.server.managers import factory
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.db.model.consumer import Consumer, Bind
from pulp.server.db.model.repository import Repo, RepoDistributor
from pulp.server.itineraries.bind import (
    bind_itinerary, unbind_itinerary, forced_unbind_itinerary)
from pulp.agent.lib.report import DispatchReport

class TestBind(PulpItineraryTests):

    CONSUMER_ID = 'test-consumer'
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'dist-1'
    NOTIFY_AGENT = True
    BINDING_CONFIG = {'b' : 'b'}
    DISTRIBUTOR_TYPE_ID = 'mock-distributor'
    QUERY = dict(
        consumer_id=CONSUMER_ID,
        repo_id=REPO_ID,
        distributor_id=DISTRIBUTOR_ID,
        )
    PAYLOAD = dict(
        server_name='pulp.redhat.com',
        relative_path='/repos/content/repoA',
        protocols=['https',],
        gpg_keys=['key1',],
        ca_cert='MY-CA',
        client_cert='MY-CLIENT-CERT')

    BIND_TAGS = [
        'pulp:consumer:test-consumer',
        'pulp:repository:test-repo',
        'pulp:repository_distributor:dist-1',
        'pulp:action:bind'
    ]

    AGENT_BIND_TAGS = [
        'pulp:consumer:test-consumer',
        'pulp:repository:test-repo',
        'pulp:repository_distributor:dist-1',
        'pulp:action:agent_bind'
    ]

    UNBIND_TAGS = [
        'pulp:consumer:test-consumer',
        'pulp:repository:test-repo',
        'pulp:repository_distributor:dist-1',
        'pulp:action:unbind'
    ]

    AGENT_UNBIND_TAGS = [
        'pulp:consumer:test-consumer',
        'pulp:repository:test-repo',
        'pulp:repository_distributor:dist-1',
        'pulp:action:agent_unbind'
    ]

    DELETE_BINDING_TAGS = [
        'pulp:consumer:test-consumer',
        'pulp:repository:test-repo',
        'pulp:repository_distributor:dist-1',
        'pulp:action:delete_binding'
    ]

    def setUp(self):
        PulpItineraryTests.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_api._create_manager()
        mock_plugins.install()
        mock_agent.install()

    def tearDown(self):
        PulpItineraryTests.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        mock_plugins.reset()

    def populate(self):
        manager = factory.repo_manager()
        manager.create_repo(self.REPO_ID)
        manager = factory.repo_distributor_manager()
        manager.add_distributor(
            self.REPO_ID,
            self.DISTRIBUTOR_TYPE_ID,
            {},
            True,
            distributor_id=self.DISTRIBUTOR_ID)
        mock_plugins.MOCK_DISTRIBUTOR.create_consumer_payload.return_value=self.PAYLOAD
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID)

    def test_bind(self):

        # Setup
        self.populate()

        # Test
        options = {}
        itinerary = bind_itinerary(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            self.NOTIFY_AGENT,
            self.BINDING_CONFIG,
            options)
        call_reports = self.coordinator.execute_multiple_calls(itinerary)

        # Verify
        self.assertEqual(len(call_reports), 2)
        self.assertEqual(call_reports[0].call_request_tags, self.BIND_TAGS)
        self.assertEqual(call_reports[1].call_request_tags, self.AGENT_BIND_TAGS)
        for call in call_reports:
            self.assertNotEqual(call.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # run task #1 (actual bind)
        self.run_next()

        # verify bind created
        manager = factory.consumer_bind_manager()
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 1)
        bind = binds[0]
        self.assertEqual(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(bind['repo_id'], self.REPO_ID)
        self.assertEqual(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertEqual(bind['notify_agent'], self.NOTIFY_AGENT)
        self.assertEqual(bind['binding_config'], self.BINDING_CONFIG)

        # run task #2 (notify consumer)
        self.run_next()

        # verify pending consumer request (pending)
        request_id = call_reports[1].call_request_id
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        actions = bind['consumer_actions']
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['id'], request_id)
        self.assertEqual(actions[0]['action'], Bind.Action.BIND)
        self.assertEqual(actions[0]['status'], Bind.Status.PENDING)
        self.assertTrue(isinstance(actions[0]['timestamp'], float))

        # verify agent notified
        self.assertTrue(mock_agent.Consumer.bind.called)
        # simulated asynchronous task result
        report = DispatchReport()
        self.coordinator.complete_call_success(request_id, report.dict())

        # verify pending consumer request (confirmed)
        manager = factory.consumer_bind_manager()
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        self.assertEqual(len(bind['consumer_actions']), 0)

    def test_bind_no_notify_agent(self):
        # Setup
        self.populate()

        # Test
        options = {}
        itinerary = bind_itinerary(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            False,
            self.BINDING_CONFIG,
            options)
        call_reports = self.coordinator.execute_multiple_calls(itinerary)

        # Verify
        self.assertEqual(len(call_reports), 1)
        self.assertEqual(call_reports[0].call_request_tags, self.BIND_TAGS)
        for call in call_reports:
            self.assertNotEqual(call.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # run task #1 (actual bind)
        self.run_next()

        # verify bind created
        manager = factory.consumer_bind_manager()
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 1)
        bind = binds[0]
        self.assertEqual(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(bind['repo_id'], self.REPO_ID)
        self.assertEqual(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertEqual(bind['notify_agent'], False)
        self.assertEqual(bind['binding_config'], self.BINDING_CONFIG)

        # run task #2 (notify consumer)
        try:
            self.run_next()
            self.fail('Second task to bind found')
        except Exception:
            pass  # the agent notify shouldn't trigger

        # verify agent was not notified
        self.assertTrue(not mock_agent.Consumer.bind.called)

    @patch('pulp.server.managers.consumer.bind.BindManager.bind', side_effect=Exception())
    def test_bind_failed(self, mock_bind):

        # Setup
        self.populate()

        # Test
        options = {}
        itinerary = bind_itinerary(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            self.NOTIFY_AGENT,
            self.BINDING_CONFIG,
            options)
        call_reports = self.coordinator.execute_multiple_calls(itinerary)

        # Verify
        self.assertEqual(len(call_reports), 2)
        for call in call_reports:
            self.assertNotEqual(call.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # run task #1 (actual bind)
        self.run_next()

        # run task #2 (notify consumer)
        self.run_next()

        # verify task #2 was skipped
        request_id = call_reports[1].call_request_id
        call_report = self.coordinator.find_call_reports(call_request_id=request_id)[0]
        self.assertEqual(call_report.state, dispatch_constants.CALL_SKIPPED_STATE)

        # verify agent NOT notified
        self.assertFalse(mock_agent.Consumer.bind.called)

    def test_bind_failed_on_consumer(self):

        # Setup
        self.populate()

        # Test
        options = {}
        itinerary = bind_itinerary(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            self.NOTIFY_AGENT,
            self.BINDING_CONFIG,
            options)
        call_reports = self.coordinator.execute_multiple_calls(itinerary)

        # Verify
        self.assertEqual(len(call_reports), 2)
        for call in call_reports:
            self.assertNotEqual(call.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # run task #1 (actual bind)
        self.run_next()

        # verify bind created
        manager = factory.consumer_bind_manager()
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 1)
        bind = binds[0]
        self.assertEqual(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEqual(bind['repo_id'], self.REPO_ID)
        self.assertEqual(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertEqual(bind['notify_agent'], self.NOTIFY_AGENT)
        self.assertEqual(bind['binding_config'], self.BINDING_CONFIG)

        # run task #2 (notify consumer)
        self.run_next()

        # verify pending consumer request (pending)
        request_id = call_reports[1].call_request_id
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        actions = bind['consumer_actions']
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['id'], request_id)
        self.assertEqual(actions[0]['action'], Bind.Action.BIND)
        self.assertEqual(actions[0]['status'], Bind.Status.PENDING)
        self.assertTrue(isinstance(actions[0]['timestamp'], float))

        # verify agent notified
        self.assertTrue(mock_agent.Consumer.bind.called)

        # simulated asynchronous task result
        report = DispatchReport()
        report.succeeded = False
        self.coordinator.complete_call_success(request_id, report.dict())

        # verify pending consumer request (failed)
        manager = factory.consumer_bind_manager()
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        actions = bind['consumer_actions']
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['id'], request_id)
        self.assertEqual(actions[0]['action'], Bind.Action.BIND)
        self.assertEqual(actions[0]['status'], Bind.Status.FAILED)
        self.assertTrue(isinstance(actions[0]['timestamp'], float))

    def test_unbind(self):

        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)

        # Test
        options = {}
        itinerary = unbind_itinerary(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            options)
        call_reports = self.coordinator.execute_multiple_calls(itinerary)

        # Verify
        self.assertEqual(len(call_reports), 3)
        self.assertEqual(call_reports[0].call_request_tags, self.UNBIND_TAGS)
        self.assertEqual(call_reports[1].call_request_tags, self.AGENT_UNBIND_TAGS)
        self.assertEqual(call_reports[2].call_request_tags[1], self.DELETE_BINDING_TAGS[1])
        for call in call_reports:
            self.assertNotEqual(call.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # run task #1 (actual unbind)
        self.run_next()

        # verify bind marked deleted
        collection = Bind.get_collection()
        bind = collection.find_one(self.QUERY)
        self.assertTrue(bind['deleted'])

        # run task #2 (notify consumer)
        self.run_next()

        # verify agent notified
        self.assertTrue(mock_agent.Consumer.unbind.called)

        # verify consumer request (pending)
        request_id = call_reports[1].call_request_id
        collection = Bind.get_collection()
        bind = collection.find_one(self.QUERY)
        self.assertTrue(bind is not None)
        actions = bind['consumer_actions']
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['id'], request_id)
        self.assertEqual(actions[0]['action'], Bind.Action.UNBIND)
        self.assertEqual(actions[0]['status'], Bind.Status.PENDING)
        self.assertTrue(isinstance(actions[0]['timestamp'], float))

        # simulated asynchronous task result
        report = DispatchReport()
        self.coordinator.complete_call_success(request_id, report.dict())

        # verify not found (marked deleted)
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 0)

        # run task #3 (bind actually deleted)
        self.run_next()

        # verify bind actually deleted
        collection = Bind.get_collection()
        bind = collection.find_one(self.QUERY)
        self.assertTrue(bind is None)

    def test_forced_unbind(self):

        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        bind = manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                            self.NOTIFY_AGENT, self.BINDING_CONFIG)

        # Test
        options = {}
        itinerary = forced_unbind_itinerary(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            options)
        call_reports = self.coordinator.execute_multiple_calls(itinerary)

        # Verify
        self.assertEqual(len(call_reports), 2)
        self.assertEqual(call_reports[0].call_request_tags, self.UNBIND_TAGS)
        self.assertEqual(call_reports[1].call_request_tags, self.AGENT_UNBIND_TAGS)
        for call in call_reports:
            self.assertNotEqual(call.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # run task #1 (actual delete)
        self.run_next()

        # verify bind marked deleted
        collection = Bind.get_collection()
        bind = collection.find_one(self.QUERY)
        self.assertTrue(bind is None)

        # run task #2 (notify consumer)
        self.run_next()

        # verify agent notified
        self.assertTrue(mock_agent.Consumer.unbind.called)

    @patch('pulp.server.managers.consumer.bind.BindManager.unbind', side_effect=Exception())
    def test_unbind_failed(self, mock_bind):

        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()

        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)

        # Test
        options = {}
        itinerary = unbind_itinerary(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            options)
        call_reports = self.coordinator.execute_multiple_calls(itinerary)

        # Verify
        self.assertEqual(len(call_reports), 3)
        for call in call_reports:
            self.assertNotEqual(call.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # run task #1 (actual bind)
        self.run_next()

        # run task #2 (notify consumer)
        self.run_next()

        # verify task #2 skipped
        request_id = call_reports[1].call_request_id
        call_report = self.coordinator.find_call_reports(call_request_id=request_id)[0]
        self.assertEqual(call_report.state, dispatch_constants.CALL_SKIPPED_STATE)

        # verify agent NOT notified
        self.assertFalse(mock_agent.Consumer.bind.called)

        # run task #3 (delete bind)
        self.run_next()

        # verify task #3 was skipped
        request_id = call_reports[2].call_request_id
        call_report = self.coordinator.find_call_reports(call_request_id=request_id)[0]
        self.assertEqual(call_report.state, dispatch_constants.CALL_SKIPPED_STATE)

        # verify bind still exists
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        self.assertTrue(bind is not None)

    def test_unbind_failed_on_consumer(self):

        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        bind = manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                            self.NOTIFY_AGENT, self.BINDING_CONFIG)

        # Test
        options = {}
        itinerary = unbind_itinerary(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            options)
        call_reports = self.coordinator.execute_multiple_calls(itinerary)

        # Verify
        self.assertEqual(len(call_reports), 3)
        for call in call_reports:
            self.assertNotEqual(call.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # run task #1 (actual unbind)
        self.run_next()

        # verify bind marked deleted
        collection = Bind.get_collection()
        bind = collection.find_one(self.QUERY)
        self.assertTrue(bind['deleted'])

        # run task #2 (notify consumer)
        self.run_next()

        # verify agent notified
        self.assertTrue(mock_agent.Consumer.unbind.called)

        # verify consumer request (pending)
        request_id = call_reports[1].call_request_id
        collection = Bind.get_collection()
        bind = collection.find_one(self.QUERY)
        self.assertTrue(bind is not None)
        actions = bind['consumer_actions']
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['id'], request_id)
        self.assertEqual(actions[0]['action'], Bind.Action.UNBIND)
        self.assertEqual(actions[0]['status'], Bind.Status.PENDING)
        self.assertTrue(isinstance(actions[0]['timestamp'], float))

        # simulated asynchronous task result
        report = DispatchReport()
        report.succeeded = False
        self.coordinator.complete_call_success(request_id, report.dict())

        # verify not found (marked deleted)
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 0)

        # run task #3 (bind actually deleted)
        self.run_next()

        # verify bind not deleted
        collection = Bind.get_collection()
        bind = collection.find_one(self.QUERY)
        self.assertTrue(bind is not None)
        actions = bind['consumer_actions']
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['id'], request_id)
        self.assertEqual(actions[0]['action'], Bind.Action.UNBIND)
        self.assertEqual(actions[0]['status'], Bind.Status.FAILED)
        self.assertTrue(isinstance(actions[0]['timestamp'], float))
