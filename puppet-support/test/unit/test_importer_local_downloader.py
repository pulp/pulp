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


import os

import base_downloader

from pulp_puppet.common import constants, model
from pulp_puppet.importer.downloaders.exceptions import FileNotFoundException
from pulp_puppet.importer.downloaders.local import LocalDownloader

VALID_REPO_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data', 'repos', 'valid')
INVALID_REPO_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data', 'repos', 'invalid')

class LocalDownloaderTests(base_downloader.BaseDownloaderTests):

    def setUp(self):
        super(LocalDownloaderTests, self).setUp()
        self.config.repo_plugin_config[constants.CONFIG_FEED] = 'file://' + VALID_REPO_DIR
        self.downloader = LocalDownloader(self.repo, None, self.config, self.mock_cancelled_callback)

    def test_retrieve_metadata(self):
        # Test
        docs = self.downloader.retrieve_metadata(self.mock_progress_report)

        # Verify
        self.assertEqual(1, len(docs))
        metadata = model.RepositoryMetadata()
        metadata.update_from_json(docs[0])
        self.assertEqual(2, len(metadata.modules))

        self.assertEqual(1, self.mock_progress_report.metadata_query_total_count)
        self.assertEqual(1, self.mock_progress_report.metadata_query_finished_count)
        expected_query = os.path.join(VALID_REPO_DIR, constants.REPO_METADATA_FILENAME)
        self.assertEqual(expected_query, self.mock_progress_report.metadata_current_query)
        self.assertEqual(2, self.mock_progress_report.update_progress.call_count)

    def test_retrieve_metadata_no_metadata_found(self):
        # Setup
        self.config.repo_plugin_config[constants.CONFIG_FEED] = 'file://' + INVALID_REPO_DIR

        # Test
        try:
            self.downloader.retrieve_metadata(self.mock_progress_report)
            self.fail()
        except FileNotFoundException, e:
            expected = os.path.join(INVALID_REPO_DIR, constants.REPO_METADATA_FILENAME)
            self.assertEqual(expected, e.location)

    def test_retrieve_module(self):
        # Test
        mod_path = self.downloader.retrieve_module(self.mock_progress_report, self.module)

        # Verify
        expected = os.path.join(VALID_REPO_DIR, self.module.filename())
        self.assertEqual(expected, mod_path)

    def test_retrieve_module_no_file(self):
        # Setup
        self.module.author = 'foo'

        # Test
        try:
            self.downloader.retrieve_module(self.mock_progress_report, self.module)
            self.fail()
        except FileNotFoundException, e:
            expected = os.path.join(VALID_REPO_DIR, self.module.filename())
            self.assertEqual(expected, e.location)

    def test_cleanup_module(self):
        # Test
        self.downloader.cleanup_module(self.module)

        # This test makes sure the default NotImplementedError is not raised