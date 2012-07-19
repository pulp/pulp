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

from pulp.plugins.conduits.mixins import ImporterConduitException
from pulp.plugins.conduits.repo_sync import RepoSyncConduit
from pulp.plugins.model import SyncReport
import pulp.plugins.types.database as types_database
import pulp.plugins.types.model as types_model
from pulp.server.db.model.repository import Repo, RepoContentUnit
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.repo.importer as importer_manager
import pulp.server.managers.repo.sync as sync_manager
import pulp.server.managers.repo.unit_association as association_manager
import pulp.server.managers.repo.unit_association_query as association_query_manager
import pulp.server.managers.content.cud as content_manager
import pulp.server.managers.content.query as query_manager

# constants --------------------------------------------------------------------

TYPE_1_DEF = types_model.TypeDefinition('type_1', 'Type 1', 'One', ['key-1'], ['search-1'], ['type_2'])
TYPE_2_DEF = types_model.TypeDefinition('type_2', 'Type 2', 'Two', ['key-2a', 'key-2b'], [], ['type_1'])

# -- test cases ---------------------------------------------------------------

class RepoSyncConduitTests(base.PulpServerTests):

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
        self.association_query_manager = association_query_manager.RepoUnitAssociationQueryManager()
        self.content_manager = content_manager.ContentManager()
        self.query_manager = query_manager.ContentQueryManager()

        self.repo_manager.create_repo('repo-1')
        self.conduit = RepoSyncConduit('repo-1', 'test-importer', 'importer', 'importer-id')

    def test_str(self):
        """
        Makes sure the __str__ implementation does not raise an error.
        """
        str(self.conduit)

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

    def test_build_reports(self):
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
        success_report = self.conduit.build_success_report('summary', 'details')
        failure_report = self.conduit.build_failure_report('summary', 'details')

        # Verify
        self.assertEqual(success_report.success_flag, True)
        self.assertEqual(failure_report.success_flag, False)

        for r in (success_report, failure_report):
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
