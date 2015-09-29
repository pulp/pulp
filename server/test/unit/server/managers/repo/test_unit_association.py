import mock

from .... import base
from pulp.devel import mock_plugins
from pulp.plugins.conduits.unit_import import ImportUnitConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Unit
from pulp.plugins.types import database, model
from pulp.server.db import models as me_model
from pulp.server.db.model.auth import User
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp.server.db.model.repository import RepoContentUnit, RepoImporter
import pulp.server.exceptions as exceptions
import pulp.server.managers.content.cud as content_cud_manager
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo.importer as importer_manager
import pulp.server.managers.repo.unit_association as association_manager


TYPE_1_DEF = model.TypeDefinition('type-1', 'Type 1', 'Test Definition One',
                                  ['key-1'], ['search-1'], [])

TYPE_2_DEF = model.TypeDefinition('type-2', 'Type 2', 'Test Definition Two',
                                  ['key-2a', 'key-2b'], [], ['type-1'])

MOCK_TYPE_DEF = model.TypeDefinition('mock-type', 'Mock Type', 'Used by the mock importer',
                                     ['key-1'], [], [])


class RepoUnitAssociationManagerTests(base.PulpServerTests):

    def clean(self):
        super(RepoUnitAssociationManagerTests, self).clean()
        database.clean()
        RepoContentUnit.get_collection().remove()
        RepoImporter.get_collection().remove()
        me_model.Repository.drop_collection()

    def tearDown(self):
        super(RepoUnitAssociationManagerTests, self).tearDown()
        mock_plugins.reset()
        manager_factory.reset()

    def setUp(self):
        super(RepoUnitAssociationManagerTests, self).setUp()
        database.update_database([TYPE_1_DEF, TYPE_2_DEF, MOCK_TYPE_DEF])
        mock_plugins.install()

        self.manager = association_manager.RepoUnitAssociationManager()
        self.importer_manager = importer_manager.RepoImporterManager()
        self.content_manager = content_cud_manager.ContentManager()

        # Set up a valid configured repo for the tests
        self.repo_id = 'associate-repo'
        with mock.patch('pulp.server.managers.repo.importer.models.Repository.objects'):
            self.importer_manager.set_importer(self.repo_id, 'mock-importer', {})

        # Create units that can be associated to a repo
        self.unit_type_id = 'mock-type'

        self.unit_id = 'test-unit-id'
        self.unit_key = {'key-1': 'test-unit'}
        self.content_manager.add_content_unit(self.unit_type_id, self.unit_id, self.unit_key)

        self.unit_id_2 = 'test-unit-id-2'
        self.unit_key_2 = {'key-1': 'test-unit-2'}
        self.content_manager.add_content_unit(self.unit_type_id, self.unit_id_2, self.unit_key_2)

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    def test_associate_by_id(self, mock_repo_qs):
        """
        Tests creating a new association by content unit ID.
        """
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-2')
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id': self.repo_id}))
        self.assertEqual(2, len(repo_units))

        unit_ids = [u['unit_id'] for u in repo_units]
        self.assertTrue('unit-1' in unit_ids)
        self.assertTrue('unit-2' in unit_ids)

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_by_id_existing(self, mock_ctrl, mock_repo_qs):
        """
        Tests attempting to create a new association where one already exists.
        """

        # Test
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')  # shouldn't error

        # Verify
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id': self.repo_id}))
        self.assertEqual(1, len(repo_units))
        self.assertEqual('unit-1', repo_units[0]['unit_id'])

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    def test_associate_by_id_other_owner(self, mock_repo_qs):
        """
        Tests making a second association using a different owner.
        """
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id': self.repo_id}))
        self.assertEqual(1, len(repo_units))
        self.assertEqual('unit-1', repo_units[0]['unit_id'])

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_all(self, mock_ctrl, mock_repo_qs):
        """
        Tests making multiple associations in a single call.
        """
        ids = ['foo', 'bar', 'baz']
        ret = self.manager.associate_all_by_ids(self.repo_id, 'type-1', ids)

        repo_units = list(RepoContentUnit.get_collection().find({'repo_id': self.repo_id}))
        self.assertEqual(len(ids), len(repo_units))

        # return value should be the number of units that were associated
        self.assertEqual(ret, len(repo_units))
        for unit in repo_units:
            self.assertTrue(unit['unit_id'] in ids)

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_unassociate_by_id(self, mock_ctrl, mock_repo_qs):
        """
        Tests removing an association that exists by its unit ID.
        """
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id)
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id_2)

        self.manager.unassociate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id)
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id': self.repo_id}))
        self.assertEqual(1, len(repo_units))
        self.assertEqual(self.unit_id_2, repo_units[0]['unit_id'])

    def test_unassociate_by_id_no_association(self):
        """
        Tests unassociating a unit where no association exists.
        """

        # Test - Make sure this does not raise an error
        self.manager.unassociate_unit_by_id(self.repo_id, 'type-1', 'unit-1')

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    def test_associate_from_repo_no_criteria(self, mock_repo_qs):
        source_repo_id = 'source-repo'
        dest_repo_id = 'dest-repo'

        self.importer_manager.set_importer(source_repo_id, 'mock-importer', {})
        self.importer_manager.set_importer(dest_repo_id, 'mock-importer', {})

        self.content_manager.add_content_unit('mock-type', 'unit-1', {'key-1': 'unit-1'})
        self.content_manager.add_content_unit('mock-type', 'unit-2', {'key-1': 'unit-2'})
        self.content_manager.add_content_unit('mock-type', 'unit-3', {'key-1': 'unit-3'})

        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-1')
        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-2')
        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-3')

        fake_user = User('associate-user', '')
        manager_factory.principal_manager().set_principal(principal=fake_user)

        mock_plugins.MOCK_IMPORTER.import_units.return_value = [Unit('mock-type', {'k': 'v'}, {},
                                                                     '')]

        # Test
        results = self.manager.associate_from_repo(source_repo_id, dest_repo_id)
        associated = results['units_successful']

        # Verify
        self.assertEqual(1, len(associated))
        self.assertEqual(associated[0]['type_id'], 'mock-type')
        self.assertEqual(associated[0]['unit_key'], {'k': 'v'})

        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.import_units.call_count)

        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        args = mock_plugins.MOCK_IMPORTER.import_units.call_args[0]
        kwargs = mock_plugins.MOCK_IMPORTER.import_units.call_args[1]
        self.assertEqual(args[0], mock_repo.to_transfer_repo())
        self.assertEqual(args[1], mock_repo.to_transfer_repo())
        self.assertEqual(None, kwargs['units'])  # units to import
        self.assertTrue(isinstance(args[3], PluginCallConfiguration))  # config

        conduit = args[2]
        self.assertTrue(isinstance(conduit, ImportUnitConduit))

        # Clean Up
        manager_factory.principal_manager().set_principal(principal=None)

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    def test_associate_from_repo_dest_has_no_importer(self, mock_repo_qs):
        self.assertRaises(
            exceptions.MissingResource,
            self.manager.associate_from_repo,
            'source-repo',
            'repo-with-no-importer'
        )

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    def test_associate_from_repo_dest_unsupported_types(self, mock_repo_qs):
        source_repo_id = 'source-repo'
        dest_repo_id = 'dest-repo'

        self.importer_manager.set_importer(source_repo_id, 'mock-importer', {})
        self.assertRaises(exceptions.MissingResource,
                          self.manager.associate_from_repo, source_repo_id, dest_repo_id)

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    def test_associate_from_repo_importer_error(self, mock_repo_qs):
        source_repo_id = 'source-repo'
        dest_repo_id = 'dest-repo'

        self.importer_manager.set_importer(source_repo_id, 'mock-importer', {})
        self.importer_manager.set_importer(dest_repo_id, 'mock-importer', {})

        mock_plugins.MOCK_IMPORTER.import_units.side_effect = Exception()

        self.content_manager.add_content_unit('mock-type', 'unit-1', {'key-1': 'unit-1'})
        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-1')

        # Test
        try:
            self.manager.associate_from_repo(source_repo_id, dest_repo_id)
            self.fail('Exception expected')
        except exceptions.PulpExecutionException:
            pass

        # Cleanup
        mock_plugins.MOCK_IMPORTER.import_units.side_effect = None

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    def test_associate_from_repo_no_matching_units(self, mock_repo_qs):
        source_repo_id = 'source-repo'
        dest_repo_id = 'dest-repo'

        self.importer_manager.set_importer(source_repo_id, 'mock-importer', {})
        self.importer_manager.set_importer(dest_repo_id, 'mock-importer', {})

        mock_plugins.MOCK_IMPORTER.import_units.return_value = []
        ret = self.manager.associate_from_repo(source_repo_id, dest_repo_id)

        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.import_units.call_count)
        self.assertEqual(ret.get('units_successful'), [])

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    def test_associate_from_repo_missing_source(self, mock_repo_qs):
        dest_repo_id = 'dest-repo'
        self.importer_manager.set_importer(dest_repo_id, 'mock-importer', {})

        try:
            self.manager.associate_from_repo('missing', dest_repo_id)
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('missing' == e.resources['repository'])

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    def test_associate_from_repo_missing_destination(self, mock_repo_qs):
        source_repo_id = 'source-repo'
        self.importer_manager.set_importer(source_repo_id, 'mock-importer', {})

        try:
            self.manager.associate_from_repo(source_repo_id, 'missing')
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('missing' == e.resources['repository'])

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_by_id_calls_update_unit_count(self, mock_ctrl, mock_repo_qs):
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        mock_ctrl.update_unit_count.assert_called_once_with(self.repo_id, 'type-1', 1)

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_by_id_calls_update_last_unit_added(self, mock_ctrl, mock_repo_qs):
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        mock_ctrl.update_last_unit_added.assert_called_once_with(self.repo_id)

    @mock.patch('pulp.server.controllers.repository.update_unit_count')
    def test_associate_by_id_does_not_call_update_unit_count(self, mock_call):
        """
        This would be the case when doing a bulk update.
        """
        self.manager.associate_unit_by_id(
            self.repo_id, 'type-1', 'unit-1', False)
        self.assertFalse(mock_call.called)

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_non_unique_by_id(self, mock_ctrl, mock_repo_qs):
        """
        non-unique call should not increment the count
        """
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')

        # creates a non-unique association for which the count should not be
        # incremented
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        self.assertEqual(mock_ctrl.update_unit_count.call_count, 1)  # only from first associate

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_all_by_ids_calls_update_unit_count(self, mock_ctrl, mock_repo_qs):
        IDS = ('foo', 'bar', 'baz')
        self.manager.associate_all_by_ids(self.repo_id, 'type-1', IDS)
        mock_ctrl.update_unit_count.assert_called_once_with(self.repo_id, 'type-1', len(IDS))

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_all_by_id_calls_update_last_unit_added(self, mock_ctrl, mock_repo_qs):
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        mock_ctrl.update_last_unit_added.assert_called_once_with(self.repo_id)

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_all_non_unique(self, mock_ctrl, mock_repo_qs):
        """
        Makes sure when two identical associations are requested, they only
        get counted once.
        """
        IDS = ('foo', 'bar', 'foo')

        self.manager.associate_all_by_ids(self.repo_id, 'type-1', IDS)
        mock_ctrl.update_unit_count.assert_called_once_with(self.repo_id, 'type-1', 2)

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_unassociate_all(self, mock_ctrl, mock_repo_qs):
        """
        Tests unassociating multiple units in a single call.
        """

        # Setup
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id)
        # Add a different user to ensure they will remove properly
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id_2)
        self.manager.associate_unit_by_id(self.repo_id, 'type-2', 'unit-1')
        self.manager.associate_unit_by_id(self.repo_id, 'type-2', 'unit-2')

        unit_coll = RepoContentUnit.get_collection()
        self.assertEqual(4, len(list(unit_coll.find({'repo_id': self.repo_id}))))

        # Test
        results = self.manager.unassociate_all_by_ids(self.repo_id, self.unit_type_id,
                                                      [self.unit_id, self.unit_id_2])
        unassociated = results['units_successful']

        # Verify
        self.assertEqual(len(unassociated), 2)
        for u in unassociated:
            self.assertTrue(isinstance(u, dict))
            self.assertTrue(u['type_id'], self.unit_type_id)
            self.assertTrue(u['unit_key'] in [self.unit_key, self.unit_key_2])

        self.assertEqual(2, len(list(unit_coll.find({'repo_id': self.repo_id}))))

        self.assertTrue(unit_coll.find_one({'repo_id': self.repo_id, 'unit_type_id': 'type-2',
                                            'unit_id': 'unit-1'}) is not None)
        self.assertTrue(unit_coll.find_one({'repo_id': self.repo_id, 'unit_type_id': 'type-2',
                                            'unit_id': 'unit-2'}) is not None)

    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_unassociate_by_id_calls_update_unit_count(self, mock_ctrl, mock_repo_qs):
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id)
        self.manager.unassociate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id)

        self.assertEqual(2, mock_ctrl.update_unit_count.call_count)
        self.assertEqual(mock_ctrl.update_unit_count.call_args_list[0][0][0], self.repo_id)
        self.assertEqual(mock_ctrl.update_unit_count.call_args_list[1][0][1], self.unit_type_id)
        self.assertEqual(mock_ctrl.update_unit_count.call_args_list[0][0][2], 1)

        self.assertEqual(mock_ctrl.update_unit_count.call_args_list[1][0][0], self.repo_id)
        self.assertEqual(mock_ctrl.update_unit_count.call_args_list[1][0][1], self.unit_type_id)
        self.assertEqual(mock_ctrl.update_unit_count.call_args_list[1][0][2], -1)

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_unassociate_by_id_non_unique(self, mock_ctrl):
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        self.manager.unassociate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        mock_ctrl.update_unit_count.assert_called_once_with(self.repo_id, 'type-1', 1)
        mock_ctrl.update_last_unit_added.assert_called_once_with(self.repo_id)

    @mock.patch('pymongo.cursor.Cursor.count', return_value=1)
    def test_association_exists_true(self, mock_count):
        self.assertTrue(self.manager.association_exists(self.repo_id, 'unit-1', 'type-1'))
        self.assertEqual(mock_count.call_count, 1)

    @mock.patch('pymongo.cursor.Cursor.count', return_value=0)
    def test_association_exists_false(self, mock_count):
        self.assertFalse(self.manager.association_exists(self.repo_id, 'type-1', 'unit-1'))
        self.assertEqual(mock_count.call_count, 1)

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    @mock.patch('pulp.server.managers.repo.unit_association.models.Repository.objects')
    def test_unassociate_via_criteria(self, mock_repo_qs, mock_ctrl):
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id)
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id_2)

        criteria_doc = {'filters': {'association': {'unit_id': {'$in': [self.unit_id, 'unit-X']}}}}

        criteria = UnitAssociationCriteria.from_client_input(criteria_doc)

        self.manager.unassociate_by_criteria(self.repo_id, criteria)

        self.assertFalse(self.manager.association_exists(self.repo_id, self.unit_id,
                                                         self.unit_type_id))
        self.assertTrue(self.manager.association_exists(self.repo_id, self.unit_id_2,
                                                        self.unit_type_id))
        mock_repo_qs.get_repo_or_missing_resource.assert_called_once_with(self.repo_id)

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_unassociate_via_criteria_no_matches(self, mock_ctrl):
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-2')

        criteria_doc = {'type_ids': ['type-2']}

        criteria = UnitAssociationCriteria.from_client_input(criteria_doc)

        result = self.manager.unassociate_by_criteria(self.repo_id, criteria)
        self.assertEquals(result, {})

        self.assertTrue(self.manager.association_exists(self.repo_id, 'unit-1', 'type-1'))
        self.assertTrue(self.manager.association_exists(self.repo_id, 'unit-2', 'type-1'))
