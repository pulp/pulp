# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import shutil
import tempfile

from base_db_upgrade import BaseDbUpgradeTests

from pulp.server.upgrade.db import (all_repos, iso_repos, yum_repos)
from pulp.server.upgrade.filesystem import repos


class WorkingDirUpgradeTests(BaseDbUpgradeTests):

    def setUp(self):
        super(WorkingDirUpgradeTests, self).setUp()

        # This script occurs after the DB is upgraded, so simulate the
        # necessary preconditions
        yum_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)
        iso_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)
        all_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        self.tmp_dir = tempfile.mkdtemp(prefix='working-dir-unit-test')
        repos.WORKING_DIR_ROOT = self.tmp_dir

    def tearDown(self):
        super(WorkingDirUpgradeTests, self).tearDown()

        shutil.rmtree(self.tmp_dir)

    def test_upgrade(self):
        # Test
        report = repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(report.success)

        all_repos = self.tmp_test_db.database.repos.find({})
        self.assertTrue(all_repos.count() > 0)
        for r in all_repos:
            working_dir = repos.repository_working_dir(r['id'], mkdir=False)
            self.assertTrue(os.path.exists(working_dir), msg='Missing: %s' % working_dir)

        repo_importers = self.tmp_test_db.database.repo_importers.find({})
        self.assertTrue(repo_importers.count() > 0)
        for i in repo_importers:
            working_dir = repos.importer_working_dir(i['importer_type_id'], i['repo_id'], mkdir=False)
            self.assertTrue(os.path.exists(working_dir), msg='Missing: %s' % working_dir)

        repo_distributors = self.tmp_test_db.database.repo_distributors.find({})
        self.assertTrue(repo_distributors.count() > 0)
        for d in repo_distributors:
            working_dir = repos.distributor_working_dir(d['distributor_type_id'], d['repo_id'], mkdir=False)
            self.assertTrue(os.path.exists(working_dir), msg='Missing: %s' % working_dir)

