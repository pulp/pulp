# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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

from pulp.bindings.responses import (Task, Response, STATE_RUNNING, STATE_WAITING,
    STATE_FINISHED, RESPONSE_REJECTED, RESPONSE_POSTPONED)
from pulp.client.commands.repo.status import status

# -- constants ----------------------------------------------------------------

TASK_TEMPLATE = {
    "exception": None,
    "call_request_group_id": 'default-group',
    "call_request_id": 'default-id',
    "call_request_tags": ['pulp:action:sync'],
    "reasons": [],
    "start_time": None,
    "traceback": None,
    "state": None,
    "finish_time": None,
    "schedule_id": None,
    "result": None,
    "progress": {},
    "response": None,
}

# -- test cases ---------------------------------------------------------------

class StatusTests(base.PulpClientTests):

    def setUp(self):
        super(StatusTests, self).setUp()
        self.renderer = mock.MagicMock()

    @mock.patch('pulp.client.commands.repo.status.status._display_task_status')
    def test_display_status(self, mock_display):
        # Setup
        task_list = []
        for i in range(0, 2):
            task = Task(TASK_TEMPLATE)
            task.task_id = 'task_%s' % i
            task_list.append(task)

        # Test
        status._display_status(self.context, self.renderer, task_list)

        # Verify
        self.assertEqual(2, mock_display.call_count)
        for i, call_args in enumerate(mock_display.call_args_list):
            self.assertEqual(call_args[0][0], self.context)
            self.assertEqual(call_args[0][1], self.renderer)
            self.assertEqual(call_args[0][2], 'task_%s' % i)

            expected_quiet = i > 0
            self.assertEqual(call_args[1]['quiet_waiting'], expected_quiet)

    @mock.patch('pulp.client.commands.repo.status.status._display_task_status')
    def test_display_with_keyboard_interrupt(self, mock_display):
        # Setup
        task_list = []
        for i in range(0, 3):
            task = Task(TASK_TEMPLATE)
            task.task_id = 'task_%s' % i
            task_list.append(task)

        # Side effect to simulate keyboard interrupt
        def interrupt(context, renderer, task_id, quiet_waiting=True):
            if task_id == 'task_1':
                raise KeyboardInterrupt()
            else:
                return task_id
        mock_display.side_effect = interrupt

        # Test
        status._display_status(self.context, self.renderer, task_list)

        # Verify
        self.assertEqual(2, mock_display.call_count) # not called for the third task
        for i, call_args in enumerate(mock_display.call_args_list):
            self.assertEqual(call_args[0][0], self.context)
            self.assertEqual(call_args[0][1], self.renderer)
            self.assertEqual(call_args[0][2], 'task_%s' % i)

            expected_quiet = i > 0
            self.assertEqual(call_args[1]['quiet_waiting'], expected_quiet)

    def test_display_status_rejected(self):
        # Setup
        rejected_task = Task(TASK_TEMPLATE)
        rejected_task.response = RESPONSE_REJECTED

        # Test
        status._display_status(self.context, self.renderer, [rejected_task])

        # Verify
        expected_tags = ['ctrl-c', 'rejected-msg', 'rejected-desc']
        self.assertEqual(expected_tags, self.prompt.get_write_tags())

    def test_display_status_postponed(self):
        # Setup
        postponed_task = Task(TASK_TEMPLATE)
        postponed_task.response = RESPONSE_POSTPONED
        postponed_task.state = STATE_WAITING

        # Test
        status._display_status(self.context, self.renderer, [postponed_task])

        # Verify
        expected_tags = ['ctrl-c', 'postponed']
        self.assertEqual(expected_tags, self.prompt.get_write_tags())

    @mock.patch('pulp.bindings.tasks.TasksAPI.get_task')
    @mock.patch('pulp.client.extensions.core.PulpPrompt.create_spinner')
    def test_internal_display_task_status(self, mock_create, mock_get):
        # Setup
        self.config['output']['poll_frequency_in_seconds'] = 0 # no need to wait

        # Make a mock spinner to track that it's called for each wait
        mock_spinner = mock.MagicMock()
        mock_create.return_value = mock_spinner

        # Side effect call to simulate polling a number of times before it completes
        def poll(task_id):
            task = Task(TASK_TEMPLATE)

            # Wait for the first 2 polls
            if mock_get.call_count < 3:
                task.state = STATE_WAITING

            # Running for the next 10
            elif mock_get.call_count < 13:
                task.state = STATE_RUNNING

            # Finally finish
            else:
                task.state = STATE_FINISHED

            return Response(200, task)

        mock_get.side_effect = poll

        self.task_id = 'ro'

        # Test
        status._display_task_status(self.context, self.renderer, self.task_id)

        # Verify
        self.assertEqual(13, mock_get.call_count)
        self.assertEqual(2, mock_spinner.next.call_count)
        self.assertEqual(11, self.renderer.display_report.call_count)

    @mock.patch('pulp.bindings.tasks.TasksAPI.get_task')
    @mock.patch('pulp.client.commands.repo.status.status._display_status')
    def test_display_task_status(self, mock_display, mock_get):
        """
        Simple test to make sure the pass through to _display_status is correct.
        """

        # Setup
        task = mock.MagicMock()
        mock_get.return_value = mock.MagicMock()
        mock_get.return_value.response_body = task

        task_id = 'fus'

        # Test
        status.display_task_status(self.context, self.renderer, task_id)

        # Verify
        self.assertEqual(1, mock_get.call_count)
        self.assertEqual(task_id, mock_get.call_args[0][0])

        self.assertEqual(1, mock_display.call_count)
        self.assertEqual(self.context, mock_display.call_args[0][0])
        self.assertEqual(self.renderer, mock_display.call_args[0][1])
        self.assertEqual([task], mock_display.call_args[0][2])

    @mock.patch('pulp.bindings.tasks.TaskGroupsAPI.get_task_group')
    @mock.patch('pulp.client.commands.repo.status.status._display_status')
    def test_display_group_status(self, mock_display, mock_get):
        """
        Simple test to make sure the pass through to _display_status is correct.
        """

        # Setup
        task_list = mock.MagicMock()
        mock_get.return_value = mock.MagicMock()
        mock_get.return_value.response_body = task_list

        task_group_id = 'fus'

        # Test
        status.display_group_status(self.context, self.renderer, task_group_id)

        # Verify
        self.assertEqual(1, mock_get.call_count)
        self.assertEqual(task_group_id, mock_get.call_args[0][0])

        self.assertEqual(1, mock_display.call_count)
        self.assertEqual(self.context, mock_display.call_args[0][0])
        self.assertEqual(self.renderer, mock_display.call_args[0][1])
        self.assertEqual(task_list, mock_display.call_args[0][2])
