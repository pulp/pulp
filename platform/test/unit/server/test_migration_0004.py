# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
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

from pulp.server.db.migrate.models import MigrationModule
from pulp.server.db.model.repository import Repo, RepoContentUnit
import base


class TestMigrationContentUnitCount(base.PulpServerTests):
    def setUp(self):
        super(TestMigrationContentUnitCount, self).setUp()
        self.module = MigrationModule('pulp.server.db.migrations.0004_content_unit_counts')._module

    @mock.patch('pulp.server.db.model.repository.Repo.get_collection')
    @mock.patch('pulp.server.managers.repo.cud.RepoManager.rebuild_content_unit_counts')
    def test_calls(self, mock_rebuild, mock_get_collection):
        self.module.migrate()

        mock_rebuild.assert_called_once_with()
        mock_update = mock_get_collection.return_value.update
        self.assertEqual(mock_update.call_count, 1)

        self.assertTrue(mock_update.call_args[1].get('safe') is True)
        self.assertEqual(mock_update.call_args[0][0], {})
        self.assertEqual(mock_update.call_args[0][1], {'$unset': {'content_unit_count': 1}})

    def test_with_db(self):
        REPO_ID = 'repo123'
        repo_collection = Repo.get_collection()
        repo_collection.save({'id': REPO_ID, 'content_unit_count': 0})

        assoc_collection = RepoContentUnit.get_collection()
        assoc_collection.insert({'repo_id': REPO_ID, 'unit_type_id': 'rpm', 'unit_id':'unit1'})
        assoc_collection.insert({'repo_id': REPO_ID, 'unit_type_id': 'rpm', 'unit_id':'unit2'})

        self.module.migrate()

        repo = repo_collection.find({'id': REPO_ID})[0]

        self.assertTrue('content_unit_count' not in repo)
        self.assertEqual(repo['content_unit_counts'], {'rpm': 2})

        # cleanup
        repo_collection.remove({'id': REPO_ID})
        assoc_collection.remove({'repo_id': REPO_ID})
