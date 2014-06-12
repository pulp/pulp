# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import mock

from pulp.devel.unit import base

from pulp.bindings import responses
from pulp.client.commands.consumer.bind import (
    OPTION_DISTRIBUTOR_ID, FLAG_FORCE, BindRelatedPollingCommand, ConsumerBindCommand,
    ConsumerUnbindCommand)
from pulp.client.commands.options import OPTION_REPO_ID, OPTION_CONSUMER_ID
from pulp.client.commands.polling import PollingCommand
from pulp.common import tags
from pulp.devel.unit import task_simulator


class BindRelatedPollingCommandTests(base.PulpClientTests):
    """
    Tests for the BindRelatedPollingCommand class.
    """
    @mock.patch('pulp.client.commands.polling.PollingCommand.failed')
    def test_failed(self, super_failed):
        """
        Test the failed() handler.
        """
        command = BindRelatedPollingCommand('name', 'description', mock.MagicMock(), self.context)
        task = mock.MagicMock()

        command.failed(task)

        super_failed.assert_called_once_with(task)

        self.assertEqual(self.prompt.get_write_tags(), ['error_message'])

    @mock.patch('pulp.client.commands.consumer.bind.BindRelatedPollingCommand.failed')
    @mock.patch('pulp.client.commands.polling.PollingCommand.succeeded')
    def test_succeeded_actually_failed(self, super_succeeded, failed):
        """
        Test the succeeded() handler for the case when the task actually failed.
        """
        command = BindRelatedPollingCommand('name', 'description', mock.MagicMock(), self.context)
        task = mock.MagicMock()
        task.result = {'succeeded': False}

        command.succeeded(task)

        failed.assert_called_once_with(task)
        self.assertEqual(super_succeeded.call_count, 0)

    @mock.patch('pulp.client.commands.consumer.bind.BindRelatedPollingCommand.failed')
    @mock.patch('pulp.client.commands.polling.PollingCommand.succeeded')
    def test_succeeded_actually_succeeded(self, super_succeeded, failed):
        """
        Test the succeeded() handler for the case when the task actually succeeded.
        """
        command = BindRelatedPollingCommand('name', 'description', mock.MagicMock(), self.context)
        task = mock.MagicMock()
        task.result = {'succeeded': True}

        command.succeeded(task)

        super_succeeded.assert_called_once_with(task)
        self.assertEqual(failed.call_count, 0)


class ConsumerBindCommandTests(base.PulpClientTests):

    def setUp(self):
        super(ConsumerBindCommandTests, self).setUp()

        self.command = ConsumerBindCommand(self.context)

        self.mock_poll = mock.MagicMock()
        self.command.poll = self.mock_poll

        self.mock_bind_binding = mock.MagicMock()
        self.mock_bind_binding.return_value = task_simulator.create_fake_task_response()
        self.bindings.bind.bind = self.mock_bind_binding

    def test_instance(self):
        """
        Make sure the ConsumerBindCommand is a BindRelatedPollingCommand.
        """
        self.assertTrue(isinstance(self.command, BindRelatedPollingCommand))

    def test_structure(self):
        self.assertTrue(isinstance(self.command, PollingCommand))

        self.assertTrue(OPTION_REPO_ID in self.command.options)
        self.assertTrue(OPTION_CONSUMER_ID in self.command.options)
        self.assertTrue(OPTION_DISTRIBUTOR_ID in self.command.options)
        self.assertEqual(4, len(self.command.options))  # these + background from PollingCommand

        self.assertEqual(self.command.method, self.command.run)

    def test_run(self):
        # Setup
        self.cli.add_command(self.command)

        # Test
        self.cli.run('bind --repo-id r1 --consumer-id c1 --distributor-id d1'.split())

        # Verify
        self.mock_bind_binding.assert_called_once_with('c1', 'r1', 'd1')

        # Poll call made with the correct value
        self.assertEqual(1, self.mock_poll.call_count)
        self.assertEqual(self.mock_poll.call_args[0][0],
                         self.mock_bind_binding.return_value.response_body)

    def test_task_header_bind(self):
        # Setup
        sim = task_simulator.TaskSimulator()

        task = sim.add_task_state('1', responses.STATE_FINISHED)
        task.tags = [tags.action_tag(tags.ACTION_BIND)]

        # Test
        self.command.task_header(task)

        # Verify
        self.assertEqual(self.prompt.get_write_tags(), ['bind-header'])

    def test_task_header_agent_bind(self):
        # Setup
        sim = task_simulator.TaskSimulator()

        task = sim.add_task_state('2', responses.STATE_FINISHED)
        task.tags = [tags.action_tag(tags.ACTION_AGENT_BIND)]

        # Test
        self.command.task_header(task)

        # Verify
        self.assertEqual(self.prompt.get_write_tags(), ['agent-bind-header'])


