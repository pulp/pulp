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

import sys
import traceback

import base_cli

from pulp.client.extensions.core import TAG_FAILURE, TAG_PROGRESS_BAR, TAG_SPINNER

from pulp_puppet.common import constants
from pulp_puppet.common.publish_progress import  PublishProgressReport
from pulp_puppet.common.sync_progress import SyncProgressReport
from pulp_puppet.extension.admin.status import PuppetStatusRenderer


IMPORTER_REPORT = {
    'modules': {
        'error_message': None,
        'execution_time': 0,
        'total_count': 0,
        'traceback': None,
        'individual_errors': None,
        'state': 'success',
        'error_count': 0,
        'error': None,
        'finished_count': 0
    },
    'metadata': {
        'query_finished_count': 2,
        'traceback': None,
        'execution_time': 10,
        'query_total_count': 2,
        'error_message': None,
        'state': 'success',
        'error': None,
        'current_query': 'http://forge.puppetlabs.com/modules.json?q=thias/php'
    }
}

DISTRIBUTOR_REPORT = {
    'modules': {
        'error_message': None,
        'execution_time': 0,
        'total_count': 12,
        'traceback': None,
        'individual_errors': None,
        'state': 'success',
        'error_count': 0,
        'error': None,
        'finished_count': 12
    },
    'publishing': {
        'http': 'success',
        'https': 'success'
    },
    'metadata': {
        'execution_time': 0,
        'state': 'success',
        'error_message': None,
        'error': None,
        'traceback': None
    }
}

FULL_REPORT = {
    'puppet_importer' : IMPORTER_REPORT,
    'puppet_distributor' : DISTRIBUTOR_REPORT,
}

