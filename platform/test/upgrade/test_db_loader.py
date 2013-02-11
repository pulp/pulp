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

import pymongo

from db_loader import DB_DIR, PulpTestDatabase


class PulpTestDatabaseTests(unittest.TestCase):

    def test_load_delete(self):
        # Setup
        db_file = os.path.join(DB_DIR, 'unit_test.tar.gz')
        db_name = 'pulp_upgrade_unit'

        # Test - Load
        test_db = PulpTestDatabase(db_name)
        test_db.load_from_file(db_file)

        # Verify - Load
        db = test_db.database
        self.assertTrue('repos' in db.collection_names())

        # Test - Delete
        test_db.delete()

        # Verify - Delete
        conn = pymongo.Connection()
        self.assertTrue(db_name not in conn.database_names())