class ConsumerUnbindCommandTests(base.PulpClientTests):

    def setUp(self):
        super(ConsumerUnbindCommandTests, self).setUp()

        self.command = ConsumerUnbindCommand(self.context)

        self.mock_poll = mock.MagicMock()
        self.command.poll = self.mock_poll

        self.mock_unbind_binding = mock.MagicMock()
        self.mock_unbind_binding.return_value = task_simulator.create_fake_task_response()
        self.bindings.bind.unbind = self.mock_unbind_binding

    def test_instance(self):
        """
        Make sure the ConsumerUnbindCommand is a BindRelatedPollingCommand.
        """
        self.assertTrue(isinstance(self.command, BindRelatedPollingCommand))

    def test_structure(self):
        self.assertTrue(isinstance(self.command, PollingCommand))

        self.assertTrue(OPTION_REPO_ID in self.command.options)
        self.assertTrue(OPTION_CONSUMER_ID in self.command.options)
        self.assertTrue(OPTION_DISTRIBUTOR_ID in self.command.options)
        self.assertTrue(FLAG_FORCE in self.command.options)
        self.assertEqual(5, len(self.command.options))  # these + background from PollingCommand

        self.assertEqual(self.command.method, self.command.run)

    def test_run(self):
        # Setup
        self.cli.add_command(self.command)

        # Test
        self.cli.run('unbind --repo-id r1 --consumer-id c1 --distributor-id d1'.split())

        # Verify
        self.mock_unbind_binding.assert_called_once_with('c1', 'r1', 'd1', False)

        # Poll call made with the correct value
        self.assertEqual(1, self.mock_poll.call_count)
        self.assertEqual(self.mock_poll.call_args[0][0],
                         self.mock_unbind_binding.return_value.response_body)

    def test_task_header_unbind(self):
        # Setup
        sim = task_simulator.TaskSimulator()

        task = sim.add_task_state('1', responses.STATE_FINISHED)
        task.tags = [tags.action_tag(tags.ACTION_UNBIND)]

        # Test
        self.command.task_header(task)

        # Verify
        self.assertEqual(self.prompt.get_write_tags(), ['unbind-header'])

    def test_task_header_agent_unbind(self):
        # Setup
        sim = task_simulator.TaskSimulator()

        task = sim.add_task_state('2', responses.STATE_FINISHED)
        task.tags = [tags.action_tag(tags.ACTION_AGENT_UNBIND)]

        # Test
        self.command.task_header(task)

        # Verify
        self.assertEqual(self.prompt.get_write_tags(), ['agent-unbind-header'])

    def test_task_header_delete_binding(self):
        # Setup
        sim = task_simulator.TaskSimulator()

        task = sim.add_task_state('3', responses.STATE_FINISHED)
        task.tags = [tags.action_tag(tags.ACTION_DELETE_BINDING)]

        # Test
        self.command.task_header(task)

        # Verify
        self.assertEqual(self.prompt.get_write_tags(), ['delete-header'])
