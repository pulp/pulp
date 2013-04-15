# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import os
import re
import shutil
import tempfile
import unittest
from cStringIO import StringIO
from urlparse import urljoin

import mock
import pycurl

from pulp.common.download.config import DownloaderConfig
from pulp.common.download.downloaders import curl as curl_downloader
from pulp.common.download.listener import AggregatingEventListener
from pulp.common.download.request import DownloadRequest

from http_static_test_server import HTTPStaticTestServer

# mock and test data methods and classes ---------------------------------------

class MockEventListener(mock.Mock):

    def __init__(self):
        super(MockEventListener, self).__init__()

        self.download_started = mock.Mock()
        self.download_progress = mock.Mock()
        self.download_succeeded = mock.Mock()
        self.download_failed = mock.Mock()


def mock_curl_multi_factory():

    mock_curl_multi = mock.Mock()
    mock_curl_multi._curls = []
    mock_curl_multi._opts = {}

    def _add_handle(curl):
        curl._is_active = True
        mock_curl_multi._curls.append(curl)

    def _info_read():
        return 0, [c for c in mock_curl_multi._curls if c._is_active], []

    def _perform():
        for curl in mock_curl_multi._curls:
            curl.perform()
        return 0, len(mock_curl_multi._curls)

    def _remove_handle(curl):
        curl._is_active = False
        mock_curl_multi._curls.remove(curl)

    def _setopt(opt, setting):
        mock_curl_multi._opts[opt] = setting

    mock_curl_multi.add_handle = mock.Mock(wraps=_add_handle)
    mock_curl_multi.close = mock.Mock()
    mock_curl_multi.info_read = mock.Mock(wraps=_info_read)
    mock_curl_multi.perform = mock.Mock(wraps=_perform)
    mock_curl_multi.remove_handle = mock.Mock(wraps=_remove_handle)
    mock_curl_multi.select = mock.Mock()
    mock_curl_multi.setopt = mock.Mock(wraps=_setopt)

    return mock_curl_multi


def mock_curl_easy_factory():

    mock_curl = mock.Mock()
    mock_curl._is_active = False
    mock_curl._opts = {}

    def _getinfo(info_code):
        # Let's always return HTTP 200
        return 200

    def _perform():
        # strip off the protocol scheme + hostname + port and use the remaining *relative* path
        input_file_path = re.sub(r'^[a-z]+://localhost:8088/', '', mock_curl._opts[pycurl.URL], 1)
        input_fp = open(input_file_path, 'rb')

        output_write_function = mock_curl._opts[pycurl.WRITEFUNCTION]

        progress_callback = mock_curl._opts[pycurl.PROGRESSFUNCTION]
        progress_callback(0, 0, 0, 0)

        output_write_function(input_fp.read())

        file_size = os.fstat(input_fp.fileno())[6]
        progress_callback(file_size, file_size, 0, 0)

        input_fp.close()

    def _setopt(opt, setting):
        mock_curl._opts[opt] = setting

    mock_curl.getinfo = mock.Mock(wraps=_getinfo)
    mock_curl.perform = mock.Mock(wraps=_perform)
    mock_curl.setopt = mock.Mock(wraps=_setopt)

    return mock_curl


class MockObjFactory(object):

    def __init__(self, mock_obj_factory):
        self.mock_obj_factory = mock_obj_factory
        self.mock_objs = []

    def __call__(self):
        mock_instance = self.mock_obj_factory()
        self.mock_objs.append(mock_instance)
        return mock_instance


def determine_relative_data_dir():
    possible_data_dir = 'platform/test/unit/server/data/test_common_download/'
    while possible_data_dir:
        if os.path.exists(possible_data_dir):
            return possible_data_dir
        possible_data_dir = possible_data_dir.split('/', 1)[1]
    raise RuntimeError('Cannot determine relative data path')

# test suite -------------------------------------------------------------------

class DownloadRequestTests(unittest.TestCase):
    def test__init__(self):
        url = 'http://www.theonion.com/articles/world-surrenders-to-north-korea,31265/'
        path = '/fake/path'
        request = DownloadRequest(url, path)
        self.assertEqual(request.url, url)
        self.assertEqual(request.destination, path)


class DownloadTests(unittest.TestCase):
    data_dir = determine_relative_data_dir()
    file_list = ['100K_file', '500K_file', '1M_file']
    file_sizes = [102400, 512000, 1048576]

    def setUp(self):
        self.storage_dir = tempfile.mkdtemp(prefix='test_common_download-')

    def tearDown(self):
        shutil.rmtree(self.storage_dir)
        self.storage_dir = None

    def _download_requests(self, protocol='http'):
        # localhost:8088 is here for the live tests
        return [DownloadRequest(protocol + '://localhost:8088/' + self.data_dir + f, os.path.join(self.storage_dir, f))
                for f in self.file_list]

    def _file_download_requests(self):
        return [DownloadRequest('file://' + os.path.join(os.getcwd(), self.data_dir, f),
                os.path.join(self.storage_dir, f)) for f in self.file_list]

# curl downloader tests --------------------------------------------------------

