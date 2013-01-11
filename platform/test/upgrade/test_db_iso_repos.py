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

import mock

from pulp.server.compat import ObjectId
from pulp.server.upgrade.model import UpgradeStepReport
from pulp.server.upgrade.db import iso_repos

from base_db_upgrade import BaseDbUpgradeTests


DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')


class IsoRepoUpgradeDefaultsTests(unittest.TestCase):

    def test_skip_is_disabled(self):
        self.assertTrue(not iso_repos.SKIP_SERVER_CONF)


class ReposUpgradeTests(BaseDbUpgradeTests):

    def setUp(self):
        super(ReposUpgradeTests, self).setUp()
        iso_repos.SKIP_SERVER_CONF = True

    def tearDown(self):
        super(ReposUpgradeTests, self).tearDown()
        iso_repos.SKIP_SERVER_CONF = False

    def test_repos(self):
        # Test
        report = iso_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        v1_iso_repos = self.v1_test_db.database.repos.find({'content_types' : iso_repos.V1_ISO_REPO})
        for v1_repo in v1_iso_repos:
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

            v2_importer = self.tmp_test_db.database.repo_importers.find_one({'repo_id' : repo_id})
            self.assertTrue(v2_importer is not None)
            self.assertTrue(isinstance(v2_importer['_id'], ObjectId))
            self.assertEqual(v2_importer['id'], iso_repos.ISO_IMPORTER_ID)
            self.assertEqual(v2_importer['importer_type_id'], iso_repos.ISO_IMPORTER_TYPE_ID)
            self.assertEqual(v2_importer['last_sync'], v1_repo['last_sync'])

            config = v2_importer['config']
            self.assertEqual(config['feed_url'], v1_repo['source']['url'])
            self.assertEqual(config['ssl_ca_cert'], v1_repo['feed_ca'])
            self.assertEqual(config['ssl_client_cert'], v1_repo['feed_cert'])
            self.assertTrue('skip' not in config)
            self.assertTrue('proxy_url' not in config)
            self.assertTrue('proxy_port' not in config)
            self.assertTrue('proxy_user' not in config)
            self.assertTrue('proxy_pass' not in config)

            # Distributor
            v2_distributor = self.tmp_test_db.database.repo_distributors.find_one({'repo_id' : repo_id})
            self.assertTrue(v2_distributor is not None)
            self.assertTrue(isinstance(v2_distributor['_id'], ObjectId))
            self.assertEqual(v2_distributor['id'], iso_repos.ISO_DISTRIBUTOR_ID)
            self.assertEqual(v2_distributor['distributor_type_id'], iso_repos.ISO_DISTRIBUTOR_TYPE_ID)
            self.assertEqual(v2_distributor['auto_publish'], True)
            self.assertEqual(v2_distributor['scratchpad'], None)
            self.assertEqual(v2_distributor['last_publish'], v1_repo['last_sync'])

            config = v2_distributor['config']
            self.assertEqual(config['relative_url'], v1_repo['relative_path'])
            self.assertEqual(config['http'], False)
            self.assertEqual(config['https'], True)

    def test_repos_idempotency(self):
        # Setup
        iso_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Test
        report = iso_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        self.assertTrue(self.v1_test_db.database.repos.count() > 0)
        v1_repos = self.v1_test_db.database.repos.find({'content_types' : iso_repos.V1_ISO_REPO})
        for v1_repo in v1_repos:
            repo_id = v1_repo['id']

            v2_repo = self.tmp_test_db.database.repos.find_one({'id' : repo_id})
            self.assertTrue(v2_repo is not None)

            v2_importer = self.tmp_test_db.database.repo_importers.find_one({'repo_id' : repo_id})
            self.assertTrue(v2_importer is not None)

            v2_distributor = self.tmp_test_db.database.repo_distributors.find_one({'repo_id' : repo_id})
            self.assertTrue(v2_distributor is not None)

    @mock.patch('pulp.server.upgrade.db.iso_repos._repos')
    def test_repos_failed_repo_step(self, mock_repos_call):
        # Setup
        mock_repos_call.return_value = False

        # Test
        report = iso_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(not report.success)

    @mock.patch('pulp.server.upgrade.db.iso_repos._repo_importers')
    def test_repos_failed_importer_step(self, mock_importer_call):
        # Setup
        mock_importer_call.return_value = False

        # Test
        report = iso_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(not report.success)

    @mock.patch('pulp.server.upgrade.db.iso_repos._repo_distributors')
    def test_repos_failed_distributor_step(self, mock_distributor_call):
        # Setup
        mock_distributor_call.return_value = False

        # Test
        report = iso_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(not report.success)


class RepoUpgradeWithProxyTests(BaseDbUpgradeTests):

    def setUp(self):
        super(RepoUpgradeWithProxyTests, self).setUp()

        self.conf_orig = iso_repos.V1_SERVER_CONF
        iso_repos.V1_SERVER_CONF = os.path.join(DATA_DIR, 'server_configs', 'with-proxy.conf')
        iso_repos.SKIP_SERVER_CONF = False
        iso_repos.SKIP_GPG_KEYS = True

    def tearDown(self):
        super(RepoUpgradeWithProxyTests, self).tearDown()

        iso_repos.V1_SERVER_CONF = self.conf_orig
        iso_repos.SKIP_SERVER_CONF = False
        iso_repos.SKIP_GPG_KEYS = False

    def test_upgrade(self):
        # Test
        report = iso_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        v1_repos = self.v1_test_db.database.repos.find({'content_types' : iso_repos.V1_ISO_REPO})

        self.assertTrue(self.v1_test_db.database.repos.count() > 0)
        for v1_repo in v1_repos:
            repo_id = v1_repo['id']

            v2_importer = self.tmp_test_db.database.repo_importers.find_one({'repo_id' : repo_id})
            self.assertTrue(v2_importer is not None, msg='Missing importer for repo: %s' % repo_id)
            config = v2_importer['config']

            # Values taken from the with-proxy.conf file
            self.assertEqual(config['proxy_url'], 'http://localhost')
            self.assertEqual(config['proxy_port'], '8080')
            self.assertEqual(config['proxy_user'], 'admin')
            self.assertEqual(config['proxy_pass'], 'admin')
