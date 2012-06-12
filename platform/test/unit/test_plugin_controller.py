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

# Python
import itertools

import base

import pulp.plugins.loader as plugin_loader
import pulp.plugins.types.database as types_db
from   pulp.plugins.types.model import TypeDefinition

# -- mocks --------------------------------------------------------------------

class MockImporter:
    @classmethod
    def metadata(cls):
        return {'types': ['mock_type']}

class MockDistributor:
    @classmethod
    def metadata(cls):
        return {'types': ['mock_type']}

# -- test cases ---------------------------------------------------------------

class PluginControllerTests(base.PulpWebserviceTests):
    def setUp(self):
        super(PluginControllerTests, self).setUp()

        plugin_loader._create_loader()
        types_db.clean()

        # Configure content manager
        plugin_loader._LOADER.add_importer('MockImporter', MockImporter, {})
        plugin_loader._LOADER.add_distributor('MockDistributor', MockDistributor, {})

    def tearDown(self):
        super(PluginControllerTests, self).tearDown()

        # Reset content manager
        plugin_loader._LOADER.remove_importer('MockImporter')
        plugin_loader._LOADER.remove_distributor('MockDistributor')

    def test_get_types(self):
        # Setup
        type_def_1 = TypeDefinition('type-1', 'Type 1', 'Type 1', [], [], [])
        type_def_2 = TypeDefinition('type-2', 'Type 2', 'Type 2', [], [], [])

        types_db._create_or_update_type(type_def_1)
        types_db._create_or_update_type(type_def_2)

        # Test
        status, body = self.get('/v2/plugins/types/')

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(2, len(body))
        self.assertEqual(body[0]['_href'], '/v2/plugins/types/type-1/')
        self.assertEqual(body[0]['id'], 'type-1')
        self.assertEqual(body[0]['display_name'], 'Type 1')

        self.assertEqual(body[1]['_href'], '/v2/plugins/types/type-2/')
        self.assertEqual(body[1]['id'], 'type-2')
        self.assertEqual(body[1]['display_name'], 'Type 2')

    def test_get_type(self):
        # Setup
        type_def_1 = TypeDefinition('type-1', 'Type 1', 'Type 1', [], [], [])
        types_db._create_or_update_type(type_def_1)

        # Test
        status, body = self.get('/v2/plugins/types/type-1/')

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(body['_href'], '/v2/plugins/types/type-1/')
        self.assertEqual(body['id'], 'type-1')
        self.assertEqual(body['display_name'], 'Type 1')

    def test_get_missing_type(self):
        # Test
        status, body = self.get('/v2/plugins/types/missing/')

        # Verify
        self.assertEqual(404, status)

        self.assertEqual(body['resources']['type'], 'missing')

    def test_get_importers(self):
        # Test
        status, body = self.get('/v2/plugins/importers/')

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(1, len(body))
        self.assertEqual(body[0]['id'], 'MockImporter')
        self.assertEqual(body[0]['_href'], '/v2/plugins/importers/MockImporter/')

    def test_get_importer(self):
        # Test
        status, body = self.get('/v2/plugins/importers/MockImporter/')

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(body['id'], 'MockImporter')
        self.assertEqual(body['_href'], '/v2/plugins/importers/MockImporter/')

    def test_get_missing_importer(self):
        # Test
        status, body = self.get('/v2/plugins/importers/foo/')

        # Verify
        self.assertEqual(404, status)

        self.assertEqual(body['resources']['importer_type_id'], 'foo')

    def test_get_distributors(self):
        # Test
        status, body = self.get('/v2/plugins/distributors/')

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(1, len(body))
        self.assertEqual(body[0]['id'], 'MockDistributor')
        self.assertEqual(body[0]['_href'], '/v2/plugins/distributors/MockDistributor/')

    def test_get_distributor(self):
        # Test
        status, body = self.get('/v2/plugins/distributors/MockDistributor/')

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(body['id'], 'MockDistributor')
        self.assertEqual(body['_href'], '/v2/plugins/distributors/MockDistributor/')

    def test_get_missing_importer(self):
        # Test
        status, body = self.get('/v2/plugins/distributors/foo/')

        # Verify
        self.assertEqual(404, status)

        self.assertEqual(body['resources']['distributor_type_id'], 'foo')
