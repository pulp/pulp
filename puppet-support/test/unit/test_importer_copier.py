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
import unittest

from pulp.plugins.conduits.mixins import UnitAssociationCriteria

from pulp_puppet.common import constants
from pulp_puppet.importer import copier

class CopierTests(unittest.TestCase):

    def test_copy_units_all_units(self):
        # Setup
        conduit = mock.MagicMock()
        all_source_units = ['a', 'b', 'c'] # content is irrelevant
        conduit.get_source_units.return_value = all_source_units

        # Test
        copier.copy_units(conduit, None)

        # Verify
        self.assertEqual(1, conduit.get_source_units.call_count)
        call_args = conduit.get_source_units.call_args
        self.assertTrue('criteria' in call_args[1])
        self.assertTrue(isinstance(call_args[1]['criteria'], UnitAssociationCriteria))
        self.assertEqual(call_args[1]['criteria'].type_ids, [constants.TYPE_PUPPET_MODULE])

        self.assertEqual(len(all_source_units), conduit.associate_unit.call_count)
        self._assert_associated_units(conduit, all_source_units)

    def test_copy_units_only_specified(self):
        # Setup
        conduit = mock.MagicMock()
        specified_units = ['a', 'b']

        # Test
        copier.copy_units(conduit, specified_units)

        # Verify
        self.assertEqual(0, conduit.get_source_units.call_count)

        self.assertEqual(len(specified_units), conduit.associate_unit.call_count)
        self._assert_associated_units(conduit, specified_units)

    def _assert_associated_units(self, conduit, units):
        all_call_args = conduit.associate_unit.call_args_list
        for unit, call_args in zip(units, all_call_args):
            self.assertEqual(call_args[0][0], unit)
