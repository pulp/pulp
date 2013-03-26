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

from pulp.bindings.responses import (STATE_WAITING, STATE_CANCELED, STATE_ERROR, STATE_FINISHED,
                                     STATE_RUNNING, STATE_SKIPPED, RESPONSE_POSTPONED, RESPONSE_REJECTED)
from pulp.client.commands.polling import PollingCommand, RESULT_ABORTED, RESULT_REJECTED, FLAG_BACKGROUND, RESULT_BACKGROUND
from pulp.devel.unit.task_simulator import TaskSimulator


def noop(**kwargs):
    # Dummy method to pass to the command when it is instantiated
    pass


class PollingCommandTests(base.PulpClientTests):

    def setUp(self):
        super(PollingCommandTests, self).setUp()

        self.command = PollingCommand('poll', 'desc', noop, self.context, poll_frequency_in_seconds=0)

    def test_init_load_poll_frequency(self):
        # Test
        command = PollingCommand('poll', 'desc', noop, self.context)

        # Verify
        self.assertEqual(.5, command.poll_frequency_in_seconds)  # from test-override-admin.conf

    @mock.patch('time.sleep')
    def test_poll_single_task(self, mock_sleep):
        """
        Task Count: 1
        Statuses: None; normal progression of waiting to running to completed
        Result: Success

        This test verifies the sleep and progress callback calls, which will be omitted
        in most other tests cases where appropriate.
        """

        # Setup
        sim = TaskSimulator()
        sim.install(self.bindings)

        task_id = '123'
        state_progression = [STATE_WAITING,
                             STATE_WAITING,
                             STATE_RUNNING,
                             STATE_RUNNING,
                             STATE_FINISHED]
        sim.add_task_states(task_id, state_progression)

        mock_progress_call = mock.MagicMock().progress
        self.command.progress = mock_progress_call

        # Test
        task_list = sim.get_all_tasks().response_body
        completed_tasks = self.command.poll(task_list, {})

        # Verify

        # The "header" tag should not be present since no headers are needed for single tasks

        expected_tags = ['abort', 'waiting', 'spinner', 'waiting', 'spinner', 'succeeded']
        self.assertEqual(self.prompt.get_write_tags(), expected_tags)

        self.assertEqual(4, mock_sleep.call_count) # 2 for waiting, 2 for running
        self.assertEqual(mock_sleep.call_args_list[0][0][0], 0)  # frequency passed to sleep

        self.assertEqual(3, mock_progress_call.call_count) # 2 running, 1 final

        self.assertTrue(isinstance(completed_tasks, list))
        self.assertEqual(1, len(completed_tasks))
        self.assertEqual(STATE_FINISHED, completed_tasks[0].state)

    def test_poll_task_list(self):
        """
        Task Count: 3
        Statuses: None; normal progression
        Result: All Success
        """

        # Setup
        sim = TaskSimulator()
        sim.install(self.bindings)

        states_1 = [STATE_WAITING, STATE_RUNNING, STATE_FINISHED]
        states_2 = [STATE_WAITING, STATE_WAITING, STATE_RUNNING, STATE_FINISHED]
        states_3 = [STATE_WAITING, STATE_RUNNING, STATE_RUNNING, STATE_RUNNING, STATE_FINISHED]

        sim.add_task_states('1', states_1)
        sim.add_task_states('2', states_2)
        sim.add_task_states('3', states_3)

        # Test
        task_list = sim.get_all_tasks().response_body
        completed_tasks = self.command.poll(task_list, {})

        expected_tags = ['abort', # default, always displayed
                         'header', 'waiting', 'spinner', 'succeeded', # states_1
                         'header', 'waiting', 'spinner', 'waiting', 'spinner', 'succeeded', # states_2
                         'header', 'waiting', 'spinner', 'succeeded', # states_3
                         ]
        found_tags = self.prompt.get_write_tags()
        self.assertEqual(expected_tags, found_tags)

        self.assertTrue(isinstance(completed_tasks, list))
        self.assertEqual(3, len(completed_tasks))
        for i in range(0, 3):
            self.assertEqual(STATE_FINISHED, completed_tasks[i].state)

    def test_poll_background(self):
        # Setup
        sim = TaskSimulator()
        sim.add_task_state('1', STATE_FINISHED)

        # Test
        task_list = sim.get_all_tasks().response_body
        result = self.command.poll(task_list, {FLAG_BACKGROUND.keyword : True})

        # Verify
        self.assertEqual(result, RESULT_BACKGROUND)

    def test_poll_empty_list(self):
        # Test
        completed_tasks = self.command.poll([], {})

        # Verify
        #   The poll command shouldn't output anything and instead just end.
        self.assertEqual(0, len(self.prompt.get_write_tags()))
        self.assertTrue(isinstance(completed_tasks, list))
        self.assertEqual(0, len(completed_tasks))

    def test_poll_rejected(self):
        """
        Task Count: 2
        Statuses: Rejected (according to server behavior, all will be rejected if one is)
        """

        # Setup
        sim = TaskSimulator()
        sim.install(self.bindings)

        sim.add_task_state('1', STATE_ERROR, response=RESPONSE_REJECTED)
        sim.add_task_state('2', STATE_ERROR, response=RESPONSE_REJECTED)

        # Test
        task_list = sim.get_all_tasks().response_body
        completed_tasks = self.command.poll(task_list, {})

        # Verify
        self.assertEqual(completed_tasks, RESULT_REJECTED)

        self.assertEqual(self.prompt.get_write_tags(), ['rejected'])

    def test_failed_task(self):
        """
        Task Count: 3
        Statuses: None, tasks will run to completion
        Results: 1 Success, 1 Failed, 1 Skipped
        """

        # Setup
        sim = TaskSimulator()
        sim.install(self.bindings)

        states_1 = [STATE_WAITING, STATE_FINISHED]
        states_2 = [STATE_WAITING, STATE_ERROR]
        states_3 = [STATE_WAITING, STATE_SKIPPED]

        sim.add_task_states('1', states_1)
        sim.add_task_states('2', states_2)
        sim.add_task_states('3', states_3)

        # Test
        task_list = sim.get_all_tasks().response_body
        completed_tasks = self.command.poll(task_list, {})

        # Verify
        self.assertTrue(isinstance(completed_tasks, list))
        self.assertEqual(3, len(completed_tasks))

        expected_tags = ['abort',
                         'header', 'waiting', 'spinner', 'succeeded', # states_1
                         'header', 'waiting', 'spinner', 'failed', 'failed_exception', # states_2
                         'header', 'waiting', 'spinner', # states_3
                         ]
        self.assertEqual(expected_tags, self.prompt.get_write_tags())

    def test_cancelled_task(self):
        """
        Task Count: 1
        Statuses: Cancelled after 2 in progress polls
        Results: 1 Cancelled
        """

        # Setup
        sim = TaskSimulator()
        sim.install(self.bindings)

        states = [STATE_WAITING, STATE_RUNNING, STATE_RUNNING, STATE_CANCELED]
        sim.add_task_states('1', states)

        # Test
        task_list = sim.get_all_tasks().response_body
        completed_tasks = self.command.poll(task_list, {})

        # Verify
        self.assertTrue(isinstance(completed_tasks, list))
        self.assertEqual(1, len(completed_tasks))

        expected_tags = ['abort', 'waiting', 'spinner', 'cancelled']
        self.assertEqual(expected_tags, self.prompt.get_write_tags())

    def test_postponed_task(self):
        """
        Task Count: 1
        Statuses: Postponed (test will eventually run it)
        Results: 1 Success
        """

        # Setup
        sim = TaskSimulator()
        sim.install(self.bindings)

        # Remain postponed for two polls and then runs successfully
        sim.add_task_state('1', STATE_WAITING, response=RESPONSE_POSTPONED)
        sim.add_task_state('1', STATE_WAITING, response=RESPONSE_POSTPONED)
        states = [STATE_RUNNING, STATE_FINISHED]
        sim.add_task_states('1', states)

        # Test
        task_list = sim.get_all_tasks().response_body
        completed_tasks = self.command.poll(task_list, {})

        # Verify
        self.assertTrue(isinstance(completed_tasks, list))
        self.assertEqual(1, len(completed_tasks))

        expected_tags = ['abort', 'postponed', 'spinner', 'postponed', 'spinner', 'succeeded']
        self.assertEqual(expected_tags, self.prompt.get_write_tags())

    def test_keyboard_interrupt(self):
        # Setup
        mock_poll_call = mock.MagicMock()._poll_task
        mock_poll_call.side_effect = KeyboardInterrupt()
        self.command._poll_task = mock_poll_call

        sim = TaskSimulator()
        sim.install(self.bindings)

        sim.add_task_state('1', STATE_WAITING)

        # Test
        task_list = sim.get_all_tasks().response_body
        result = self.command.poll(task_list, {})

        # Verify
        self.assertEqual(result, RESULT_ABORTED)

        self.assertEqual(['abort'], self.prompt.get_write_tags())
