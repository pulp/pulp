from .... import base
from pulp.devel import mock_plugins
from pulp.plugins.conduits.dependency import DependencyResolutionConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.types import database, model
from pulp.server.controllers import repository as repo_controller
from pulp.server.db import model as db_model
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp.server.db.model.repository import RepoImporter, RepoContentUnit
from pulp.server.exceptions import MissingResource
from pulp.server.managers import factory as manager_factory


TYPE_1_DEF = model.TypeDefinition('type-1', 'Type 1', 'Test Definition One',
                                  ['key-1'], ['search-1'], [])


class DependencyManagerTests(base.PulpServerTests):

    def setUp(self):
        super(DependencyManagerTests, self).setUp()

        mock_plugins.install()

        database.update_database([TYPE_1_DEF])

        self.repo_id = 'dep-repo'
        self.manager = manager_factory.dependency_manager()

        repo_controller.create_repo(self.repo_id)
        manager_factory.repo_importer_manager().set_importer(self.repo_id, 'mock-importer', {})

    def tearDown(self):
        super(DependencyManagerTests, self).tearDown()

        mock_plugins.reset()

    def clean(self):
        super(DependencyManagerTests, self).clean()

        database.clean()

        db_model.Repository.drop_collection()
        RepoImporter.get_collection().remove()
        RepoContentUnit.get_collection().remove()

        mock_plugins.MOCK_IMPORTER.resolve_dependencies.return_value = None

    def test_resolve_dependencies_by_unit(self):
        # Setup
        report = 'dep report'
        mock_plugins.MOCK_IMPORTER.resolve_dependencies.return_value = report

        unit_id_1 = manager_factory.content_manager().add_content_unit('type-1', None,
                                                                       {'key-1': 'v1'})
        unit_id_2 = manager_factory.content_manager().add_content_unit('type-1', None,
                                                                       {'key-1': 'v2'})

        association_manager = manager_factory.repo_unit_association_manager()
        association_manager.associate_unit_by_id(self.repo_id, 'type-1', unit_id_1)
        association_manager.associate_unit_by_id(self.repo_id, 'type-1', unit_id_2)

        # Test
        result = self.manager.resolve_dependencies_by_units(self.repo_id, [], {})

        # Verify
        self.assertEqual(result, report)

        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.resolve_dependencies.call_count)

        args = mock_plugins.MOCK_IMPORTER.resolve_dependencies.call_args[0]
        self.assertEqual(args[0].id, self.repo_id)
        self.assertEqual(len(args[1]), 0)
        self.assertTrue(isinstance(args[2], DependencyResolutionConduit))
        self.assertTrue(isinstance(args[3], PluginCallConfiguration))

    def test_resolve_dependencies_by_unit_no_repo(self):
        self.assertRaises(MissingResource, self.manager.resolve_dependencies_by_units, 'foo', [],
                          {})

    def test_resolve_dependencies_by_unit_no_importer(self):
        repo_controller.create_repo('empty')
        self.assertRaises(MissingResource, self.manager.resolve_dependencies_by_units, 'empty', [],
                          {})

    def test_resolve_dependencies_by_criteria(self):
        # Setup
        report = 'dep report'
        mock_plugins.MOCK_IMPORTER.resolve_dependencies.return_value = report

        unit_id_1 = manager_factory.content_manager().add_content_unit('type-1', None,
                                                                       {'key-1': 'unit-id-1'})
        unit_id_2 = manager_factory.content_manager().add_content_unit('type-1', None,
                                                                       {'key-1': 'dep-1'})

        association_manager = manager_factory.repo_unit_association_manager()
        association_manager.associate_unit_by_id(self.repo_id, 'type-1', unit_id_1)
        association_manager.associate_unit_by_id(self.repo_id, 'type-1', unit_id_2)

        criteria = UnitAssociationCriteria(type_ids=['type-1'], unit_filters={'key-1': 'unit-id-1'})

        # Test
        result = self.manager.resolve_dependencies_by_criteria(self.repo_id, criteria, {})

        # Verify
        self.assertEqual(report, result)

        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.resolve_dependencies.call_count)

        args = mock_plugins.MOCK_IMPORTER.resolve_dependencies.call_args[0]
        self.assertEqual(1, len(args[1]))