class PuppetStatusRendererTests(base_cli.ExtensionTests):

    def setUp(self):
        super(PuppetStatusRendererTests, self).setUp()
        self.renderer = PuppetStatusRenderer(self.context)

        self.config['logging'] = {'filename' : 'test-extension-status.log'}

        self.sync_report = SyncProgressReport.from_progress_dict(IMPORTER_REPORT)
        self.publish_report = PublishProgressReport.from_progress_dict(DISTRIBUTOR_REPORT)

    def test_display_sync_metadata(self):
        # Test
        self.renderer._display_sync_metadata_step(self.sync_report)

        # Verify
        expected_tags = ['download-metadata', TAG_PROGRESS_BAR]
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.sync_metadata_last_state, constants.STATE_SUCCESS)

    def test_display_sync_metadata_not_started(self):
        # Setup
        self.sync_report.metadata_state = constants.STATE_NOT_STARTED

        # Test
        self.renderer._display_sync_metadata_step(self.sync_report)

        # Verify
        self.assertEqual(0, len(self.prompt.get_write_tags()))
        self.assertEqual(self.renderer.sync_metadata_last_state, constants.STATE_NOT_STARTED)

    def test_display_sync_metadata_failed(self):
        # Setup
        self.sync_report.metadata_state = constants.STATE_FAILED

        # Test
        self.renderer._display_sync_metadata_step(self.sync_report)

        # Verify
        expected_tags = ['download-metadata', TAG_FAILURE, TAG_FAILURE, TAG_FAILURE]
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.sync_metadata_last_state, constants.STATE_FAILED)

    def test_display_sync_modules(self):
        # Test
        self.renderer._display_sync_modules_step(self.sync_report)

        # Verify
        expected_tags = ['downloading', TAG_PROGRESS_BAR]
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.sync_modules_last_state, constants.STATE_SUCCESS)

    def test_display_sync_modules_not_started(self):
        # Setup
        self.sync_report.modules_state = constants.STATE_NOT_STARTED

        # Test
        self.renderer._display_sync_modules_step(self.sync_report)

        # Verify
        expected_tags = []
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.sync_modules_last_state, constants.STATE_NOT_STARTED)

    def test_display_sync_modules_failed(self):
        # Setup
        self.sync_report.modules_state = constants.STATE_FAILED

        # Test
        self.renderer._display_sync_modules_step(self.sync_report)

        # Verify
        expected_tags = ['downloading', TAG_FAILURE, TAG_FAILURE, TAG_FAILURE]
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.sync_modules_last_state, constants.STATE_FAILED)

    def test_display_publish_modules(self):
        # Test
        self.renderer._display_publish_modules_step(self.publish_report)

        # Verify
        expected_tags = ['publishing', TAG_PROGRESS_BAR]
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.publish_modules_last_state, constants.STATE_SUCCESS)

    def test_display_publish_modules_not_started(self):
        # Setup
        self.publish_report.modules_state = constants.STATE_NOT_STARTED

        # Test
        self.renderer._display_publish_modules_step(self.publish_report)

        # Verify
        expected_tags = []
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.publish_modules_last_state, constants.STATE_NOT_STARTED)

    def test_display_publish_modules_failed(self):
        # Setup
        self.publish_report.modules_state = constants.STATE_FAILED

        # Test
        self.renderer._display_publish_modules_step(self.publish_report)

        # Verify
        expected_tags = ['publishing', TAG_FAILURE, TAG_FAILURE, TAG_FAILURE]
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.publish_modules_last_state, constants.STATE_FAILED)

    def test_display_publish_metadata(self):
        # Test
        self.renderer._display_publish_metadata_step(self.publish_report)

        # Verify
        expected_tags = ['generating', TAG_SPINNER, 'completed']
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.publish_metadata_last_state, constants.STATE_SUCCESS)

    def test_display_publish_metadata_not_started(self):
        # Setup
        self.publish_report.metadata_state = constants.STATE_NOT_STARTED

        # Test
        self.renderer._display_publish_metadata_step(self.publish_report)

        # Verify
        expected_tags = []
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.publish_metadata_last_state, constants.STATE_NOT_STARTED)

    def test_display_publish_metadata_in_progress(self):
        # Setup
        self.renderer.publish_metadata_last_state = constants.STATE_RUNNING
        self.publish_report.metadata_state = constants.STATE_RUNNING

        # Test
        self.renderer._display_publish_metadata_step(self.publish_report)

        # Verify
        expected_tags = [TAG_SPINNER]
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.publish_metadata_last_state, constants.STATE_RUNNING)

    def test_display_publish_metadata_complete(self):
        # Setup
        self.renderer.publish_metadata_last_state = constants.STATE_RUNNING
        self.publish_report.metadata_state = constants.STATE_SUCCESS

        # Test
        self.renderer._display_publish_metadata_step(self.publish_report)

        # Verify
        expected_tags = [TAG_SPINNER, 'completed']
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.publish_metadata_last_state, constants.STATE_SUCCESS)

    def test_display_publish_metadata_failed(self):
        # Setup
        self.renderer.publish_metadata_last_state = constants.STATE_RUNNING
        self.publish_report.metadata_state = constants.STATE_FAILED

        # Test
        self.renderer._display_publish_metadata_step(self.publish_report)

        # Verify
        expected_tags = [TAG_SPINNER, TAG_FAILURE, TAG_FAILURE, TAG_FAILURE]
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.publish_metadata_last_state, constants.STATE_FAILED)

    def test_publsh_http_https(self):
        # Test
        self.renderer._display_publish_http_https_step(self.publish_report)

        # Verify
        expected_tags = ['http-completed', 'https-completed']
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.publish_http_last_state, constants.STATE_SUCCESS)
        self.assertEqual(self.renderer.publish_https_last_state, constants.STATE_SUCCESS)

    def test_publish_http_https_not_started(self):
        # Setup
        self.publish_report.publish_http = constants.STATE_NOT_STARTED
        self.publish_report.publish_https = constants.STATE_NOT_STARTED

        # Test
        self.renderer._display_publish_http_https_step(self.publish_report)

        # Verify
        expected_tags = []
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.publish_http_last_state, constants.STATE_NOT_STARTED)
        self.assertEqual(self.renderer.publish_https_last_state, constants.STATE_NOT_STARTED)


    def test_publish_http_https_skipped(self):
        # Setup
        self.publish_report.publish_http = constants.STATE_SKIPPED
        self.publish_report.publish_https = constants.STATE_SKIPPED

        # Test
        self.renderer._display_publish_http_https_step(self.publish_report)

        # Verify
        expected_tags = ['http-skipped', 'https-skipped']
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.publish_http_last_state, constants.STATE_SKIPPED)
        self.assertEqual(self.renderer.publish_https_last_state, constants.STATE_SKIPPED)

    def test_publish_http_https_unknown(self):
        # Setup
        self.publish_report.publish_http = 'unknown'
        self.publish_report.publish_https = 'unknown'

        # Test
        self.renderer._display_publish_http_https_step(self.publish_report)

        # Verify
        expected_tags = ['http-unknown', 'https-unknown']
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
        self.assertEqual(self.renderer.publish_http_last_state, 'unknown')
        self.assertEqual(self.renderer.publish_https_last_state, 'unknown')

    def test_render_module_errors(self):
        # Setup

        # Need a valid traceback instance to be formatted and this is the best
        # I could come up with to make one :)
        tb = None
        try:
            raise Exception()
        except Exception:
            tb = sys.exc_info()[2]
        tb = traceback.extract_tb(tb)

        individual_errors = {}
        for i in range(0, 10):
            individual_errors['mod_%s' % i] = {
                'exception' : 'e_%s' % i,
                'traceback' : tb,
            }

        # Test
        self.renderer._render_module_errors(individual_errors)

        # Verify
        expected_tags = [TAG_FAILURE]
        self.assertEqual(expected_tags, self.prompt.get_write_tags())

    def test_display_report(self):
        # Test
        self.renderer.display_report(FULL_REPORT)

        # Verify
        expected_tags = ['download-metadata', 'progress_bar',
                         'downloading', 'progress_bar',
                         'publishing', 'progress_bar',
                         'generating', 'spinner',
                         'completed',
                         'http-completed', 'https-completed']

        tags = self.prompt.get_write_tags()
        self.assertEqual(expected_tags, tags)
