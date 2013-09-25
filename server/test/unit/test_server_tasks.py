# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
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
This module contains tests for the pulp.server.tasks module.
"""
import unittest

import mock

from pulp.server import tasks


class TestTask(unittest.TestCase):
    """
    Test the pulp.server.tasks.Task class.
    """
    @mock.patch('pulp.server.tasks.Task.apply_async', autospec=True)
    def test_apply_async_with_reservation_calls_apply_async(self, apply_async):
        """
        Assert that apply_async_with_reservation() calls Celery's apply_async.
        """
        some_args = [1, 'b', 'iii']
        some_kwargs = {'1': 'for the money', '2': 'for the show'}
        resource_id = 'three_to_get_ready'
        task = tasks.Task()

        task.apply_async_with_reservation(resource_id, *some_args, **some_kwargs)

        apply_async.assert_called_once_with(task, *some_args, **some_kwargs)


class TestCancel(unittest.TestCase):
    """
    Test the tasks.cancel() function.
    """
    @mock.patch('pulp.server.tasks.controller.revoke', autospec=True)
    def test_cancel(self, revoke):
        task_id = '1234abcd'

        tasks.cancel(task_id)

        revoke.assert_called_once_with(task_id, terminate=True)
