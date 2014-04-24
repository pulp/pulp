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

import unittest

import mock

from pulp.server.async.active_queues import print_active_queues


class TestSubprocessActiveQueues(unittest.TestCase):
    """
    Test the subprocess_active_queues() function.
    """

    @mock.patch('pulp.server.async.active_queues.json')
    @mock.patch('pulp.server.async.active_queues.sys')
    @mock.patch('pulp.server.async.active_queues.controller')
    def test_subprocess_active_queues(self, controller, sys, json):
        """
        Test that subprocess_active_queues() makes the correct calls.
        """
        inspect = mock.Mock()
        active_queues = mock.Mock()
        dumps_result = mock.Mock()
        inspect.active_queues.return_value = active_queues
        controller.inspect.return_value = inspect
        json.dumps.return_value = dumps_result
        print_active_queues()
        controller.inspect.assert_called_once()
        inspect.active_queues.assert_called_once()
        json.dumps.assert_called_with(active_queues)
        sys.stdout.write.assert_called_with(dumps_result)
