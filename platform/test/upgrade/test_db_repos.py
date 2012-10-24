# -*- coding: utf-8 -*-
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from bson import ObjectId

from base_db_upgrade import BaseDbUpgradeTests
from pulp.server.upgrade.model import UpgradeStepReport
from pulp.server.upgrade.db import repos


class ReposUpgradeTests(BaseDbUpgradeTests):

    def setUp(self):
        super(ReposUpgradeTests, self).setUp()
        repos.SKIP_LOCAL_FILES = True

    def tearDown(self):
        super(ReposUpgradeTests, self).tearDown()
        repos.SKIP_LOCAL_FILES = False

    def test_repos(self):
        # Test
        report = repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        self.assertTrue(self.v1_test_db.database.repos.count() > 0)
        v1_repos = self.v1_test_db.database.repos.find()
        for v1_repo in v1_repos:
            repo_id = v1_repo['id']

            # Repo
            v2_repo = self.tmp_test_db.database.repos.find_one({'id' : repo_id})
            self.assertTrue(v2_repo is not None)
            self.assertTrue(isinstance(v2_repo['_id'], ObjectId))
            self.assertEqual(v2_repo['id'], v1_repo['id'])
            self.assertEqual(v2_repo['display_name'], v1_repo['name'])
            self.assertEqual(v2_repo['description'], None)
            self.assertEqual(v2_repo['scratchpad'], {})
            self.assertEqual(v2_repo['content_unit_count'], 0)

            # Importer
            v2_importer = self.tmp_test_db.database.repo_importers.find_one({'repo_id' : repo_id})
            self.assertTrue(v2_importer is not None)
            self.assertTrue(isinstance(v2_importer['_id'], ObjectId))
            self.assertEqual(v2_importer['id'], repos.YUM_IMPORTER_ID)
            self.assertEqual(v2_importer['importer_type_id'], repos.YUM_IMPORTER_TYPE_ID)
            self.assertEqual(v2_importer['last_sync'], v1_repo['last_sync'])

            config = v2_importer['config']
            self.assertEqual(config['feed'], v1_repo['source']['url'])
