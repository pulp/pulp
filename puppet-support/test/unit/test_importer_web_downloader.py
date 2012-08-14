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
import pycurl
import shutil
import tempfile
import unittest

from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository

from pulp_puppet.common import constants
from pulp_puppet.importer.downloaders import exceptions
from pulp_puppet.importer.downloaders.web import HttpDownloader

TEST_SOURCE = 'http://forge.puppetlabs.com/'

class HttpDownloaderTests(unittest.TestCase):

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

    def test_create_metadata_download_urls(self):

        # See note in _create_metadata_download_urls about its behavior; at the
        # time of writing it intentionally only returned 1 URL.

        # Setup
        self.config.repo_plugin_config[constants.CONFIG_QUERIES] = ['a', ['b', 'c']]

        # Test
        urls = self.downloader._create_metadata_download_urls()

        # Verify
        self.assertEqual(1, len(urls))
        expected = TEST_SOURCE + 'modules.json?q=a&q=b&q=c'
        self.assertEqual(urls[0], expected)

    def test_create_metadata_download_urls_no_queries(self):
        # Test
        urls = self.downloader._create_metadata_download_urls()

        # Verify
        self.assertEqual(1, len(urls))
        self.assertEqual(urls[0], TEST_SOURCE + 'modules.json')

    @mock.patch('pulp_puppet.importer.downloaders.web.HttpDownloader._create_and_configure_curl')
    def test_download_file(self, mock_curl_create):
        # Setup
        mock_curl = mock.MagicMock()
        mock_curl.getinfo.return_value = 200
        mock_curl_create.return_value = mock_curl

        url = 'http://localhost/module.tar.gz'
        destination = mock.MagicMock()

        # Test
        self.downloader._download_file(url, destination)

        # Verify
        opts_by_key = curl_opts_by_key(mock_curl.setopt.call_args_list)
        self.assertEqual(opts_by_key[pycurl.URL], url)
        self.assertEqual(opts_by_key[pycurl.WRITEFUNCTION], destination.update)

        self.assertEqual(1, mock_curl.perform.call_count)
        self.assertEqual(1, mock_curl.getinfo.call_count)
        self.assertEqual(1, mock_curl.close.call_count)

    @mock.patch('pulp_puppet.importer.downloaders.web.HttpDownloader._create_and_configure_curl')
    def test_download_file_unauthorized(self, mock_curl_create):
        # Setup
        mock_curl = mock.MagicMock()
        mock_curl.getinfo.return_value = 401
        mock_curl_create.return_value = mock_curl

        url = 'http://localhost/module.tar.gz'
        destination = mock.MagicMock()

        # Test
        try:
            self.downloader._download_file(url, destination)
            self.fail()
        except exceptions.UnauthorizedException, e:
            self.assertEqual(e.location, url)

    @mock.patch('pulp_puppet.importer.downloaders.web.HttpDownloader._create_and_configure_curl')
    def test_download_file_not_found(self, mock_curl_create):
        # Setup
        mock_curl = mock.MagicMock()
        mock_curl.getinfo.return_value = 404
        mock_curl_create.return_value = mock_curl

        url = 'http://localhost/module.tar.gz'
        destination = mock.MagicMock()

        # Test
        try:
            self.downloader._download_file(url, destination)
            self.fail()
        except exceptions.FileNotFoundException, e:
            self.assertEqual(e.location, url)

    @mock.patch('pulp_puppet.importer.downloaders.web.HttpDownloader._create_and_configure_curl')
    def test_download_file_unhandled_error(self, mock_curl_create):
        # Setup
        mock_curl = mock.MagicMock()
        mock_curl.getinfo.return_value = 500
        mock_curl_create.return_value = mock_curl

        url = 'http://localhost/module.tar.gz'
        destination = mock.MagicMock()

        # Test
        try:
            self.downloader._download_file(url, destination)
            self.fail()
        except exceptions.FileRetrievalException, e:
            self.assertEqual(e.location, url)

    @mock.patch('pycurl.Curl')
    def test_create_and_configure_curl(self, mock_constructor):

        # PyCurl doesn't give visibility into what options are set, so mock out
        # the constructor so we can check what's being set on the curl instance

        # Test
        mock_constructor.return_value = mock.MagicMock()
        curl = self.downloader._create_and_configure_curl()

        # Verify
        opts_by_key = curl_opts_by_key(curl.setopt.call_args_list)

        self.assertEqual(opts_by_key[pycurl.VERBOSE], 0)
        self.assertEqual(opts_by_key[pycurl.LOW_SPEED_LIMIT], 1000)
        self.assertEqual(opts_by_key[pycurl.LOW_SPEED_TIME], 5 * 60)

def curl_opts_by_key(call_args_list):
    opts_by_key = dict([(c[0][0], c[0][1]) for c in call_args_list])
    return opts_by_key