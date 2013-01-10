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
DB_FILE_PATH = os.path.join(DB_DIR, 'unit_test.tar.gz')


def configure_for_non_unit_test_db():
    """
    Used to tweak the settings to run against the sample DBs that jdob collected.
    Once the bulk of upgrade has been debugged this can be deleted.
    """
    import test_db_yum_repos
    from pulp.server.upgrade.db import yum_repos as repo_db_upgrades

    DB_FILE_PATH = '/home/jdob/code/pulp/databases/large.tar.gz'

    # These rely on the filesystem being in a specific state
    repo_db_upgrades.SKIP_GPG_KEYS = True
    repo_db_upgrades.SKIP_SERVER_CONF = True

    # These tests munge the repos to point to a place on disk and can only
    # run against the unit test DB
    test_db_yum_repos.RepoGpgKeyTests.ENABLED = False


class BaseDbUpgradeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseDbUpgradeTests, cls).setUpClass()
#        configure_for_non_unit_test_db()

    def setUp(self):
        super(BaseDbUpgradeTests, self).setUp()

        self.v1_db_name = 'pulp_upgrade_unit'
        self.tmp_db_name = 'pulp_upgrade_unit_tmp'
        db_file = DB_FILE_PATH

        self.v1_test_db = PulpTestDatabase(self.v1_db_name)
        self.v1_test_db.delete()
        self.v1_test_db.load_from_file(db_file)

        self.tmp_test_db = PulpTestDatabase(self.tmp_db_name)
        self.tmp_test_db.delete()

    def tearDown(self):
        super(BaseDbUpgradeTests, self).tearDown()

        self.v1_test_db.delete()
        self.tmp_test_db.delete()


