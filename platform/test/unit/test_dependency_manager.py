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

import base
import mock_plugins

from pulp.plugins.conduits.dependency import DependencyResolutionConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Unit
from pulp.plugins.types import database, model
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp.server.db.model.repository import Repo, RepoImporter, RepoContentUnit
from pulp.server.exceptions import MissingResource
from pulp.server.managers import factory as manager_factory

# -- constants ----------------------------------------------------------------

TYPE_1_DEF = model.TypeDefinition('type-1', 'Type 1', 'Test Definition One',
    ['key-1'], ['search-1'], [])

# -- test cases ---------------------------------------------------------------

class DependencyManagerTests(base.PulpServerTests):

    def setUp(self):
        super(DependencyManagerTests, self).setUp()

        mock_plugins.install()

        database.update_database([TYPE_1_DEF])

        self.repo_id = 'dep-repo'
        self.manager = manager_factory.dependency_manager()

        manager_factory.repo_manager().create_repo(self.repo_id)
        manager_factory.repo_importer_manager().set_importer(self.repo_id, 'mock-importer', {})

    def tearDown(self):
        super(DependencyManagerTests, self).tearDown()

        mock_plugins.reset()

    def clean(self):
        super(DependencyManagerTests, self).clean()

        database.clean()

        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoContentUnit.get_collection().remove()

        mock_plugins.MOCK_IMPORTER.resolve_dependencies.return_value = None

    def test_resolve_dependencies_by_unit(self):
        # Setup
        transfer_deps = [
            Unit('type-1', {'key-1' : 'v1'}, {}, 'p1'),
            Unit('type-1', {'key-1' : 'v2'}, {}, 'p2'),
        ]

        mock_plugins.MOCK_IMPORTER.resolve_dependencies.return_value = transfer_deps

        unit_id_1 = manager_factory.content_manager().add_content_unit('type-1', None, {'key-1' : 'v1'})
        unit_id_2 = manager_factory.content_manager().add_content_unit('type-1', None, {'key-1' : 'v2'})

        association_manager = manager_factory.repo_unit_association_manager()
        association_manager.associate_unit_by_id(self.repo_id, 'type-1', unit_id_1, 'user', 'admin')
        association_manager.associate_unit_by_id(self.repo_id, 'type-1', unit_id_2, 'user', 'admin')

        # Test
        deps = self.manager.resolve_dependencies_by_units(self.repo_id, [], {})

        # Verify
        self.assertEqual(2, len(deps))

        deps.sort(key=lambda x : x['key-1'])
        self.assertEqual(deps[0]['key-1'], 'v1')
        self.assertEqual(deps[1]['key-1'], 'v2')

        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.resolve_dependencies.call_count)

        args = mock_plugins.MOCK_IMPORTER.resolve_dependencies.call_args[0]
        self.assertEqual(args[0].id, self.repo_id)
        self.assertEqual(len(args[1]), 0)
        self.assertTrue(isinstance(args[2], DependencyResolutionConduit))
        self.assertTrue(isinstance(args[3], PluginCallConfiguration))

    def test_resolve_dependencies_by_unit_no_repo(self):
        # Test
        self.assertRaises(MissingResource, self.manager.resolve_dependencies_by_units, 'foo', [], {})

    def test_resolve_dependencies_by_unit_no_importer(self):
        # Setup
        manager_factory.repo_manager().create_repo('empty')

        # Test
        self.assertRaises(MissingResource, self.manager.resolve_dependencies_by_units, 'empty', [], {})

    def test_resolve_dependencies_by_criteria(self):
        # Setup
        transfer_deps = [
            Unit('type-1', {'key-1' : 'dep-1'}, {}, 'p1'),
        ]

        mock_plugins.MOCK_IMPORTER.resolve_dependencies.return_value = transfer_deps

        unit_id_1 = manager_factory.content_manager().add_content_unit('type-1', None, {'key-1' : 'unit-id-1'})
        unit_id_2 = manager_factory.content_manager().add_content_unit('type-1', None, {'key-1' : 'dep-1'})

        association_manager = manager_factory.repo_unit_association_manager()
        association_manager.associate_unit_by_id(self.repo_id, 'type-1', unit_id_1, 'user', 'admin')
        association_manager.associate_unit_by_id(self.repo_id, 'type-1', unit_id_2, 'user', 'admin')

        criteria = UnitAssociationCriteria(type_ids=['type-1'], unit_filters={'key-1' : 'unit-id-1'})

        # Test
        deps = self.manager.resolve_dependencies_by_criteria(self.repo_id, criteria, {})

        # Verify
        self.assertEqual(1, len(deps))

        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.resolve_dependencies.call_count)

        args = mock_plugins.MOCK_IMPORTER.resolve_dependencies.call_args[0]
        self.assertEqual(1, len(args[1]))

