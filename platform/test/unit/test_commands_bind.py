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

import base

from pulp.bindings import responses
from pulp.client.commands.consumer.bind import (OPTION_DISTRIBUTOR_ID, FLAG_FORCE,
                                                ConsumerBindCommand, ConsumerUnbindCommand)
from pulp.client.commands.options import OPTION_REPO_ID, OPTION_CONSUMER_ID
from pulp.client.commands.polling import PollingCommand
from pulp.common import tags
from pulp.devel.unit import task_simulator


class ConsumerBindCommandTests(base.PulpClientTests):

    def setUp(self):
        super(ConsumerBindCommandTests, self).setUp()

        self.command = ConsumerBindCommand(self.context)

        self.mock_poll = mock.MagicMock().poll
        self.command.poll = self.mock_poll

        self.mock_bind_binding = mock.MagicMock().bind
        self.mock_bind_binding.return_value = task_simulator.create_fake_task_response()
        self.bindings.bind.bind = self.mock_bind_binding

    def test_structure(self):
        self.assertTrue(isinstance(self.command, PollingCommand))

        self.assertTrue(OPTION_REPO_ID in self.command.options)
        self.assertTrue(OPTION_CONSUMER_ID in self.command.options)
        self.assertTrue(OPTION_DISTRIBUTOR_ID in self.command.options)
        self.assertEqual(3, len(self.command.options))

        self.assertEqual(self.command.method, self.command.run)

    def test_run(self):
        # Setup
        self.cli.add_command(self.command)

        # Test
        self.cli.run('bind --repo-id r1 --consumer-id c1 --distributor-id d1'.split())

        # Verify
        #   Call to binding with the data from the command
        self.assertEqual(1, self.mock_bind_binding.call_count)
        call_args = self.mock_bind_binding.call_args[0]
        self.assertEqual(call_args[0], 'c1')
        self.assertEqual(call_args[1], 'r1')
        self.assertEqual(call_args[2], 'd1')

        #   Poll call made with the correct value
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

        self.mock_poll = mock.MagicMock().poll
        self.command.poll = self.mock_poll

        self.mock_unbind_binding = mock.MagicMock().unbind
        self.mock_unbind_binding.return_value = task_simulator.create_fake_task_response()
        self.bindings.bind.unbind = self.mock_unbind_binding

    def test_structure(self):
        self.assertTrue(isinstance(self.command, PollingCommand))

        self.assertTrue(OPTION_REPO_ID in self.command.options)
        self.assertTrue(OPTION_CONSUMER_ID in self.command.options)
        self.assertTrue(OPTION_DISTRIBUTOR_ID in self.command.options)
        self.assertTrue(FLAG_FORCE in self.command.options)
        self.assertEqual(4, len(self.command.options))

        self.assertEqual(self.command.method, self.command.run)

    def test_run(self):
        # Setup
        self.cli.add_command(self.command)

        # Test
        self.cli.run('unbind --repo-id r1 --consumer-id c1 --distributor-id d1'.split())

        # Verify
        #   Call to binding with the data from the command
        self.assertEqual(1, self.mock_unbind_binding.call_count)
        call_args = self.mock_unbind_binding.call_args[0]
        self.assertEqual(call_args[0], 'c1')
        self.assertEqual(call_args[1], 'r1')
        self.assertEqual(call_args[2], 'd1')

        #   Poll call made with the correct value
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
