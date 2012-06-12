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

import mock

import base
import mock_plugins

from pulp.plugins.conduits.unit_import import ImportUnitConduit, UnitImportConduitException
from pulp.plugins.conduits._common import to_plugin_unit
import pulp.plugins.types.database as types_database
import pulp.plugins.types.model as types_model
from pulp.server.db.model.repository import Repo, RepoContentUnit, RepoImporter
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo.unit_association as association_manager

# constants --------------------------------------------------------------------

MOCK_TYPE_DEF = types_model.TypeDefinition('mock-type', 'Mock Type', 'Used by the mock importer', ['key-1'], [], [])

# -- test cases ---------------------------------------------------------------

class RepoSyncConduitTests(base.PulpServerTests):

    def clean(self):
        super(RepoSyncConduitTests, self).clean()
        types_database.clean()

        RepoContentUnit.get_collection().remove()
        RepoImporter.get_collection().remove()
        Repo.get_collection().remove()

    def setUp(self):
        super(RepoSyncConduitTests, self).setUp()
        mock_plugins.install()
        types_database.update_database([MOCK_TYPE_DEF])

        self.repo_manager = manager_factory.repo_manager()
        self.repo_query_manager = manager_factory.repo_query_manager()
        self.importer_manager = manager_factory.repo_importer_manager()
        self.association_manager = manager_factory.repo_unit_association_manager()
        self.association_query_manager = manager_factory.repo_unit_association_query_manager()
        self.content_manager = manager_factory.content_manager()
        self.content_query_manager = manager_factory.content_query_manager()

        self.repo_manager.create_repo('source_repo')
        self.importer_manager.set_importer('source_repo', 'mock-importer', {})

        self.repo_manager.create_repo('dest_repo')
        self.importer_manager.set_importer('dest_repo', 'mock-importer', {})

        self.conduit = ImportUnitConduit('source_repo', 'dest_repo', 'mock-importer', 'mock-importer')

    def tearDown(self):
        super(RepoSyncConduitTests, self).tearDown()
        manager_factory.reset()

    def test_str(self):
        """
        Makes sure the __str__ implementation does not raise an error.
        """
        str(self.conduit)

    def test_associate_unit(self):

        # Setup
        self.content_manager.add_content_unit('mock-type', 'unit_1', {'key-1' : 'unit-1'})
        self.association_manager.associate_unit_by_id('source_repo', 'mock-type', 'unit_1', association_manager.OWNER_TYPE_USER, 'admin')

        pulp_unit = self.association_query_manager.get_units('source_repo')[0]
        type_def = types_database.type_definition('mock-type')
        plugin_unit = to_plugin_unit(pulp_unit, type_def)

        # Test
        self.conduit.associate_unit(plugin_unit)

        # Verify
        associated_units = self.association_query_manager.get_units('dest_repo')
        self.assertEqual(1, len(associated_units))

    def test_associate_unit_server_error(self):
        """
        Makes sure the conduit wraps any exception emerging from the server.
        """

        # Setup
        mock_association_manager = mock.Mock()
        mock_association_manager.associate_unit_by_id.side_effect = Exception()
        manager_factory._INSTANCES[manager_factory.TYPE_REPO_ASSOCIATION] = mock_association_manager

        conduit = ImportUnitConduit('source_repo', 'dest_repo', 'mock-importer', 'mock-importer')

        # Test
        try:
           conduit.associate_unit(None)
           self.fail('Exception expected')
        except UnitImportConduitException:
            pass

    def test_get_source_units(self):

        # Setup
        self.content_manager.add_content_unit('mock-type', 'unit_1', {'key-1' : 'unit-1'})
        self.association_manager.associate_unit_by_id('source_repo', 'mock-type', 'unit_1', association_manager.OWNER_TYPE_USER, 'admin')

        # Test
        units = self.conduit.get_source_units()

        # Verify
        self.assertEqual(1, len(units))

    def test_get_source_units_with_error(self):

        # Setup
        self.conduit._ImportUnitConduit__association_query_manager = mock.Mock()
        self.conduit._ImportUnitConduit__association_query_manager.get_units_across_types.side_effect = Exception()

        # Test
        try:
            self.conduit.get_source_units()
            self.fail('Exception expected')
        except UnitImportConduitException, e:
            print(e) # for coverage
