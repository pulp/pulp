# -*- coding: utf-8 -*-
#
# Copyright ©2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
"""
Tests for the pulp.server.db.model.dispatch module.
"""
import unittest

from pulp.server.db.model import dispatch


class TestTaskStatus(unittest.TestCase):
    """
    Test the TaskStatus class.
    """
    def test___init__(self):
        """
        Test the __init__() method.
        """
        task_id = 'a_task_id'
        queue = 'some_queue'
        tags = ['tag_1', 'tag_2']
        state = 'a state'

        ts = dispatch.TaskStatus(task_id, queue, tags, state)

        self.assertEqual(ts.task_id, task_id)
        self.assertEqual(ts.queue, queue)
        self.assertEqual(ts.tags, tags)
        self.assertEqual(ts.state, state)
        self.assertEqual(ts.result, None)
        self.assertEqual(ts.traceback, None)
        self.assertEqual(ts.start_time, None)
        self.assertEqual(ts.finish_time, None)

    def test___init___defaults(self):
        """
        Test the __init__() method with default values
        """
        task_id = 'a_task_id'
        queue = 'some_queue'

        ts = dispatch.TaskStatus(task_id, queue)

        self.assertEqual(ts.task_id, task_id)
        self.assertEqual(ts.queue, queue)
        self.assertEqual(ts.tags, [])
        self.assertEqual(ts.state, None)
        self.assertEqual(ts.result, None)
        self.assertEqual(ts.traceback, None)
        self.assertEqual(ts.start_time, None)
        self.assertEqual(ts.finish_time, None)
