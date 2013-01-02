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

# Full path to the DB that will be loaded for the test run
V1_DB_FILE_PATH = os.path.join(DB_DIR, 'test-fs-db.tar.gz')

class BaseFileUpgradeTests(unittest.TestCase):

    def setUp(self):
        super(BaseFileUpgradeTests, self).setUp()

        self.v1_db_name = 'pulp_upgrade_unit_fs'
        self.v2_db_name = 'pulp_upgrade_unit_fs_tmp'

        self.v1_test_db = PulpTestDatabase(self.v1_db_name)
        self.v1_test_db.load_from_file(V1_DB_FILE_PATH)

        self.v2_test_db = PulpTestDatabase(self.v2_db_name)

    def tearDown(self):
        super(BaseFileUpgradeTests, self).tearDown()


