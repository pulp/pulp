# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import mock
import os
import shutil
import tempfile
import unittest

from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository, SyncReport, Unit

from pulp_puppet.common import constants
from pulp_puppet.importer import sync
from pulp_puppet.importer.sync import PuppetModuleSyncRun

# -- constants ----------------------------------------------------------------

FEED = 'file://' + os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data', 'repos', 'valid')
INVALID_FEED = 'file://' + os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data', 'repos', 'invalid')

# Simulated location where Pulp will store synchronized units
MOCK_PULP_STORAGE_LOCATION = tempfile.mkdtemp(prefix='var-lib')

# -- test cases ---------------------------------------------------------------

class MockConduit(mock.MagicMock):

    def build_success_report(self, summary, details):
        return SyncReport(True, -1, -1, -1, summary, details)

    def build_failure_report(self, summary, details):
        return SyncReport(False, -1, -1, -1, summary, details)

    def init_unit(self, type_id, unit_key, unit_metadata, relative_path):
        storage_path = os.path.join(MOCK_PULP_STORAGE_LOCATION, relative_path)
        return Unit(type_id, unit_key, unit_metadata, storage_path)

class PuppetModuleSyncRunTests(unittest.TestCase):

    def setUp(self):
        self.working_dir = tempfile.mkdtemp(prefix='puppet-sync-tests')
        self.repo = Repository('test-repo', working_dir=self.working_dir)
        self.conduit = MockConduit()
        self.config = PluginCallConfiguration({}, {
            constants.CONFIG_FEED : FEED,
        })
        self.is_cancelled_call = mock.MagicMock().is_cancelled_call

        self.run = PuppetModuleSyncRun(self.repo, self.conduit, self.config,
                                       self.is_cancelled_call)

    def tearDown(self):
        shutil.rmtree(self.working_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MOCK_PULP_STORAGE_LOCATION)

    def test_perform_sync(self):
        # Test
        report = self.run.perform_sync()

        # Verify

        # Units copied to simulated Pulp storage
        expected_module_filenames = ['adob-good-2.0.0.tar.gz', 'jdob-valid-1.1.0.tar.gz']
        for f in expected_module_filenames:
            expected_path = os.path.join(MOCK_PULP_STORAGE_LOCATION, f)
            self.assertTrue(os.path.exists(expected_path))

        # Final Report
        self.assertTrue(report.success_flag)
        self.assertTrue(report.summary['total_execution_time'] is not None)
        self.assertTrue(report.summary['total_execution_time'] > -1)

        # Progress Reporting
        pr = self.run.progress_report
        self.assertEqual(pr.metadata_state, sync.STATE_SUCCESS)
        self.assertEqual(pr.metadata_query_total_count, 1)
        self.assertEqual(pr.metadata_query_finished_count, 1)
        self.assertTrue(pr.metadata_execution_time is not None)

        self.assertEqual(pr.modules_state, sync.STATE_SUCCESS)
        self.assertEqual(pr.modules_total_count, 2)
        self.assertEqual(pr.modules_finished_count, 2)
        self.assertTrue(pr.modules_execution_time is not None)

        # Number of times update was called on the progress report
        self.assertEqual(self.conduit.set_progress.call_count, 9)

    def test_perform_sync_metadata_error(self):
        # Setup
        self.config.repo_plugin_config[constants.CONFIG_FEED] = INVALID_FEED

        # Test
        report = self.run.perform_sync()

        # Verify
        self.assertTrue(not report.success_flag)

        pr = self.run.progress_report
        self.assertEqual(pr.metadata_state, sync.STATE_FAILED)
        self.assertEqual(pr.metadata_query_total_count, 1)
        self.assertEqual(pr.metadata_query_finished_count, 0)
        self.assertEqual(pr.metadata_execution_time, None)

        self.assertEqual(pr.modules_state, sync.STATE_NOT_STARTED)
        self.assertEqual(pr.modules_total_count, None)
        self.assertEqual(pr.modules_finished_count, None)
        self.assertEqual(pr.modules_execution_time, None)
