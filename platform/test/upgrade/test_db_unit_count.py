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

from base_db_upgrade import BaseDbUpgradeTests
from pulp.server.upgrade.db import units, unit_count, iso_repos, yum_repos
from pulp.server.upgrade.model import UpgradeStepReport


class UnitCountUpgradeTests(BaseDbUpgradeTests):

    def setUp(self):
        super(UnitCountUpgradeTests, self).setUp()

        yum_repos.SKIP_SERVER_CONF = True
        yum_repos.SKIP_GPG_KEYS = True
        iso_repos.SKIP_SERVER_CONF = True
        units.SKIP_FILES = True

    def tearDown(self):
        super(UnitCountUpgradeTests, self).tearDown()

        yum_repos.SKIP_SERVER_CONF = False
        yum_repos.SKIP_GPG_KEYS = False
        iso_repos.SKIP_SERVER_CONF = False
        units.SKIP_FILES = False

    def test_upgrade(self):
        # Setup
        yum_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)
        iso_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)
        units.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Test
        report = unit_count.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        ass_coll = self.tmp_test_db.database.repo_content_units
        v2_repos = self.tmp_test_db.database.repos.find()
        for v2_repo in v2_repos:
            expected = ass_coll.find({'repo_id' : v2_repo['id']}).count()
            found = v2_repo['content_unit_count']

            self.assertEqual(expected, found,
                             msg='Repository [%s] Found [%s] Expected [%s]' %
                             (v2_repo['id'], found, expected))
