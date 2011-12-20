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
import mock
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil
import mock_plugins

from pulp.server.content.conduits.repo_sync import RepoSyncConduit, RepoSyncConduitException
from pulp.server.content.plugins.model import SyncReport
import pulp.server.content.types.database as types_database
import pulp.server.content.types.model as types_model
from pulp.server.db.model.gc_repository import Repo, RepoContentUnit
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.repo.importer as importer_manager
import pulp.server.managers.repo.sync as sync_manager
import pulp.server.managers.repo.unit_association as association_manager
import pulp.server.managers.content.cud as content_manager
import pulp.server.managers.content.query as query_manager

# constants --------------------------------------------------------------------

TYPE_1_DEF = types_model.TypeDefinition('type_1', 'Type 1', 'One', ['key-1'], ['search-1'], ['type_2'])
TYPE_2_DEF = types_model.TypeDefinition('type_2', 'Type 2', 'Two', ['key-2a', 'key-2b'], [], ['type_1'])

# -- test cases ---------------------------------------------------------------

class RepoSyncConduitTests(testutil.PulpTest):

    def clean(self):
        super(RepoSyncConduitTests, self).clean()
        types_database.clean()

        RepoContentUnit.get_collection().remove()
        Repo.get_collection().remove()

    def setUp(self):
        super(RepoSyncConduitTests, self).setUp()
        mock_plugins.install()
        types_database.update_database([TYPE_1_DEF, TYPE_2_DEF])

        self.repo_manager = repo_manager.RepoManager()
        self.importer_manager = importer_manager.RepoImporterManager()
        self.sync_manager = sync_manager.RepoSyncManager()
        self.association_manager = association_manager.RepoUnitAssociationManager()
        self.content_manager = content_manager.ContentManager()
        self.query_manager = query_manager.ContentQueryManager()

        self.repo_manager.create_repo('repo-1')
        self.conduit = self._conduit('repo-1')

    def test_str(self):
        """
        Makes sure the __str__ implementation does not raise an error.
        """
        str(self.conduit)

    def test_init_save_units(self):
        """
        Tests using the init and save methods to add and associate content to a repository.
        """

        # Test - init_unit
        unit_1_key = {'key-1' : 'unit_1'}
        unit_1_metadata = {'meta_1' : 'value_1'}
        unit_1 = self.conduit.init_unit(TYPE_1_DEF.id, unit_1_key, unit_1_metadata, '/foo/bar')

        #   Verify that the returned unit is populated with the correct data
        self.assertTrue(unit_1 is not None)
        self.assertEqual(unit_1.unit_key, unit_1_key)
        self.assertEqual(unit_1.type_id, TYPE_1_DEF.id)
        self.assertEqual(unit_1.metadata, unit_1_metadata)
        self.assertTrue(unit_1.id is None)
        self.assertTrue(unit_1.storage_path is not None)
        self.assertTrue('/foo/bar' in unit_1.storage_path)

        # Test - save_unit
        unit_1 = self.conduit.save_unit(unit_1)

        #   Verify the returned unit
        self.assertTrue(unit_1 is not None)
        self.assertTrue(unit_1.id is not None)

        #   Verify the unit exists in the database
        db_unit = self.query_manager.get_content_unit_by_id(TYPE_1_DEF.id, unit_1.id)
        self.assertTrue(db_unit is not None)

        #   Verify the repo association exists
        associated_units = list(RepoContentUnit.get_collection().find({'repo_id' : 'repo-1'}))
        self.assertEqual(1, len(associated_units))

    def test_init_no_relative_path(self):
        """
        Makes sure passing a none relative path doesn't error.
        """

        # Test
        unit_1_key = {'key-1' : 'unit_1'}
        unit_1_metadata = {'meta_1' : 'value_1'}
        unit_1 = self.conduit.init_unit(TYPE_1_DEF.id, unit_1_key, unit_1_metadata, None)

        # Verify
        self.assertTrue(unit_1.storage_path is None)

    def test_update_unit(self):
        """
        Tests saving a unit that already exists.
        """

        # Setup
        unit_1_key = {'key-1' : 'unit_1'}
        unit_1_metadata = {'meta_1' : 'value_1'}
        unit_1 = self.conduit.init_unit(TYPE_1_DEF.id, unit_1_key, unit_1_metadata, '/foo/bar')
        self.conduit.save_unit(unit_1)

        # Test
        unit_1_new_metadata = {'meta_1' : 'value_2', 'meta_2' : 'value_2'}
        unit_1_updated = self.conduit.init_unit(TYPE_1_DEF.id, unit_1_key, unit_1_new_metadata, '/foo/bar')
        self.conduit.save_unit(unit_1_updated)

        # Verify database metadata
        db_unit = self.query_manager.get_content_unit_by_id(TYPE_1_DEF.id, unit_1.id)
        self.assertTrue(db_unit is not None)
        self.assertEqual('value_2', db_unit['meta_1'])

        # Verify only one repo association
        associated_units = list(RepoContentUnit.get_collection().find({'repo_id' : 'repo-1'}))
        self.assertEqual(1, len(associated_units))

    def test_get_remove_unit(self):
        """
        Tests retrieving units through the conduit and removing them.
        """

        # Setup
        unit_1_key = {'key-1' : 'unit_1'}
        unit_1_metadata = {'meta_1' : 'value_1'}
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

        #   Verify repo association removed in the database
        associated_units = list(RepoContentUnit.get_collection().find({'repo_id' : 'repo-1'}))
        self.assertEqual(0, len(associated_units))

        #   Verify the unit itself is still in the database
        db_unit = self.query_manager.get_content_unit_by_id(TYPE_1_DEF.id, unit_1.id)
        self.assertTrue(db_unit is not None)

    def test_link_unit(self):
        """
        Tests creating a unit reference.
        """

        # Setup
        unit_1_key = {'key-1' : 'unit_1'}
        unit_1_metadata = {'meta_1' : 'value_1'}
        unit_1 = self.conduit.init_unit(TYPE_1_DEF.id, unit_1_key, unit_1_metadata, '/foo/bar')
        unit_1 = self.conduit.save_unit(unit_1)

        unit_2_key = {'key-2a' : 'unit_2', 'key-2b' : 'unit_2'}
        unit_2_metadata = {}
        unit_2 = self.conduit.init_unit(TYPE_2_DEF.id, unit_2_key, unit_2_metadata, '/foo/bar')
        unit_2 = self.conduit.save_unit(unit_2)

        # Test
        self.conduit.link_unit(unit_2, unit_1)

        # Verify
        parent = self.query_manager.get_content_unit_by_id(TYPE_2_DEF.id, unit_2.id)
        self.assertTrue('_type_1_references' in parent)
        self.assertTrue(unit_1.id in parent['_type_1_references'])

    def test_link_unit_bidirectional(self):
        """
        Tests creating a bidirectional unit reference.
        """

        # Setup
        unit_1_key = {'key-1' : 'unit_1'}
        unit_1_metadata = {'meta_1' : 'value_1'}
        unit_1 = self.conduit.init_unit(TYPE_1_DEF.id, unit_1_key, unit_1_metadata, '/foo/bar')
        unit_1 = self.conduit.save_unit(unit_1)

        unit_2_key = {'key-2a' : 'unit_2', 'key-2b' : 'unit_2'}
        unit_2_metadata = {}
        unit_2 = self.conduit.init_unit(TYPE_2_DEF.id, unit_2_key, unit_2_metadata, '/foo/bar')
        unit_2 = self.conduit.save_unit(unit_2)

        # Test
        self.conduit.link_unit(unit_2, unit_1, bidirectional=True)

        # Verify
        parent = self.query_manager.get_content_unit_by_id(TYPE_2_DEF.id, unit_2.id)
        self.assertTrue('_type_1_references' in parent)
        self.assertTrue(unit_1.id in parent['_type_1_references'])

        parent = self.query_manager.get_content_unit_by_id(TYPE_1_DEF.id, unit_1.id)
        self.assertTrue('_type_2_references' in parent)
        self.assertTrue(unit_2.id in parent['_type_2_references'])

    def test_get_set_scratchpad(self):
        """
        Tests scratchpad calls.
        """

        # Setup
        self.importer_manager.set_importer('repo-1', 'mock-importer', {})

        # Test - get no scratchpad
        self.assertTrue(self.conduit.get_scratchpad() is None)

        # Test - set scrathpad
        value = 'dragon'
        self.conduit.set_scratchpad(value)

        # Test - get updated value
        self.assertEqual(value, self.conduit.get_scratchpad())

    def test_build_report(self):
        """
        Tests that the conduit correctly inserts the count values into the report.
        """

        # Setup

        #   Created - 10
        for i in range(0, 10):
            unit_key = {'key-1' : 'unit_%d' % i}
            unit = self.conduit.init_unit(TYPE_1_DEF.id, unit_key, {}, '/foo/bar')
            self.conduit.save_unit(unit)

        #   Removed - 1
        doomed = self.conduit.get_units()[0]
        self.conduit.remove_unit(doomed)

        #   Updated - 1
        update_me = self.conduit.init_unit(TYPE_1_DEF.id, {'key-1' : 'unit_5'}, {}, '/foo/bar')
        self.conduit.save_unit(update_me)

        # Test
        report = self.conduit.build_report('summary', 'details')

        # Verify
        self.assertTrue(isinstance(report, SyncReport))
        self.assertEqual(10, report.added_count)
        self.assertEqual(1, report.removed_count)
        self.assertEqual(1, report.updated_count)
        self.assertEqual('summary', report.summary)
        self.assertEqual('details', report.details)

    # -- error tests ----------------------------------------------------------

    # The following tests make sure error conditions are always wrapped in a
    # RepoSyncConduitException

    def test_get_units_with_error(self):
        # Setup
        self.conduit._RepoSyncConduit__association_manager = mock.Mock()
        self.conduit._RepoSyncConduit__association_manager.get_units.side_effect = Exception()

        # Test
        try:
            self.conduit.get_units()
            self.fail('Exception expected')
        except RepoSyncConduitException, e:
            print(e) # for coverage

    def test_init_unit_with_error(self):
        # Setup
        self.conduit._RepoSyncConduit__content_query_manager = mock.Mock()
        self.conduit._RepoSyncConduit__content_query_manager.request_content_unit_file_path.side_effect = Exception()

        # Test
        self.assertRaises(RepoSyncConduitException, self.conduit.init_unit, 't', {}, {}, 'p')

    def test_save_unit_with_error(self):
        # Setup
        self.conduit._RepoSyncConduit__content_query_manager = mock.Mock()
        self.conduit._RepoSyncConduit__content_query_manager.request_content_unit_file_path.side_effect = Exception()

        # Test
        self.assertRaises(RepoSyncConduitException, self.conduit.save_unit, None)

    def test_remove_unit_with_error(self):
        # Setup
        self.conduit._RepoSyncConduit__association_manager = mock.Mock()
        self.conduit._RepoSyncConduit__association_manager.unassociate_unit_by_id.side_effect = Exception()

        # Test
        self.assertRaises(RepoSyncConduitException, self.conduit.remove_unit, None)

    def test_link_unit_with_error(self):
        # Setup
        self.conduit._RepoSyncConduit__content_manager = mock.Mock()
        self.conduit._RepoSyncConduit__content_manager.link_referenced_content_units.side_effect = Exception()

        # Test
        self.assertRaises(RepoSyncConduitException, self.conduit.link_unit, None, None)

    def test_scratchpad_with_error(self):
        # Setup
        self.conduit._RepoSyncConduit__importer_manager = mock.Mock()
        self.conduit._RepoSyncConduit__importer_manager.get_importer_scratchpad.side_effect = Exception()
        self.conduit._RepoSyncConduit__importer_manager.set_importer_scratchpad.side_effect = Exception()

        # Test
        self.assertRaises(RepoSyncConduitException, self.conduit.get_scratchpad)
        self.assertRaises(RepoSyncConduitException, self.conduit.set_scratchpad, 'foo')

    # -- utilities ------------------------------------------------------------

    def _conduit(self, repo_id):
        """
        Convenience method for creating a conduit.
        """
        conduit = RepoSyncConduit(repo_id, 'test-importer', self.repo_manager, self.importer_manager, self.sync_manager,
                                  self.association_manager, self.content_manager, self.query_manager)
        return conduit