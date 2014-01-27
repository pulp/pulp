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
This test module contains tests for the pulp.server.maintenance.monthly module.
"""

import unittest

import mock

from pulp.server.maintenance import monthly


class TestMain(unittest.TestCase):
    """
    Test the main() function.
    """
    @mock.patch('pulp.server.maintenance.monthly.RepoProfileApplicabilityManager.remove_orphans')
    def test_monthly_maintenance_calls_remove_orphans(self, remove_orphans):
        """
        Assert that the main() function calls remove_orphans.
        """
        monthly.monthly_maintenance()

        remove_orphans.assert_called_once_with()
