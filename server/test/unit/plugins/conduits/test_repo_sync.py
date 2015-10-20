import mock

from ... import base
from pulp.devel import mock_plugins
from pulp.plugins.conduits.mixins import ImporterConduitException
from pulp.plugins.conduits.repo_sync import RepoSyncConduit
from pulp.plugins.model import SyncReport
from pulp.server.controllers import importer as importer_controller
from pulp.server.db import model
from pulp.server.db.model.repository import RepoContentUnit
import pulp.plugins.types.database as types_database
import pulp.plugins.types.model as types_model
import pulp.server.managers.content.cud as content_manager
import pulp.server.managers.content.query as query_manager
import pulp.server.managers.repo.unit_association as association_manager
import pulp.server.managers.repo.unit_association_query as association_query_manager

TYPE_1_DEF = types_model.TypeDefinition('type_1', 'Type 1', 'One', ['key-1'], ['search-1'],
                                        ['type_2'])
TYPE_2_DEF = types_model.TypeDefinition('type_2', 'Type 2', 'Two', ['key-2a', 'key-2b'], [],
                                        ['type_1'])


class RepoSyncConduitTests(base.PulpServerTests):

    def clean(self):
        super(RepoSyncConduitTests, self).clean()
        model.Repository.objects.delete()
        model.Importer.objects.delete()
        RepoContentUnit.get_collection().remove()

    @mock.patch('pulp.server.controllers.importer.remove_importer')
    @mock.patch('pulp.server.controllers.importer.model.Repository.objects')
    @mock.patch('pulp.server.controllers.importer.model.Importer.objects')
    def setUp(self, mock_repo_qs, mock_imp_qs, mock_remove):
        super(RepoSyncConduitTests, self).setUp()
        mock_plugins.install()
        types_database.update_database([TYPE_1_DEF, TYPE_2_DEF])

        self.association_manager = association_manager.RepoUnitAssociationManager()
        self.association_query_manager = association_query_manager.RepoUnitAssociationQueryManager()
        self.content_manager = content_manager.ContentManager()
        self.query_manager = query_manager.ContentQueryManager()

        importer_controller.set_importer(mock.MagicMock(repo_id='repo-1'), 'mock-importer', {})
        self.conduit = RepoSyncConduit('repo-1', 'test-importer')

    def tearDown(self):
        super(RepoSyncConduitTests, self).tearDown()

        types_database.clean()
        mock_plugins.reset()

    def test_str(self):
        """
        Makes sure the __str__ implementation does not raise an error.
        """
        str(self.conduit)

    @mock.patch('pulp.server.managers.repo.unit_association.model.Repository.objects')
    def test_get_remove_unit(self, mock_repo_qs):
        """
        Tests retrieving units through the conduit and removing them.
        """

        # Setup
        unit_1_key = {'key-1': 'unit_1'}
        unit_1_metadata = {'meta_1': 'value_1'}
        unit_1 = self.conduit.init_unit(TYPE_1_DEF.id, unit_1_key, unit_1_metadata, '/foo/bar')
        self.conduit.save_unit(unit_1)

        # Test - get_units
        units = self.conduit.get_units()

        #   Verify returned units
        self.assertEqual(1, len(units))
        self.assertEqual(unit_1_key, units[0].unit_key)
        self.assertTrue(units[0].id is not None)

        # Test - remove_units
        self.conduit.remove_unit(units[0])

        # Verify repo association removed in the database
        associated_units = list(RepoContentUnit.get_collection().find({'repo_id': 'repo-1'}))
        self.assertEqual(0, len(associated_units))

        #   Verify the unit itself is still in the database
        db_unit = self.query_manager.get_content_unit_by_id(TYPE_1_DEF.id, unit_1.id)
        self.assertTrue(db_unit is not None)

    @mock.patch('pulp.server.managers.repo.unit_association.model.Repository')
    def test_build_reports(self, mock_repo_qs):
        """
        Tests that the conduit correctly inserts the count values into the report.
        """

        # Setup

        # Created - 10
        for i in range(0, 10):
            unit_key = {'key-1': 'unit_%d' % i}
            unit = self.conduit.init_unit(TYPE_1_DEF.id, unit_key, {}, '/foo/bar')
            self.conduit.save_unit(unit)

        # Removed - 1
        doomed = self.conduit.get_units()[0]
        self.conduit.remove_unit(doomed)

        # Updated - 1
        update_me = self.conduit.init_unit(TYPE_1_DEF.id, {'key-1': 'unit_5'}, {}, '/foo/bar')
        self.conduit.save_unit(update_me)

        # Test
        success_report = self.conduit.build_success_report('summary', 'details')
        failure_report = self.conduit.build_failure_report('summary', 'details')
        cancel_report = self.conduit.build_cancel_report('summary', 'details')

        # Verify
        self.assertEqual(success_report.success_flag, True)
        self.assertEqual(success_report.canceled_flag, False)
        self.assertEqual(failure_report.success_flag, False)
        self.assertEqual(failure_report.canceled_flag, False)
        self.assertEqual(cancel_report.success_flag, False)
        self.assertEqual(cancel_report.canceled_flag, True)

        for r in (success_report, failure_report, cancel_report):
            self.assertTrue(isinstance(r, SyncReport))
            self.assertEqual(10, r.added_count)
            self.assertEqual(1, r.removed_count)
            self.assertEqual(1, r.updated_count)
            self.assertEqual('summary', r.summary)
            self.assertEqual('details', r.details)

    def test_remove_unit_with_error(self):
        # Setup
        self.conduit._association_manager = mock.Mock()
        self.conduit._association_manager.unassociate_unit_by_id.side_effect = Exception()

        # Test
        self.assertRaises(ImporterConduitException, self.conduit.remove_unit, None)

    def test_associate_existing(self):
        mock_am = mock.Mock()
        self.conduit._association_manager = mock_am
        self.conduit._content_query_manager = mock.Mock()
        mock_unit_key = {'some_key': 123}
        mock_id = mock.Mock()
        self.conduit._content_query_manager.get_content_unit_ids.return_value = [mock_id]
        self.conduit.associate_existing('fake-type', [mock_unit_key])
        mock_am.associate_all_by_ids.assert_called_once_with('repo-1', 'fake-type', [mock_id])
