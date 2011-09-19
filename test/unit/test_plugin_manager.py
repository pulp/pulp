#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Python
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import pulp.server.content.manager as content_manager
import pulp.server.content.types.database as types_db
from pulp.server.content.types.model import TypeDefinition
import pulp.server.managers.plugin as plugin_manager

# -- mocks --------------------------------------------------------------------

class MockImporter:
    pass

class MockDistributor:
    pass

# -- test cases ---------------------------------------------------------------

class PluginManagerTests(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)

        content_manager._create_manager()

        # Configure content manager
        content_manager._MANAGER.add_importer('MockImporter', 1, MockImporter, None)
        content_manager._MANAGER.add_distributor('MockDistributor', 1, MockDistributor, None)

        # Create the manager instance to test
        self.manager = plugin_manager.PluginManager()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)

        # Reset content manager
        content_manager._MANAGER.remove_importer('MockImporter', 1)
        content_manager._MANAGER.remove_distributor('MockDistributor', 1)

    def test_types(self):
        """
        Tests retrieving all types in the database.
        """

        # Setup
        type_def_1 = TypeDefinition('type-1', 'Type 1', 'Type 1', [], [], [])
        type_def_2 = TypeDefinition('type-2', 'Type 2', 'Type 2', [], [], [])

        types_db._create_or_update_type(type_def_1)
        types_db._create_or_update_type(type_def_2)

        # Test
        found_defs = self.manager.types()

        # Verify
        self.assertEqual(2, len(found_defs))

        for type_def in [type_def_1, type_def_2]:
            found_def = [t for t in found_defs if t['id'] == type_def.id][0]

            self.assertEqual(found_def['id'], type_def.id)
            self.assertEqual(found_def['display_name'], type_def.display_name)
            self.assertEqual(found_def['description'], type_def.description)
            self.assertEqual(found_def['unique_indexes'], type_def.unique_indexes)
            self.assertEqual(found_def['search_indexes'], type_def.search_indexes)
            self.assertEqual(found_def['child_types'], type_def.child_types)

    def test_types_no_types(self):
        """
        Tests an empty list is returned when no types are loaded.
        """

        # Test
        found_defs = self.manager.types()

        # Verify
        self.assertTrue(isinstance(found_defs, list))
        self.assertEqual(0, len(found_defs))

    def test_importers(self):
        """
        Tests retieving all importers.
        """

        # Test
        found = self.manager.importers()

        # Verify
        self.assertEqual(1, len(found))
        self.assertEqual('MockImporter', found[0][0])
        self.assertEqual([1], found[0][1])

    def test_importers_no_importers(self):
        """
        Tests an empty list is returned when no importers are present.
        """

        # Setup
        content_manager._MANAGER.remove_importer('MockImporter', 1)

        # Test
        found = self.manager.importers()

        # Verify
        self.assertTrue(isinstance(found, list))
        self.assertEqual(0, len(found))

    def test_distributors(self):
        """
        Tests retrieving all distributors.
        """

        # Test
        found = self.manager.distributors()

        # Verify
        self.assertEqual(1, len(found))
        self.assertEqual('MockDistributor', found[0][0])
        self.assertEqual([1], found[0][1])

    def test_distributors_no_distributors(self):
        """
        Tests an empty list is returned when no distributors are present.
        """

        # Setup
        content_manager._MANAGER.remove_distributor('MockDistributor', 1)

        # Test
        found = self.manager.distributors()

        # Verify
        self.assertTrue(isinstance(found, list))
        self.assertEqual(0, len(found))
