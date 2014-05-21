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

import itertools
from unittest import TestCase

from mock import patch, Mock, ANY

from pulp.common import tags
from pulp.server.db.model.consumer import Bind
from pulp.server.managers.consumer.agent import AgentManager, Units
from pulp.server.exceptions import PulpExecutionException, PulpDataException, MissingResource
from pulp.plugins.profiler import Profiler, InvalidUnitsRequested
from pulp.plugins.loader import exceptions as plugin_exceptions
from pulp.plugins.model import Consumer as ProfiledConsumer


class TestAgentManager(TestCase):

    @patch('pulp.server.managers.consumer.agent.managers')
    @patch('pulp.server.managers.consumer.agent.Context')
    @patch('pulp.server.agent.direct.pulpagent.Consumer')
    def test_unregistered(self, mock_agent, mock_context, mock_factory):
        consumer = {'id': 'xyz'}
        mock_consumer_manager = Mock()
        mock_consumer_manager.get_consumer = Mock(return_value=consumer)
        mock_factory.consumer_manager = Mock(return_value=mock_consumer_manager)

        mock_context.return_value = {}

        # test manager

        agent_manager = AgentManager()
        consumer_id = 'abc'
        agent_manager.unregistered(consumer_id)

        # validations

        mock_context.assert_called_with(consumer)
        mock_agent.unregistered.assert_called_with(mock_context.return_value)

    @patch('pulp.server.managers.consumer.agent.uuid4')
    @patch('pulp.server.managers.consumer.agent.TaskStatusManager')
    @patch('pulp.server.managers.consumer.agent.AgentManager._bindings')
    @patch('pulp.server.managers.consumer.agent.managers')
    @patch('pulp.server.managers.consumer.agent.Context')
    @patch('pulp.server.agent.direct.pulpagent.Consumer')
    def test_bind(self, *mocks):

        mock_agent = mocks[0]
        mock_context = mocks[1]
        mock_factory = mocks[2]
        mock_bindings = mocks[3]
        mock_task_status_manager = mocks[4]
        mock_uuid = mocks[5]

        consumer = {'id': '1234'}
        mock_consumer_manager = Mock()
        mock_consumer_manager.get_consumer = Mock(return_value=consumer)
        mock_factory.consumer_manager = Mock(return_value=mock_consumer_manager)

        binding = {}
        mock_bind_manager = Mock()
        mock_bind_manager.get_bind = Mock(return_value=binding)
        mock_bind_manager.action_pending = Mock()
        mock_factory.consumer_bind_manager = Mock(return_value=mock_bind_manager)

        agent_bindings = []
        mock_bindings.return_value = agent_bindings

        task_id = '2345'
        mock_task = {'task_id': task_id}
        mock_task_status_manager.create_task_status = Mock(return_value=mock_task)

        mock_context.return_value = {}

        mock_uuid.return_value = task_id

        # test manager

        repo_id = '100'
        distributor_id = '200'
        options = {}
        agent_manager = AgentManager()
        task = agent_manager.bind(consumer['id'], repo_id, distributor_id, options)

        # validations

        task_tags = [
            tags.resource_tag(tags.RESOURCE_CONSUMER_TYPE, consumer['id']),
            tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
            tags.resource_tag(tags.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
            tags.action_tag(tags.ACTION_AGENT_BIND)
        ]

        mock_consumer_manager.get_consumer.assert_called_with(consumer['id'])
        mock_bind_manager.get_bind.assert_called_with(consumer['id'], repo_id, distributor_id)
        mock_bindings.assert_called_with([binding])

        mock_context.assert_called_with(
            consumer,
            task_id=task_id,
            action='bind',
            consumer_id=consumer['id'],
            repo_id=repo_id,
            distributor_id=distributor_id)

        self.assertEqual(task, mock_task)
        mock_task_status_manager.create_task_status.assert_called_with(task_id, 'agent', tags=task_tags)
        mock_agent.bind.assert_called_with(mock_context.return_value, agent_bindings, options)
        mock_bind_manager.action_pending.assert_called_with(
            consumer['id'], repo_id, distributor_id, Bind.Action.BIND, task_id)

    @patch('pulp.server.managers.consumer.agent.uuid4')
    @patch('pulp.server.managers.consumer.agent.TaskStatusManager')
    @patch('pulp.server.managers.consumer.agent.AgentManager._unbindings')
    @patch('pulp.server.managers.consumer.agent.managers')
    @patch('pulp.server.managers.consumer.agent.Context')
    @patch('pulp.server.agent.direct.pulpagent.Consumer')
    def test_unbind(self, *mocks):
        mock_agent = mocks[0]
        mock_context = mocks[1]
        mock_factory = mocks[2]
        mock_unbindings = mocks[3]
        mock_task_status_manager = mocks[4]
        mock_uuid = mocks[5]

        consumer = {'id': '1234'}
        mock_consumer_manager = Mock()
        mock_consumer_manager.get_consumer = Mock(return_value=consumer)
        mock_factory.consumer_manager = Mock(return_value=mock_consumer_manager)

        repo_id = '100'
        distributor_id = '200'
        binding = {'repo_id': repo_id, 'distributor_id': distributor_id}
        mock_bind_manager = Mock()
        mock_bind_manager.action_pending = Mock()
        mock_factory.consumer_bind_manager = Mock(return_value=mock_bind_manager)

        agent_bindings = []
        mock_unbindings.return_value = agent_bindings

        task_id = '2345'
        mock_task = {'task_id': task_id}
        mock_task_status_manager.create_task_status = Mock(return_value=mock_task)

        mock_context.return_value = {}

        mock_uuid.return_value = task_id

        # test manager

        options = {}
        agent_manager = AgentManager()
        task = agent_manager.unbind(consumer['id'], repo_id, distributor_id, options)

        # validations

        task_tags = [
            tags.resource_tag(tags.RESOURCE_CONSUMER_TYPE, consumer['id']),
            tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
            tags.resource_tag(tags.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
            tags.action_tag(tags.ACTION_AGENT_UNBIND)
        ]

        mock_consumer_manager.get_consumer.assert_called_with(consumer['id'])
        mock_unbindings.assert_called_with([binding])

        mock_context.assert_called_with(
            consumer,
            task_id=task_id,
            action='unbind',
            consumer_id=consumer['id'],
            repo_id=repo_id,
            distributor_id=distributor_id)

        self.assertEqual(task, mock_task)
        mock_task_status_manager.create_task_status.assert_called_with(task_id, 'agent', tags=task_tags)
        mock_agent.unbind.assert_called_with(mock_context.return_value, agent_bindings, options)
        mock_bind_manager.action_pending.assert_called_with(
            consumer['id'], repo_id, distributor_id, Bind.Action.UNBIND, task_id)

    @patch('pulp.server.managers.consumer.agent.uuid4')
    @patch('pulp.server.managers.consumer.agent.TaskStatusManager')
    @patch('pulp.server.managers.consumer.agent.AgentManager._profiled_consumer')
    @patch('pulp.server.managers.consumer.agent.AgentManager._profiler')
    @patch('pulp.server.managers.consumer.agent.managers')
    @patch('pulp.server.managers.consumer.agent.Context')
    @patch('pulp.server.agent.direct.pulpagent.Content')
    def test_install_content(self, *mocks):
        mock_agent = mocks[0]
        mock_context = mocks[1]
        mock_factory = mocks[2]
        mock_get_profiler = mocks[3]
        mock_get_profiled_consumer = mocks[4]
        mock_task_status_manager = mocks[5]
        mock_uuid = mocks[6]

        unit = {'type_id': 'xyz', 'unit_key': {}}

        consumer = {'id': '1234'}
        mock_consumer_manager = Mock()
        mock_consumer_manager.get_consumer = Mock(return_value=consumer)
        mock_factory.consumer_manager = Mock(return_value=mock_consumer_manager)

        mock_get_profiled_consumer.return_value = consumer

        mock_profiler = Mock()
        mock_profiler.install_units = Mock(return_value=[unit])
        mock_get_profiler.return_value = (mock_profiler, {})

        task_id = '2345'
        mock_task = {'task_id': task_id}
        mock_task_status_manager.create_task_status = Mock(return_value=mock_task)

        mock_context.return_value = {}

        mock_uuid.return_value = task_id

        # test manager

        options = {'a': 1}
        agent_manager = AgentManager()
        task = agent_manager.install_content(consumer['id'], [unit], options)

        # validations

        task_tags = [
            tags.resource_tag(tags.RESOURCE_CONSUMER_TYPE, consumer['id']),
            tags.action_tag(tags.ACTION_AGENT_UNIT_INSTALL)
        ]

        self.assertEqual(task, mock_task)
        mock_consumer_manager.get_consumer.assert_called_with(consumer['id'])
        mock_context.assert_called_with(consumer, task_id=task_id, consumer_id=consumer['id'])
        mock_task_status_manager.create_task_status.assert_called_with(task_id, 'agent', tags=task_tags)
        mock_profiler.install_units.assert_called_with(consumer, [unit], options, {}, ANY)
        mock_agent.install.assert_called_with(mock_context.return_value, [unit], options)

    @patch('pulp.server.managers.consumer.agent.uuid4')
    @patch('pulp.server.managers.consumer.agent.TaskStatusManager')
    @patch('pulp.server.managers.consumer.agent.AgentManager._profiled_consumer')
    @patch('pulp.server.managers.consumer.agent.AgentManager._profiler')
    @patch('pulp.server.managers.consumer.agent.managers')
    @patch('pulp.server.managers.consumer.agent.Context')
    @patch('pulp.server.agent.direct.pulpagent.Content')
    def test_update_content(self, *mocks):
        mock_agent = mocks[0]
        mock_context = mocks[1]
        mock_factory = mocks[2]
        mock_get_profiler = mocks[3]
        mock_get_profiled_consumer = mocks[4]
        mock_task_status_manager = mocks[5]
        mock_uuid = mocks[6]

        unit = {'type_id': 'xyz', 'unit_key': {}}

        consumer = {'id': '1234'}
        mock_consumer_manager = Mock()
        mock_consumer_manager.get_consumer = Mock(return_value=consumer)
        mock_factory.consumer_manager = Mock(return_value=mock_consumer_manager)

        mock_get_profiled_consumer.return_value = consumer

        mock_profiler = Mock()
        mock_profiler.update_units = Mock(return_value=[unit])
        mock_get_profiler.return_value = (mock_profiler, {})

        task_id = '2345'
        mock_task = {'task_id': task_id}
        mock_task_status_manager.create_task_status = Mock(return_value=mock_task)

        mock_context.return_value = {}

        mock_uuid.return_value = task_id

        # test manager

        options = {'a': 1}
        agent_manager = AgentManager()
        task = agent_manager.update_content(consumer['id'], [unit], options)

        # validations

        task_tags = [
            tags.resource_tag(tags.RESOURCE_CONSUMER_TYPE, consumer['id']),
            tags.action_tag(tags.ACTION_AGENT_UNIT_UPDATE)
        ]

        self.assertEqual(task, mock_task)
        mock_consumer_manager.get_consumer.assert_called_with(consumer['id'])
        mock_context.assert_called_with(consumer, task_id=task_id, consumer_id=consumer['id'])
        mock_task_status_manager.create_task_status.assert_called_with(task_id, 'agent', tags=task_tags)
        mock_profiler.update_units.assert_called_with(consumer, [unit], options, {}, ANY)
        mock_agent.update.assert_called_with(mock_context.return_value, [unit], options)

    @patch('pulp.server.managers.consumer.agent.uuid4')
    @patch('pulp.server.managers.consumer.agent.TaskStatusManager')
    @patch('pulp.server.managers.consumer.agent.AgentManager._profiled_consumer')
    @patch('pulp.server.managers.consumer.agent.AgentManager._profiler')
    @patch('pulp.server.managers.consumer.agent.managers')
    @patch('pulp.server.managers.consumer.agent.Context')
    @patch('pulp.server.agent.direct.pulpagent.Content')
    def test_uninstall_content(self, *mocks):
        mock_agent = mocks[0]
        mock_context = mocks[1]
        mock_factory = mocks[2]
        mock_get_profiler = mocks[3]
        mock_get_profiled_consumer = mocks[4]
        mock_task_status_manager = mocks[5]
        mock_uuid = mocks[6]

        unit = {'type_id': 'xyz', 'unit_key': {}}

        consumer = {'id': '1234'}
        mock_consumer_manager = Mock()
        mock_consumer_manager.get_consumer = Mock(return_value=consumer)
        mock_factory.consumer_manager = Mock(return_value=mock_consumer_manager)

        mock_get_profiled_consumer.return_value = consumer

        mock_profiler = Mock()
        mock_profiler.uninstall_units = Mock(return_value=[unit])
        mock_get_profiler.return_value = (mock_profiler, {})

        task_id = '2345'
        mock_task = {'task_id': task_id}
        mock_task_status_manager.create_task_status = Mock(return_value=mock_task)

        mock_context.return_value = {}

        mock_uuid.return_value = task_id

        # test manager

        options = {'a': 1}
        agent_manager = AgentManager()
        task = agent_manager.uninstall_content(consumer['id'], [unit], options)

        # validations

        task_tags = [
            tags.resource_tag(tags.RESOURCE_CONSUMER_TYPE, consumer['id']),
            tags.action_tag(tags.ACTION_AGENT_UNIT_UNINSTALL)
        ]

        self.assertEqual(task, mock_task)
        mock_consumer_manager.get_consumer.assert_called_with(consumer['id'])
        mock_context.assert_called_with(consumer, task_id=task_id, consumer_id=consumer['id'])
        mock_task_status_manager.create_task_status.assert_called_with(task_id, 'agent', tags=task_tags)
        mock_profiler.uninstall_units.assert_called_with(consumer, [unit], options, {}, ANY)
        mock_agent.uninstall.assert_called_with(mock_context.return_value, [unit], options)

    @patch('pulp.server.managers.consumer.agent.managers')
    @patch('pulp.server.managers.consumer.agent.Context')
    @patch('pulp.server.managers.consumer.agent.PulpAgent')
    def test_cancel(self, agent, context, mock_factory):
        consumer = {'id': 'xyz'}
        mock_consumer_manager = Mock()
        mock_consumer_manager.get_consumer = Mock(return_value=consumer)
        mock_factory.consumer_manager = Mock(return_value=mock_consumer_manager)

        mock_context = Mock()
        mock_context.uuid = 'test-uuid'
        mock_context.url = 'http://broker.com'
        context.return_value = mock_context

        mock_agent = Mock()
        agent.return_value = mock_agent

        # test manager

        task_id = '1234'
        agent_manager = AgentManager()
        consumer_id = 'abc'
        agent_manager.cancel_request(consumer_id, task_id)

        # validations

        mock_agent.cancel.assert_called_with(mock_context, task_id)

    def test_invoke_plugin(self):
        method = Mock()
        args = 1, 2, 3
        kwargs = {'a': 1, 'b': 2}
        # test manager
        AgentManager._invoke_plugin(method, *args, **kwargs)
        # validate
        method.assert_called_once_with(*args, **kwargs)

    def test_invoke_plugin_invalid_units_raised(self):
        method = Mock(side_effect=InvalidUnitsRequested([], ''))
        self.assertRaises(PulpDataException, AgentManager._invoke_plugin, method)

    def test_invoke_plugin_invalid_exception_raised(self):
        method = Mock(side_effect=Exception())
        self.assertRaises(PulpExecutionException, AgentManager._invoke_plugin, method)

    @patch('pulp.server.managers.consumer.agent.plugin_api')
    def test_find_profiler(self, mock_plugins):
        type_id = '2344'
        plugin = Mock()
        mock_plugins.get_profiler_by_type.return_value = (plugin, {})

        # test manager

        _plugin, cfg = AgentManager._profiler(type_id)

        # validation

        mock_plugins.get_profiler_by_type.assert_called_with(type_id)
        self.assertEqual(plugin, _plugin)
        self.assertEqual(cfg, {})

    @patch('pulp.server.managers.consumer.agent.plugin_api')
    def test_find_profiler_not_found(self, mock_plugins):
        type_id = '2344'
        mock_plugins.get_profiler_by_type.side_effect = plugin_exceptions.PluginNotFound()

        # test manager

        plugin, cfg = AgentManager._profiler(type_id)

        # validation

        mock_plugins.get_profiler_by_type.assert_called_with(type_id)
        self.assertTrue(isinstance(plugin, Profiler))
        self.assertEqual(cfg, {})

    @patch('pulp.server.managers.consumer.agent.managers')
    def test_profiled_consumer(self, mock_factory):
        consumer_id = '2345'
        type_id = 123
        profile = {'a': 1}
        profiles = [{'content_type': type_id, 'profile': profile}]
        mock_profile_manager = Mock()
        mock_profile_manager.get_profiles = Mock(return_value=profiles)
        mock_factory.consumer_profile_manager = Mock(return_value=mock_profile_manager)

        # test manager

        profiled = AgentManager._profiled_consumer(consumer_id)

        # validation

        mock_profile_manager.get_profiles.assert_called_once_with(consumer_id)
        self.assertTrue(isinstance(profiled, ProfiledConsumer))
        self.assertEqual(profiled.id, consumer_id)
        self.assertEqual(profiled.profiles, {type_id: profile})

    @patch('pulp.server.managers.consumer.agent.managers')
    def test_get_agent_bindings(self, mock_factory):
        bind_payload = {'a': 1, 'b': 2}
        distributor = {'distributor_type_id': '3838'}
        mock_distributor_manager = Mock()
        mock_distributor_manager.get_distributor = Mock(return_value=distributor)
        mock_distributor_manager.create_bind_payload = Mock(return_value=bind_payload)
        mock_factory.repo_distributor_manager = Mock(return_value=mock_distributor_manager)

        # test manager

        bindings = [
            {'consumer_id': '10', 'repo_id': '20', 'distributor_id': '30', 'binding_config': {}},
            {'consumer_id': '40', 'repo_id': '50', 'distributor_id': '60', 'binding_config': {}},
        ]
        agent_bindings = AgentManager._bindings(bindings)

        # validation

        for binding in bindings:
            mock_distributor_manager.get_distributor.assert_any_call(
                binding['repo_id'], binding['distributor_id'])
            mock_distributor_manager.create_bind_payload.assert_any_call(
                binding['repo_id'], binding['distributor_id'], binding['binding_config'])

        self.assertEqual(len(agent_bindings), 2)
        for binding, agent_binding in itertools.izip(bindings, agent_bindings):
            self.assertEqual(binding['repo_id'], agent_binding['repo_id'])
            self.assertEqual(distributor['distributor_type_id'], agent_binding['type_id'])
            self.assertEqual(bind_payload, agent_binding['details'])

    @patch('pulp.server.managers.consumer.agent.managers')
    def test_get_agent_unbindings(self, mock_factory):
        distributor = {'distributor_type_id': '3838'}
        mock_distributor_manager = Mock()
        mock_distributor_manager.get_distributor = Mock(return_value=distributor)
        mock_factory.repo_distributor_manager = Mock(return_value=mock_distributor_manager)

        # test manager

        bindings = [
            {'consumer_id': '10', 'repo_id': '20', 'distributor_id': '30', 'binding_config': {}},
            {'consumer_id': '40', 'repo_id': '50', 'distributor_id': '60', 'binding_config': {}},
        ]
        agent_bindings = AgentManager._unbindings(bindings)

        # validation

        for binding in bindings:
            mock_distributor_manager.get_distributor.assert_any_call(
                binding['repo_id'], binding['distributor_id'])

        self.assertEqual(len(agent_bindings), 2)
        for binding, agent_binding in itertools.izip(bindings, agent_bindings):
            self.assertEqual(binding['repo_id'], agent_binding['repo_id'])
            self.assertEqual(distributor['distributor_type_id'], agent_binding['type_id'])

    @patch('pulp.server.managers.repo.distributor.RepoDistributorManager')
    def test_get_agent_unbindings_distributor_deleted(self, mock_repo_distributor_manager):
        # Test that AgentManager._unbindings does not raise an exception
        # when the distributor is deleted and returns None as the distributor_type_id.
        def test_get_distributor():
            raise MissingResource()
        mock_repo_distributor_manager.get_distributor = test_get_distributor

        # test
        bindings = [
            {'consumer_id': '10', 'repo_id': '20', 'distributor_id': '30', 'binding_config': {}},
            {'consumer_id': '40', 'repo_id': '50', 'distributor_id': '60', 'binding_config': {}},
        ]
        agent_bindings = AgentManager._unbindings(bindings)

        # validation
        self.assertEqual(len(agent_bindings), 2)
        for binding, agent_binding in itertools.izip(bindings, agent_bindings):
            self.assertEqual(binding['repo_id'], agent_binding['repo_id'])
            self.assertEqual(None, agent_binding['type_id'])


class TestUnits(TestCase):

    def test_collation(self):
        units = [
            {'type_id': '10', 'unit_key': {'A': 1}},
            {'type_id': '10', 'unit_key': {'A': 2}},
            {'type_id': '20', 'unit_key': {'B': 10}},
            {'type_id': '30', 'unit_key': {'B': 20}},
            {'type_id': '30', 'unit_key': {'B': 30}},
        ]

        # test units

        collated = Units(units)

        # validation

        self.assertEqual(len(collated), 3)

        # type_id: 10 collated
        type_id = '10'
        self.assertEqual(len(collated[type_id]), 2)
        self.assertEqual(collated[type_id], units[0:2])

        # type_id: 20 collated
        type_id = '20'
        self.assertEqual(len(collated[type_id]), 1)
        self.assertEqual(collated[type_id], units[2:3])

        # type_id: 30 collated
        type_id = '30'
        self.assertEqual(len(collated[type_id]), 2)
        self.assertEqual(collated[type_id], units[3:])
