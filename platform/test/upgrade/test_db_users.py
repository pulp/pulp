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
from pulp.server.upgrade.db import users


class UsersUpgradeTests(BaseDbUpgradeTests):

    def test_users(self):
        # Test
        report = users.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        v1_roles = list(self.v1_test_db.database.roles.find().sort('name', 1))
        v2_roles = list(self.tmp_test_db.database.roles.find().sort('display_name', 1))
        self.assertEqual(len(v1_roles), len(v2_roles))

        for v1_role, v2_role in zip(v1_roles, v2_roles):
            self.assertTrue(v1_role['_id'] != v2_role['_id'])
            self.assertTrue(isinstance(v2_role['_id'], ObjectId))
            self.assertEqual(v1_role['name'], v2_role['display_name'])
            self.assertEqual(v1_role['permissions'], v2_role['permissions'])
            self.assertTrue('name' not in v2_role)

    def test_users_resumed(self):
        # Setup
        users.upgrade(self.v1_test_db.database, self.tmp_test_db.database)
        self.v1_test_db.database.roles.insert({'name' : 'new-to-v1', 'permissions' : {}})

        # Test
        report = users.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        v1_roles = list(self.v1_test_db.database.roles.find().sort('name', 1))
        v2_roles = list(self.tmp_test_db.database.roles.find().sort('display_name', 1))
        self.assertEqual(len(v1_roles), len(v2_roles))

    def test_users_idempotency(self):
        # Setup
        users.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Test
        report = users.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        v1_roles = list(self.v1_test_db.database.roles.find().sort('name', 1))
        v2_roles = list(self.tmp_test_db.database.roles.find().sort('display_name', 1))
        self.assertEqual(len(v1_roles), len(v2_roles))