class CurlInstantiationTests(unittest.TestCase):

    def test_http_downloader(self):
        config = DownloaderConfig()
        try:
            curl_downloader.HTTPSCurlDownloader(config)
        except Exception, e:
            self.fail(str(e))

    def test_https_downloader(self):
        config = DownloaderConfig()
        try:
            downloader = curl_downloader.HTTPSCurlDownloader(config)
        except Exception, e:
            self.fail(str(e))

        ssl_working_dir = downloader.ssl_working_dir
        self.assertTrue(os.path.exists(ssl_working_dir))

        del downloader
        self.assertFalse(os.path.exists(ssl_working_dir))


class MockCurlDownloadTests(DownloadTests):
    # test suite that really tests the download framework built on top of pycurl

    @mock.patch('pycurl.CurlMulti', MockObjFactory(mock_curl_multi_factory))
    @mock.patch('pycurl.Curl', MockObjFactory(mock_curl_easy_factory))
    def test_download_single_file(self):
        config = DownloaderConfig()
        downloader = curl_downloader.HTTPSCurlDownloader(config)
        request_list = self._download_requests()[:1]
        downloader.download(request_list)

        self.assertEqual(len(pycurl.CurlMulti.mock_objs), 1)
        self.assertEqual(len(pycurl.Curl.mock_objs), curl_downloader.DEFAULT_MAX_CONCURRENT)

        mock_multi_curl = pycurl.CurlMulti.mock_objs[0]

        self.assertEqual(mock_multi_curl.setopt.call_count, 2) # dangerous as this could easily change
        self.assertEqual(mock_multi_curl.add_handle.call_count, 1)
        self.assertEqual(mock_multi_curl.select.call_count, 1)
        self.assertEqual(mock_multi_curl.perform.call_count, 1)
        self.assertEqual(mock_multi_curl.info_read.call_count, 1)
        self.assertEqual(mock_multi_curl.remove_handle.call_count, 1)

        mock_curl = pycurl.Curl.mock_objs[-1] # curl objects are used from back of the list

        self.assertEqual(mock_curl.setopt.call_count, 11) # also dangerous for the same reasons
        self.assertEqual(mock_curl.perform.call_count, 1)

    @mock.patch('pycurl.CurlMulti', MockObjFactory(mock_curl_multi_factory))
    @mock.patch('pycurl.Curl', MockObjFactory(mock_curl_easy_factory))
    def test_download_multi_file(self):
        config = DownloaderConfig()
        downloader = curl_downloader.HTTPSCurlDownloader(config)
        request_list = self._download_requests()
        downloader.download(request_list)

        # this is really just testing my mock curl objects, but it's nice to know
        for file_name, file_size in zip(self.file_list, self.file_sizes):
            input_file = os.path.join(self.data_dir, file_name)
            input_file_size = os.stat(input_file)[6]

            output_file = os.path.join(self.storage_dir, file_name)
            output_file_size = os.stat(output_file)[6]

            self.assertEqual(input_file_size, file_size)
            self.assertEqual(output_file_size, file_size) # does check that close() was called properly

        mock_curl_multi = pycurl.CurlMulti.mock_objs[0]
        self.assertEqual(mock_curl_multi.perform.call_count, 1)

        num_unused_curl_objs = max(0, curl_downloader.DEFAULT_MAX_CONCURRENT - len(self.file_list))
        unused_mock_curl_objs = pycurl.Curl.mock_objs[:num_unused_curl_objs]

        for mock_curl in unused_mock_curl_objs:
            self.assertEqual(mock_curl.perform.call_count, 0)

        used_mock_curl_objs = pycurl.Curl.mock_objs[num_unused_curl_objs:]

        for mock_curl in used_mock_curl_objs:
            self.assertEqual(mock_curl.perform.call_count, 1)

    @mock.patch('pycurl.CurlMulti', MockObjFactory(mock_curl_multi_factory))
    @mock.patch('pycurl.Curl', MockObjFactory(mock_curl_easy_factory))
    def test_download_event_listener(self):
        config = DownloaderConfig()
        listener = MockEventListener()
        downloader = curl_downloader.HTTPSCurlDownloader(config, listener)
        request_list = self._download_requests()[:1]
        downloader.download(request_list)

        self.assertEqual(listener.download_started.call_count, 1)
        self.assertEqual(listener.download_progress.call_count, 2) # this one only tests the mock curl
        self.assertEqual(listener.download_succeeded.call_count, 1)
        self.assertEqual(listener.download_failed.call_count, 0)

    @mock.patch('pycurl.CurlMulti', MockObjFactory(mock_curl_multi_factory))
    @mock.patch('pycurl.Curl', MockObjFactory(mock_curl_easy_factory))
    def test_download_aggregating_event_listener(self):
        config = DownloaderConfig()
        listener = AggregatingEventListener()
        downloader = curl_downloader.HTTPCurlDownloader(config, listener)
        request_list = self._download_requests()
        downloader.download(request_list)

        self.assertEqual(len(listener.succeeded_reports), 3)
        self.assertEqual(len(listener.failed_reports), 0)
        self.assertEqual(len(list(listener.all_reports)), 3)

    @mock.patch('pycurl.CurlMulti', MockObjFactory(mock_curl_multi_factory))
    @mock.patch('pycurl.Curl', MockObjFactory(mock_curl_easy_factory))
    def test_https_download(self):
        config = DownloaderConfig()
        downloader = curl_downloader.HTTPSCurlDownloader(config)

        for attr in ('ssl_working_dir', 'ssl_ca_cert', 'ssl_client_cert', 'ssl_client_key'):
            self.assertTrue(hasattr(downloader, attr))

        request_list = self._download_requests('https')[:1]
        downloader.download(request_list)

        mock_curl = pycurl.Curl.mock_objs[-1] # curl objects are used from the end

        self.assertEqual(mock_curl.setopt.call_count, 11) # dangerous as this could easily change


