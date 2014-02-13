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

import unittest

import mock

from pulp.bindings.responses import Response, Task
from pulp.devel.unit import task_simulator
from pulp.devel.unit.task_simulator import TaskSimulator


class TaskSimulatorTests(unittest.TestCase):

    def test_install(self):
        """
        Tests the correct API in the bindings is replaced by the simulator.
        """

        # Test
        mock_bindings = mock.MagicMock()
        sim = TaskSimulator()
        sim.install(mock_bindings)

        # Verify
        self.assertEqual(sim, mock_bindings.tasks)

    def test_add_task_state(self):
        # Setup
        task_id = '123'
        state = 'running'
        response = 'success'
        progress_report = '1/10'

        # Test
        sim = TaskSimulator()
        task = sim.add_task_state(task_id, state, progress_report=progress_report)

        # Verify
        self.assertTrue(task_id in sim.ordered_task_ids)
        self.assertTrue(task_id in sim.tasks_by_id)
        self.assertTrue(1, len(sim.tasks_by_id[task_id]))

        self.assertEqual(task.task_id, task_id)
        self.assertEqual(task.state, state)
        self.assertEqual(task.progress_report, progress_report)

    def test_add_task_states(self):
        # Setup
        task_id = '123'
        states = ['waiting', 'running']


        # Test
        sim = TaskSimulator()
        sim.add_task_states(task_id, states)

        # Verify
        self.assertTrue(task_id in sim.ordered_task_ids)
        self.assertTrue(task_id in sim.tasks_by_id)
        self.assertTrue(len(states), len(sim.tasks_by_id[task_id]))

        # Stored in reverse order
        states.reverse()
        for index, state in enumerate(states):
            task = sim.tasks_by_id[task_id][index]
            self.assertEqual(task.state, state)

    def test_get_task(self):
        # Setup
        task_id = '123'
        states = ['waiting', 'running', 'success']

        sim = TaskSimulator()
        sim.add_task_states(task_id, states)

        # Test & Verify
        for state in states:
            task = sim.get_task(task_id).response_body
            self.assertEqual(task.state, state)

        self.assertEqual(0, len(sim.tasks_by_id[task_id]))

    def test_get_all_tasks(self):
        # Setup
        sim = TaskSimulator()
        for i in range(0, 3):
            task_id = 'task-%s' % i
            states = ['state-%s' % i]
            sim.add_task_states(task_id, states)

        # Test
        all_tasks = sim.get_all_tasks().response_body

        # Order is important here, they should be returned in the same order added
        for i in range(0, 3):
            task = all_tasks[i]
            self.assertEqual(task.task_id, 'task-%s' % i)

    def test_create_fake_task(self):
        # Test
        response = task_simulator.create_fake_task_response()

        # Verify
        self.assertTrue(isinstance(response, Response))
        self.assertTrue(isinstance(response.response_body, Task))
