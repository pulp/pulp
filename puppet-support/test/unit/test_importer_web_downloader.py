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

import base_downloader

from pulp_puppet.common import constants, model
from pulp_puppet.importer.downloaders import exceptions, web
from pulp_puppet.importer.downloaders.web import HttpDownloader

TEST_SOURCE = 'http://forge.puppetlabs.com/'

class HttpDownloaderTests(base_downloader.BaseDownloaderTests):

    def setUp(self):
        super(HttpDownloaderTests, self).setUp()
        self.config.repo_plugin_config[constants.CONFIG_FEED] = TEST_SOURCE
        self.downloader = HttpDownloader(self.repo, None, self.config, self.mock_cancelled_callback)

    @mock.patch('pycurl.Curl')
    def test_retrieve_metadata(self, mock_curl_constructor):
        # Setup
        mock_curl = mock.MagicMock()
        mock_curl.getinfo.return_value = 200 # simulate a successful download
        mock_curl_constructor.return_value = mock_curl

        # Test
        docs = self.downloader.retrieve_metadata(self.mock_progress_report)

        # Verify
        self.assertEqual(1, len(docs))

        # Progress indicators
        self.assertEqual(self.mock_progress_report.metadata_query_finished_count, 1)
        self.assertEqual(self.mock_progress_report.metadata_query_total_count, 1)
        self.assertEqual(2, self.mock_progress_report.update_progress.call_count)

    @mock.patch('pycurl.Curl')
    def test_retrieve_metadata_multiple_queries(self, mock_curl_constructor):
        # Setup
        mock_curl = mock.MagicMock()
        mock_curl.getinfo.return_value = 200 # simulate a successful download
        mock_curl_constructor.return_value = mock_curl

        self.config.repo_plugin_config[constants.CONFIG_QUERIES] = ['a', ['b', 'c']]

        # Test
        docs = self.downloader.retrieve_metadata(self.mock_progress_report)

        # Verify
        self.assertEqual(2, len(docs))

        # Progress indicators
        self.assertEqual(self.mock_progress_report.metadata_query_finished_count, 2)
        self.assertEqual(self.mock_progress_report.metadata_query_total_count, 2)
        self.assertEqual(3, self.mock_progress_report.update_progress.call_count)

    @mock.patch('pycurl.Curl')
    def test_retrieve_metadata_with_error(self, mock_curl_constructor):
        # Setup
        mock_curl = mock.MagicMock()
        mock_curl.getinfo.return_value = 404 # simulate an error
        mock_curl_constructor.return_value = mock_curl

        # Test
        try:
            self.downloader.retrieve_metadata(self.mock_progress_report)
            self.fail()
        except exceptions.FileNotFoundException, e:
            expected = TEST_SOURCE + constants.REPO_METADATA_FILENAME
            self.assertEqual(expected, e.location)

    @mock.patch('pycurl.Curl')
    def test_retrieve_module(self, mock_curl_constructor):
        # Setup
        mock_curl = mock.MagicMock()
        mock_curl.getinfo.return_value = 200 # simulate a successful download
        mock_curl_constructor.return_value = mock_curl

        # Test
        stored_filename = self.downloader.retrieve_module(self.mock_progress_report, self.module)

        # Verify
        self.assertTrue(os.path.exists(stored_filename))

    @mock.patch('pycurl.Curl')
    def test_retrieve_module_missing_module(self, mock_curl_constructor):
        # Setup
        mock_curl = mock.MagicMock()
        mock_curl.getinfo.return_value = 404 # simulate a not found
        mock_curl_constructor.return_value = mock_curl

        # Test
        try:
            self.downloader.retrieve_module(self.mock_progress_report, self.module)
            self.fail()
        except exceptions.FileNotFoundException, e:
            self.assertTrue(self.module.filename() in e.location)
            expected_filename = web._create_download_tmp_dir(self.working_dir)
            expected_filename = os.path.join(expected_filename, self.module.filename())
            self.assertTrue(not os.path.exists(os.path.join(expected_filename)))

    @mock.patch('pycurl.Curl')
    def test_cleanup_module(self, mock_curl_constructor):
        # Setup
        mock_curl = mock.MagicMock()
        mock_curl.getinfo.return_value = 200 # simulate a successful download
        mock_curl_constructor.return_value = mock_curl

        stored_filename = self.downloader.retrieve_module(self.mock_progress_report, self.module)

        # Test
        self.downloader.cleanup_module(self.module)

        # Verify
        self.assertTrue(not os.path.exists(stored_filename))


    def test_create_metadata_download_urls(self):
        # Setup
        self.config.repo_plugin_config[constants.CONFIG_QUERIES] = ['a', ['b', 'c']]

        # Test
        urls = self.downloader._create_metadata_download_urls()

        # Verify
        self.assertEqual(2, len(urls))
        self.assertEqual(urls[0], TEST_SOURCE + 'modules.json?q=a')
        self.assertEqual(urls[1], TEST_SOURCE + 'modules.json?q=b&q=c')

    def test_create_metadata_download_urls_no_queries(self):
        # Test
        urls = self.downloader._create_metadata_download_urls()

        # Verify
        self.assertEqual(1, len(urls))
        self.assertEqual(urls[0], TEST_SOURCE + 'modules.json')

    def test_create_module_url(self):
        # Test

        # Strip the trailing / off to make sure that branch is followed
        self.config.repo_plugin_config[constants.CONFIG_FEED] = TEST_SOURCE[:-1]
        url = self.downloader._create_module_url(self.module)

        # Verify
        expected = TEST_SOURCE + \
                   constants.HOSTED_MODULE_FILE_RELATIVE_PATH % (self.module.author[0], self.module.author) + \
                   self.module.filename()
        self.assertEqual(url, expected)

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

    def test_create_download_tmp_dir(self):
        # Test
        created = web._create_download_tmp_dir(self.working_dir)

        # Verify
        self.assertTrue(os.path.exists(created))
        self.assertEqual(created, os.path.join(self.working_dir, web.DOWNLOAD_TMP_DIR))

class InMemoryDownloadedContentTests(unittest.TestCase):

    def test_update(self):
        # Setup
        data = ['abc', 'de', 'fgh']

        # Test
        content = web.InMemoryDownloadedContent()
        for d in data:
            content.update(d)

        # Verify
        self.assertEqual(content.content, ''.join(data))

class StoredDownloadedContentTests(unittest.TestCase):

    def test_update(self):
        # Setup
        tmp_dir = tempfile.mkdtemp(prefix='stored-downloaded-content')
        filename = os.path.join(tmp_dir, 'storage-test.txt')
        data = ['abc', 'de', 'fgh']

        # Test - Store
        content = web.StoredDownloadedContent(filename)
        content.open()
        for d in data:
            content.update(d)
        content.close()

        # Verify
        self.assertTrue(os.path.exists(filename))
        f = open(filename, 'r')
        stored = f.read()
        f.close()
        self.assertEqual(stored, ''.join(data))

        # Test - Delete
        content.delete()

        # Verify
        self.assertTrue(not os.path.exists(filename))

        # Clean Up
        shutil.rmtree(tmp_dir)

def curl_opts_by_key(call_args_list):
    opts_by_key = dict([(c[0][0], c[0][1]) for c in call_args_list])
    return opts_by_key