class LiveCurlDownloadTests(DownloadTests):
    # test suite that tests that pycurl is being used (mostly) correctly

    http_server = None

    @classmethod
    def setUpClass(cls):
        cls.http_server = HTTPStaticTestServer()
        cls.http_server.start()

    @classmethod
    def tearDownClass(cls):
        cls.http_server.stop()
        cls.http_server = None

    def test_download_destination_file_like_object(self):
        """
        We want to assert that we can download URLs to file-like objects, and not just to
        filesystem paths.
        """
        config = DownloaderConfig()
        downloader = curl_downloader.HTTPSCurlDownloader(config)
        destination_file = StringIO()
        request_list = [
            DownloadRequest(urljoin('http://localhost:8088/',
                                    self.data_dir + '/' + self.file_list[0]),
                            destination_file)]

        downloader.download(request_list)

        with open(os.path.join(self.data_dir, self.file_list[0])) as expected_data_file:
            expected_data = expected_data_file.read()

        destination_file.seek(0)
        destination_file_data = destination_file.read()
        # The destination_file should be safe to close now (This actually does test that the
        # downloader hasn't already closed the file, because closing a file twice is an error.)
        destination_file.close()
        self.assertEqual(len(destination_file_data), len(expected_data))
        self.assertEqual(destination_file_data, expected_data)

    def test_download_single(self):
        config = DownloaderConfig()
        downloader = curl_downloader.HTTPSCurlDownloader(config)
        request_list = self._download_requests()[:1]
        downloader.download(request_list)

        input_file_name = self.file_list[0]
        input_file_size = self.file_sizes[0]

        output_file_path = os.path.join(self.storage_dir, input_file_name)
        output_file_size = os.stat(output_file_path)[6]

        self.assertEqual(input_file_size, output_file_size)

    def test_download_multiple(self):
        config = DownloaderConfig()
        downloader = curl_downloader.HTTPSCurlDownloader(config)
        request_list = self._download_requests()

        try:
            downloader.download(request_list)

        except Exception, e:
            self.fail(str(e))

    def test_download_event_listener(self):
        config = DownloaderConfig()
        listener = MockEventListener()
        downloader = curl_downloader.HTTPSCurlDownloader(config, listener)
        request_list = self._download_requests()[:1]
        downloader.download(request_list)

        self.assertEqual(listener.download_started.call_count, 1)
        self.assertNotEqual(listener.download_progress.call_count, 0) # not sure how many times
        self.assertEqual(listener.download_succeeded.call_count, 1)
        self.assertEqual(listener.download_failed.call_count, 0)


class TestHTTPCurlDownloadBackend(unittest.TestCase):
    def test__clear_easy_handle_download_filelike_destination(self):
        # If we give a file-like object as a destination to the request on the easy_handle, this
        # method should not close the filepointer on the handle
        easy_handle = mock.MagicMock()
        easy_handle.request = mock.MagicMock()
        easy_handle.request.destination = StringIO()

        filepointer = easy_handle.fp = mock.MagicMock()

        http_download_backend = curl_downloader.HTTPCurlDownloader(mock.MagicMock())
        http_download_backend._clear_easy_handle_download(easy_handle)

        # close() should not have been called on the fp
        self.assertEqual(filepointer.close.called, False)
        self.assertEqual(easy_handle.fp, None)
        self.assertEqual(easy_handle.request, None)
        self.assertEqual(easy_handle.report, None)

    def test__clear_easy_handle_download_string_destination(self):
        # If we give a string as a destination to the request on the easy_handle, this method
        # should try to close the filepointer on the handle
        easy_handle = mock.MagicMock()
        easy_handle.request = mock.MagicMock()
        easy_handle.request.destination = '/fake/path/should/get/closed'

        filepointer = easy_handle.fp = mock.MagicMock()

        http_download_backend = curl_downloader.HTTPCurlDownloader(mock.MagicMock())
        http_download_backend._clear_easy_handle_download(easy_handle)

        # close() should have been called on the fp
        filepointer.close.assert_called_once_with()
        self.assertEqual(easy_handle.fp, None)
        self.assertEqual(easy_handle.request, None)
        self.assertEqual(easy_handle.report, None)
