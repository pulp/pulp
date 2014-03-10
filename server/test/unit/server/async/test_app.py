# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
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
Tests for the pulp.server.async.app module.
"""
import unittest

import mock

from pulp.server.async import app


class TestInitializeWorker(unittest.TestCase):
    """
    Test the initialize_worker() function.
    """
    @mock.patch('pulp.server.async.tasks.babysit')
    @mock.patch('pulp.server.initialization.initialize')
    def test_initialize_worker(self, initialize, babysit):
        """
        Test that initialize_worker() makes the correct calls.
        """
        app.initialize_worker()

        # initialize() and babysit() should each have been called with no args
        initialize.assert_called_once_with()
        babysit.assert_called_once_with()