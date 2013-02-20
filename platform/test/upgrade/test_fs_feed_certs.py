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
from base_file_upgrade import DATA_DIR

from pulp.server.upgrade.db import (all_repos, iso_repos, yum_repos)
from pulp.server.upgrade.filesystem import feed_certs, repos


class FeedCertificateTests(BaseDbUpgradeTests):

    def setUp(self):
        super(FeedCertificateTests, self).setUp()

        # Munge each repo to point to a sample cert and CA
        ca_cert_path = os.path.join(DATA_DIR, 'repo_related_files', 'feed_ca.crt')
        client_cert_path = os.path.join(DATA_DIR, 'repo_related_files', 'feed_cert.crt')

        v1_repos = self.v1_test_db.database.repos.find()
        for v1_repo in v1_repos:
            v1_repo['feed_ca'] = ca_cert_path
            v1_repo['feed_cert'] = client_cert_path
            self.v1_test_db.database.repos.save(v1_repo)

        # This script occurs after the DB is upgraded, so simulate the
        # necessary preconditions
        yum_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)
        iso_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)
        all_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # This script also relies on the working directories to be created
        self.tmp_dir = tempfile.mkdtemp(prefix='feeds-fs-unit-test')
        repos.WORKING_DIR_ROOT = self.tmp_dir
        repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

    def tearDown(self):
        super(FeedCertificateTests, self).tearDown()
        shutil.rmtree(self.tmp_dir)

    def test_upgrade(self):
        # Test
        report = feed_certs.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(report is not None)
        self.assertTrue(report.success)

        all_repo_importers = self.tmp_test_db.database.repo_importers.find({})
        self.assertTrue(all_repo_importers.count() > 0)
        for repo_importer in all_repo_importers:
            importer_working_dir = repos.importer_working_dir(repo_importer['importer_type_id'],
                                                              repo_importer['repo_id'],
                                                              mkdir=False)

            expected_cert_path = os.path.join(importer_working_dir, 'ssl_ca_cert')
            self.assertTrue(os.path.exists(expected_cert_path))
            self._assert_contents(expected_cert_path, repo_importer['config']['ssl_ca_cert'])

            expected_cert_path = os.path.join(importer_working_dir, 'ssl_client_cert')
            self.assertTrue(os.path.exists(expected_cert_path))
            self._assert_contents(expected_cert_path, repo_importer['config']['ssl_client_cert'])

    def _assert_contents(self, filename, contents):
        f = open(filename, 'r')
        found = f.read()
        f.close()

        self.assertEqual(found, contents)

