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

import os
import sys
import unittest

import mock

sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)),
    '../../extensions/admin/'))
from pulp_orphan import pulp_cli


class TestOrphanSection(unittest.TestCase):
    def setUp(self):
        self.section = pulp_cli.OrphanSection(mock.MagicMock())

    def test_initialize(self):
        mock_context = mock.MagicMock()
        pulp_cli.initialize(mock_context)

        self.assertEqual(mock_context.cli.add_section.call_count, 1)
        self.assertTrue(isinstance(mock_context.cli.add_section.call_args[0][0],
            pulp_cli.OrphanSection))

    def test_adds_commands(self):
        self.assertEqual(len(self.section.commands), 2)
