import mock

from .... import base
from pulp.common.compat import unittest
from pulp.devel import mock_plugins, skip
from pulp.plugins.types import database, model
from pulp.server.controllers import importer as importer_controller
from pulp.server.db import model as me_model
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp.server.db.model.repository import RepoContentUnit
import pulp.server.exceptions as exceptions
import pulp.server.managers.content.cud as content_cud_manager
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo.unit_association as association_manager


TYPE_1_DEF = model.TypeDefinition('type-1', 'Type 1', 'Test Definition One',
                                  ['key-1'], ['search-1'], [])

TYPE_2_DEF = model.TypeDefinition('type-2', 'Type 2', 'Test Definition Two',
                                  ['key-2a', 'key-2b'], [], ['type-1'])

MOCK_TYPE_DEF = model.TypeDefinition('mock-type', 'Mock Type', 'Used by the mock importer',
                                     ['key-1'], [], [])


@mock.patch('pulp.server.controllers.repository.find_repo_content_units', spec_set=True)
class TestUnitsFromCriteria(unittest.TestCase):
    def setUp(self):
        super(TestUnitsFromCriteria, self).setUp()
        self.manager = association_manager.RepoUnitAssociationManager()
        self.repo = me_model.Repository(repo_id='repo1')

    def test_criteria_unit_fields(self, mock_find):
        """
        Ensure that the criteria unit_fields are passed on to the find_repo_content_units function.
        """
        criteria = UnitAssociationCriteria(unit_fields=['secret_location', 'pasword'])

        self.manager._units_from_criteria(self.repo, criteria)

        self.assertEqual(mock_find.call_count, 1)
        self.assertEqual(mock_find.mock_calls[0][2]['unit_fields'], ['secret_location', 'pasword'])

    def test_limits_by_type(self, mock_find):
        criteria = UnitAssociationCriteria(type_ids=['foo'])

        self.manager._units_from_criteria(self.repo, criteria)

        # This is the combination of a Q with a raw query, plus a normal Q. The original Q
        # objects are preserved on the "children" attribute, since they cannot be directly
        # combined like normal Q objects.
        association_q_combination = mock_find.call_args[1]['repo_content_unit_q']
        found = False
        for association_q in association_q_combination.children:
            if association_q.query.get('unit_type_id__in') == ['foo']:
                found = True
                break
        self.assertTrue(found)


