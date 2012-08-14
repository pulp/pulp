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
from pulp.plugins.model import Repository

from pulp_puppet.common import constants, model
from pulp_puppet.importer.downloaders.web import HttpDownloader

TEST_SOURCE = 'http://forge.puppetlabs.com/'

class LiveHttpDownloaderTests(unittest.TestCase):

    def setUp(self):
        self.working_dir = tempfile.mkdtemp(prefix='http-downloader-tests')
        self.repo = Repository('test-repo', working_dir=self.working_dir)

        repo_config = {
            constants.CONFIG_FEED : TEST_SOURCE,
        }
        self.config = PluginCallConfiguration({}, repo_config)

        self.mock_cancelled_callback = mock.MagicMock().is_cancelled
        self.mock_cancelled_callback.return_value = False

        self.downloader = HttpDownloader(self.repo, None, self.config, self.mock_cancelled_callback)

        self.mock_progress_report = mock.MagicMock()

    def tearDown(self):
        if os.path.exists(self.working_dir):
            shutil.rmtree(self.working_dir)

    def test_retrieve_metadata(self):
        docs = self._run_test()
        self.assertEqual(1, len(docs))

    def test_retrieve_metadata_with_vague_query(self):
        self.config.repo_plugin_config[constants.CONFIG_QUERIES] = ['httpd']
        docs = self._run_test()
        self.assertEqual(1, len(docs))

    def test_retrieve_metadata_with_specific_query(self):
        self.config.repo_plugin_config[constants.CONFIG_QUERIES] = ['thias/php']
        docs = self._run_test()
        self.assertEqual(1, len(docs))

    def test_retrieve_metadata_with_multiple_specific_queries(self):
        self.config.repo_plugin_config[constants.CONFIG_QUERIES] = ['thias/php', 'larstobi/dns']
        docs = self._run_test()
        self.assertEqual(2, len(docs))

    def _run_test(self):
        # Test
        docs = self.downloader.retrieve_metadata(self.mock_progress_report)

        # Verify
        parsed = model.RepositoryMetadata()
        for d in docs:
            parsed.update_from_json(d)

        print('Number of Modules: %s' % len(parsed.modules))

        return docs