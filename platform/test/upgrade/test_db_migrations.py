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

from pulp.server.upgrade.db import migrations

from base_db_upgrade import BaseDbUpgradeTests


class MigrationsTests(BaseDbUpgradeTests):

    def test_upgrade(self):
        # Test
        report = migrations.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(report.success)

        migrations_coll = self.tmp_test_db.database.migration_trackers
        all_migrations = migrations_coll.find()
        self.assertEqual(len(migrations.MIGRATION_PACKAGES), all_migrations.count())

        for m in all_migrations:
            self.assertEqual(m['version'], 0)

    def test_upgrade_idempotency(self):
        # Setup
        migrations.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Test
        migrations.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        migrations_coll = self.tmp_test_db.database.migration_trackers
        all_migrations = migrations_coll.find()
        self.assertEqual(len(migrations.MIGRATION_PACKAGES), all_migrations.count())