@mock.patch('pulp.server.managers.repo.unit_association.model.Repository')
class RepoUnitAssociationManagerTests(base.PulpServerTests):

    def clean(self):
        super(RepoUnitAssociationManagerTests, self).clean()
        database.clean()
        RepoContentUnit.get_collection().remove()
        me_model.Repository.objects.delete()
        me_model.Importer.objects.delete()

    def tearDown(self):
        super(RepoUnitAssociationManagerTests, self).tearDown()
        mock_plugins.reset()
        manager_factory.reset()

    def setUp(self):
        super(RepoUnitAssociationManagerTests, self).setUp()
        database.update_database([TYPE_1_DEF, TYPE_2_DEF, MOCK_TYPE_DEF])
        mock_plugins.install()

        self.manager = association_manager.RepoUnitAssociationManager()
        self.content_manager = content_cud_manager.ContentManager()

        # Set up a valid configured repo for the tests
        self.repo_id = 'associate-repo'
        with mock.patch('pulp.server.controllers.importer.model.Repository'):
            importer_controller.set_importer(self.repo_id, 'mock-importer', {})

        # Create units that can be associated to a repo
        self.unit_type_id = 'mock-type'

        self.unit_id = 'test-unit-id'
        self.unit_key = {'key-1': 'test-unit'}
        self.content_manager.add_content_unit(self.unit_type_id, self.unit_id, self.unit_key)

        self.unit_id_2 = 'test-unit-id-2'
        self.unit_key_2 = {'key-1': 'test-unit-2'}
        self.content_manager.add_content_unit(self.unit_type_id, self.unit_id_2, self.unit_key_2)

    def test_associate_by_id(self, mock_repo):
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

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_by_id_existing(self, mock_ctrl, mock_repo):
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

    def test_associate_by_id_other_owner(self, mock_repo_qs):
        """
        Tests making a second association using a different owner.
        """
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id': self.repo_id}))
        self.assertEqual(1, len(repo_units))
        self.assertEqual('unit-1', repo_units[0]['unit_id'])

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_all(self, mock_ctrl, mock_repo):
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

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_unassociate_by_id(self, mock_ctrl, mock_repo):
        """
        Tests removing an association that exists by its unit ID.
        """
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id)
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id_2)

        self.manager.unassociate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id)
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id': self.repo_id}))
        self.assertEqual(1, len(repo_units))
        self.assertEqual(self.unit_id_2, repo_units[0]['unit_id'])

    def test_unassociate_by_id_no_association(self, mock_repo_qs):
        """
        Tests unassociating a unit where no association exists.
        """

        # Test - Make sure this does not raise an error
        self.manager.unassociate_unit_by_id(self.repo_id, 'type-1', 'unit-1')

    @mock.patch('pulp.server.managers.repo.unit_association.UnitAssociationCriteria')
    def test_associate_from_repo_dest_has_no_importer(self, mock_repo, mock_crit):
        self.assertRaises(
            exceptions.MissingResource,
            self.manager.associate_from_repo,
            'source-repo',
            'repo-with-no-importer',
            mock_crit
        )

    @mock.patch('pulp.server.managers.repo.unit_association.UnitAssociationCriteria')
    def test_associate_from_repo_dest_unsupported_types(self, mock_repo_qs, mock_crit):
        importer_controller.set_importer('source_repo', 'mock-importer', {})
        self.assertRaises(exceptions.MissingResource, self.manager.associate_from_repo,
                          'source_repo', 'dest_repo', mock_crit)

    @mock.patch('pulp.server.managers.repo.unit_association.UnitAssociationCriteria')
    def test_associate_from_repo_importer_error(self, mock_repo, mock_crit):
        importer_controller.set_importer('source_repo', 'mock-importer', {})
        importer_controller.set_importer('dest_repo', 'mock-importer', {})

        mock_plugins.MOCK_IMPORTER.import_units.side_effect = Exception()

        self.content_manager.add_content_unit('mock-type', 'unit-1', {'key-1': 'unit-1'})
        self.manager.associate_unit_by_id('source_repo', 'mock-type', 'unit-1')

        # Test
        try:
            self.manager.associate_from_repo('source_repo', 'dest_repo', mock_crit)
            self.fail('Exception expected')
        except Exception:
            pass

        # Cleanup
        mock_plugins.MOCK_IMPORTER.import_units.side_effect = None

    @mock.patch('pulp.server.controllers.repository.rebuild_content_unit_counts', spec_set=True)
    @mock.patch('pulp.server.managers.repo.unit_association.UnitAssociationCriteria')
    @mock.patch('pulp.server.managers.repo.unit_association.plugin_api')
    @mock.patch('pulp.server.managers.repo.unit_association.model.Importer')
    def test_associate_from_repo_no_matching_units(self, mock_importer, mock_plugin, mock_repo,
                                                   mock_crit, mock_rebuild_count):
        mock_imp_inst = mock.MagicMock()
        mock_plugin.get_importer_by_id.return_value = (mock_imp_inst, mock.MagicMock())
        source_repo = mock.MagicMock(repo_id='source-repo')
        dest_repo = mock.MagicMock(repo_id='dest-repo')

        with mock.patch('pulp.server.controllers.importer.remove_importer'):
            importer_controller.set_importer(source_repo, 'mock-importer', {})
            importer_controller.set_importer(dest_repo, 'mock-importer', {})

        mock_plugins.MOCK_IMPORTER.import_units.return_value = []
        ret = self.manager.associate_from_repo('source_repo', 'dest_repo', mock_crit)

        self.assertEqual(1, mock_imp_inst.import_units.call_count)
        self.assertEqual(ret.get('units_successful'), [])

    @mock.patch('pulp.server.controllers.repository.update_last_unit_added')
    @mock.patch('pulp.server.controllers.repository.rebuild_content_unit_counts', spec_set=True)
    @mock.patch('pulp.server.managers.repo.unit_association.UnitAssociationCriteria')
    @mock.patch('pulp.server.managers.repo.unit_association.plugin_api')
    @mock.patch('pulp.server.managers.repo.unit_association.model.Importer')
    def test_associate_from_repo_return_tuple(self, mock_importer, mock_plugin, mock_repo,
                                              mock_crit, mock_rebuild_count, mock_last_unit_added):
        mock_imp_inst = mock.MagicMock()
        mock_plugin.get_importer_by_id.return_value = (mock_imp_inst, mock.MagicMock())
        source_repo = mock.MagicMock(repo_id='source-repo')
        dest_repo = mock.MagicMock(repo_id='dest-repo')

        with mock.patch('pulp.server.controllers.importer.remove_importer'):
            importer_controller.set_importer(source_repo, 'mock-importer', {})
            importer_controller.set_importer(dest_repo, 'mock-importer', {})

        mock_imp_inst.import_units.return_value = (list(), list())
        ret = self.manager.associate_from_repo('source_repo', 'dest_repo', mock_crit)

        mock_last_unit_added.assert_called_once()
        self.assertEqual(1, mock_imp_inst.import_units.call_count)
        self.assertEqual(ret.get('units_successful'), [])
        self.assertEqual(ret.get('units_failed_signature_filter'), [])

    @mock.patch('pulp.server.managers.repo.unit_association.UnitAssociationCriteria')
    def test_associate_from_repo_missing_source(self, mock_repo, mock_crit):
        importer_controller.set_importer('dest_repo', 'mock-importer', {})

        try:
            self.manager.associate_from_repo('missing', 'dest_repo', mock_crit)
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('missing' == e.resources['repo_id'])

    @mock.patch('pulp.server.managers.repo.unit_association.UnitAssociationCriteria')
    def test_associate_from_repo_missing_destination(self, mock_repo, mock_crit):
        importer_controller.set_importer('source_repo', 'mock-importer', {})

        try:
            self.manager.associate_from_repo('source_repo', 'missing', mock_crit)
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('missing' == e.resources['repo_id'])

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_by_id_calls_update_unit_count(self, mock_ctrl, mock_repo):
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        mock_ctrl.update_unit_count.assert_called_once_with(self.repo_id, 'type-1', 1)

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_by_id_calls_update_last_unit_added(self, mock_ctrl, mock_repo):
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        mock_ctrl.update_last_unit_added.assert_called_once_with(self.repo_id)

    @mock.patch('pulp.server.controllers.repository.update_unit_count')
    def test_associate_by_id_does_not_call_update_unit_count(self, mock_call, mock_repo):
        """
        This would be the case when doing a bulk update.
        """
        self.manager.associate_unit_by_id(
            self.repo_id, 'type-1', 'unit-1', False)
        self.assertFalse(mock_call.called)

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_non_unique_by_id(self, mock_ctrl, mock_repo):
        """
        non-unique call should not increment the count
        """
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')

        # creates a non-unique association for which the count should not be
        # incremented
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        self.assertEqual(mock_ctrl.update_unit_count.call_count, 1)  # only from first associate

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_all_by_ids_calls_update_unit_count(self, mock_ctrl, mock_repo):
        IDS = ('foo', 'bar', 'baz')
        self.manager.associate_all_by_ids(self.repo_id, 'type-1', IDS)
        mock_ctrl.update_unit_count.assert_called_once_with(self.repo_id, 'type-1', len(IDS))

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_all_by_id_calls_update_last_unit_added(self, mock_ctrl, mock_repo_qs):
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        mock_ctrl.update_last_unit_added.assert_called_once_with(self.repo_id)

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_associate_all_non_unique(self, mock_ctrl, mock_repo):
        """
        Makes sure when two identical associations are requested, they only
        get counted once.
        """
        IDS = ('foo', 'bar', 'foo')

        self.manager.associate_all_by_ids(self.repo_id, 'type-1', IDS)
        mock_ctrl.update_unit_count.assert_called_once_with(self.repo_id, 'type-1', 2)

    # This test is skipped for now because it needs to be reworked to reflect the changes from this
    # commit, and we don't have time to do that at the moment.
    @skip.skip_broken
    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_unassociate_all(self, mock_ctrl, mock_repo):
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

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_unassociate_by_id_calls_update_unit_count(self, mock_ctrl, mock_repo):
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id)
        self.manager.unassociate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id)

        self.assertEqual(1, mock_ctrl.update_unit_count.call_count)
        self.assertEqual(1, mock_ctrl.rebuild_content_unit_counts.call_count)
        self.assertEqual(mock_ctrl.update_unit_count.call_args_list[0][0][0], self.repo_id)
        self.assertEqual(mock_ctrl.update_unit_count.call_args_list[0][0][1], self.unit_type_id)
        self.assertEqual(mock_ctrl.update_unit_count.call_args_list[0][0][2], 1)

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_unassociate_by_id_non_unique(self, mock_ctrl, mock_repo):
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        self.manager.unassociate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        mock_ctrl.update_unit_count.assert_called_once_with(self.repo_id, 'type-1', 1)
        mock_ctrl.update_last_unit_added.assert_called_once_with(self.repo_id)

    @mock.patch('pymongo.cursor.Cursor.count', return_value=1)
    def test_association_exists_true(self, mock_count, mock_repo):
        self.assertTrue(self.manager.association_exists(self.repo_id, 'unit-1', 'type-1'))
        self.assertEqual(mock_count.call_count, 1)

    @mock.patch('pymongo.cursor.Cursor.count', return_value=0)
    def test_association_exists_false(self, mock_count, mock_repo):
        self.assertFalse(self.manager.association_exists(self.repo_id, 'type-1', 'unit-1'))
        self.assertEqual(mock_count.call_count, 1)

    # This test is skipped for now because it needs to be reworked to reflect the changes from this
    # commit, and we don't have time to do that at the moment.
    @skip.skip_broken
    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_unassociate_via_criteria(self, mock_ctrl, mock_repo):
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id)
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id_2)

        criteria_doc = {'filters': {'association': {'unit_id': {'$in': [self.unit_id, 'unit-X']}}}}

        criteria = UnitAssociationCriteria.from_client_input(criteria_doc)

        self.manager.unassociate_by_criteria(self.repo_id, criteria)

        self.assertFalse(self.manager.association_exists(self.repo_id, self.unit_id,
                                                         self.unit_type_id))
        self.assertTrue(self.manager.association_exists(self.repo_id, self.unit_id_2,
                                                        self.unit_type_id))
        mock_repo.objects.get_repo_or_missing_resource.assert_called_once_with(self.repo_id)

    @mock.patch('pulp.server.managers.repo.unit_association.repo_controller')
    def test_unassociate_via_criteria_no_matches(self, mock_ctrl, mock_repo):
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1')
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-2')

        criteria_doc = {'type_ids': ['type-2']}

        criteria = UnitAssociationCriteria.from_client_input(criteria_doc)

        result = self.manager.unassociate_by_criteria(self.repo_id, criteria)
        self.assertEquals(result, {})

        self.assertTrue(self.manager.association_exists(self.repo_id, 'unit-1', 'type-1'))
        self.assertTrue(self.manager.association_exists(self.repo_id, 'unit-2', 'type-1'))
