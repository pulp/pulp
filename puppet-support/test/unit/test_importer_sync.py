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


class UnitsMockConduit(MockConduit):

    def get_units(self, criteria=None):
        units = [
            Unit(constants.TYPE_PUPPET_MODULE, {'name' : 'valid', 'version' : '1.1.0', 'author' : 'jdob'}, {}, ''),
            Unit(constants.TYPE_PUPPET_MODULE, {'name' : 'good', 'version' : '2.0.0', 'author' : 'adob'}, {}, ''),
        ]
        return units


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

        self.assertEqual(report.details['total_count'], 2)
        self.assertEqual(report.details['finished_count'], 2)
        self.assertEqual(report.details['error_count'], 0)

        # Progress Reporting
        pr = self.run.progress_report
        self.assertEqual(pr.metadata_state, constants.STATE_SUCCESS)
        self.assertEqual(pr.metadata_query_total_count, 1)
        self.assertEqual(pr.metadata_query_finished_count, 1)
        self.assertTrue(pr.metadata_execution_time is not None)
        self.assertEqual(pr.metadata_error_message, None)
        self.assertEqual(pr.metadata_exception, None)
        self.assertEqual(pr.metadata_traceback, None)

        self.assertEqual(pr.modules_state, constants.STATE_SUCCESS)
        self.assertEqual(pr.modules_total_count, 2)
        self.assertEqual(pr.modules_error_count, 0)
        self.assertEqual(pr.modules_finished_count, 2)
        self.assertTrue(pr.modules_execution_time is not None)
        self.assertEqual(pr.modules_error_message, None)
        self.assertEqual(pr.modules_exception, None)
        self.assertEqual(pr.modules_traceback, None)
        self.assertEqual(pr.modules_individual_errors, None)

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
        self.assertEqual(pr.metadata_state, constants.STATE_FAILED)
        self.assertEqual(pr.metadata_query_total_count, 1)
        self.assertEqual(pr.metadata_query_finished_count, 0)

        self.assertEqual(pr.modules_state, constants.STATE_NOT_STARTED)
        self.assertEqual(pr.modules_total_count, None)
        self.assertEqual(pr.modules_finished_count, None)

    @mock.patch('pulp_puppet.importer.sync.PuppetModuleSyncRun._resolve_remove_units')
    def test_perform_sync_with_remove_units(self, mock_resolve):
        # Setup
        remove_me = 'valid-1.1.0-jdob'
        mock_resolve.return_value = [remove_me]

        self.conduit = UnitsMockConduit()
        self.run.sync_conduit = self.conduit

        self.config.repo_plugin_config[constants.CONFIG_REMOVE_MISSING] = 'true'

        # Test
        report = self.run.perform_sync()

        # Verify
        self.assertEqual(1, self.conduit.remove_unit.call_count)

    @mock.patch('pulp_puppet.importer.sync.PuppetModuleSyncRun._parse_metadata')
    def test_perform_sync_no_metadata(self, mock_parse):
        # Setup
        mock_parse.return_value = None

        # Test
        report = self.run.perform_sync()

        # Verify
        self.assertTrue(report is not None)
        self.assertTrue(not report.success_flag)

        pr = self.run.progress_report
        self.assertEqual(pr.modules_state, constants.STATE_NOT_STARTED)

    @mock.patch('pulp_puppet.importer.sync.PuppetModuleSyncRun._create_downloader')
    def test_parse_metadata_retrieve_exception(self, mock_create):
        # Setup
        mock_create.side_effect = Exception()

        # Test
        report = self.run.perform_sync()

        # Verify
        self.assertTrue(not report.success_flag)

        pr = self.run.progress_report
        self.assertEqual(pr.metadata_state, constants.STATE_FAILED)
        self.assertEqual(pr.metadata_query_total_count, None)
        self.assertEqual(pr.metadata_query_finished_count, None)
        self.assertTrue(pr.metadata_execution_time is not None)
        self.assertTrue(pr.metadata_error_message is not None)
        self.assertTrue(pr.metadata_exception is not None)
        self.assertTrue(pr.metadata_traceback is not None)

        self.assertEqual(pr.modules_state, constants.STATE_NOT_STARTED)

    @mock.patch('pulp_puppet.importer.downloaders.local.LocalDownloader.retrieve_metadata')
    def test_parse_metadata_parse_exception(self, mock_retrieve):
        # Setup
        mock_retrieve.return_value = ['not parsable json']

        # Test
        report = self.run.perform_sync()

        # Test
        self.assertTrue(not report.success_flag)

        pr = self.run.progress_report
        self.assertEqual(pr.metadata_state, constants.STATE_FAILED)
        self.assertTrue(pr.metadata_execution_time is not None)
        self.assertTrue(pr.metadata_error_message is not None)
        self.assertTrue(pr.metadata_exception is not None)
        self.assertTrue(pr.metadata_traceback is not None)

        self.assertEqual(pr.modules_state, constants.STATE_NOT_STARTED)

    @mock.patch('pulp_puppet.importer.sync.PuppetModuleSyncRun._do_import_modules')
    def test_import_modules_exception(self, mock_import):
        # Setup
        mock_import.side_effect = Exception()

        # Test
        report = self.run.perform_sync()

        # Verify
        self.assertTrue(not report.success_flag)

        pr = self.run.progress_report
        self.assertEqual(pr.metadata_state, constants.STATE_SUCCESS)
        self.assertEqual(pr.metadata_query_total_count, 1)
        self.assertEqual(pr.metadata_query_finished_count, 1)
        self.assertTrue(pr.metadata_execution_time is not None)
        self.assertTrue(pr.metadata_error_message is None)
        self.assertTrue(pr.metadata_exception is None)
        self.assertTrue(pr.metadata_traceback is None)

        self.assertEqual(pr.modules_state, constants.STATE_FAILED)
        self.assertEqual(pr.modules_total_count, None)
        self.assertEqual(pr.modules_finished_count, None)
        self.assertTrue(pr.modules_execution_time is not None)
        self.assertTrue(pr.modules_error_message is not None)
        self.assertTrue(pr.modules_exception is not None)
        self.assertTrue(pr.modules_traceback is not None)

    @mock.patch('pulp_puppet.importer.sync.PuppetModuleSyncRun._add_new_module')
    def test_do_import_add_exception(self, mock_add):
        # Setup
        mock_add.side_effect = Exception()

        # Test
        report = self.run.perform_sync()

        # Verify

        # Failed modules still represent a successful sync and import modules
        # step as far as states are concerned. But at the individual module
        # level, the errors should be stored per failed module and the counts
        # accurately reflect successes v. failures.

        self.assertTrue(report.success_flag)

        pr = self.run.progress_report
        self.assertEqual(pr.metadata_state, constants.STATE_SUCCESS)

        self.assertEqual(pr.modules_state, constants.STATE_SUCCESS)
        self.assertEqual(pr.modules_total_count, 2)
        self.assertEqual(pr.modules_finished_count, 0)
        self.assertEqual(pr.modules_error_count, 2)
        self.assertEqual(len(pr.modules_individual_errors), 2)
        self.assertTrue(pr.modules_execution_time is not None)
        self.assertTrue(pr.modules_error_message is None)
        self.assertTrue(pr.modules_exception is None)
        self.assertTrue(pr.modules_traceback is None)
