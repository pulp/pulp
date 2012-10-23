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

import os
import unittest

from db_loader import DB_DIR, PulpTestDatabase


class BaseDbUpgradeTests(unittest.TestCase):

    def setUp(self):
        super(BaseDbUpgradeTests, self).setUp()

        db_file = os.path.join(DB_DIR, 'unit_test.tar.gz')
        self.v1_db_name = 'pulp_upgrade_unit'
        self.tmp_db_name = 'pulp_upgrade_unit_tmp'

        self.v1_test_db = PulpTestDatabase(self.v1_db_name)
        self.v1_test_db.load_from_file(db_file)

        self.tmp_test_db = PulpTestDatabase(self.tmp_db_name)

    def tearDown(self):
        super(BaseDbUpgradeTests, self).tearDown()

        self.v1_test_db.delete()
        self.tmp_test_db.delete()


