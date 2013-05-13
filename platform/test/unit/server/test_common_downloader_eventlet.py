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

import httplib
import os
import unittest
import urllib2
from cStringIO import StringIO

import mock

from pulp.common.download.config import DownloaderConfig
from pulp.common.download.downloaders import event as eventlet_downloader
from pulp.common.download.downloaders import urllib2_utils

from http_static_test_server import HTTPStaticTestServer
from test_common_download import DownloadTests, MockEventListener

# evenetlet downloader tests ---------------------------------------------------

class EventletDownloaderInstantiationTests(unittest.TestCase):

    def test_instantiation(self):
        config =  DownloaderConfig()
        try:
            eventlet_downloader.HTTPEventletDownloader(config)
        except Exception, e:
            self.fail(str(e))


class LiveEventletDownloaderTests(DownloadTests):

    http_server = None

    @classmethod
    def setUpClass(cls):
        cls.http_server = HTTPStaticTestServer()
        cls.http_server.start()

    @classmethod
    def tearDownClass(cls):
        cls.http_server.stop()
        cls.http_server = None

    def test_download_single(self):
        config = DownloaderConfig()
        downloader = eventlet_downloader.HTTPEventletDownloader(config)
        request_list = self._download_requests()[:1]
        downloader.download(request_list)

        input_file_name = self.file_list[0]
        input_file_size = self.file_sizes[0]

        output_file_path = os.path.join(self.storage_dir, input_file_name)
        output_file_size = os.path.getsize(output_file_path)

        self.assertEqual(input_file_size, output_file_size)

    def test_download_multiple(self):
        downloader = eventlet_downloader.HTTPEventletDownloader(DownloaderConfig())
        request_list = self._download_requests()

        try:
            downloader.download(request_list)

        except Exception, e:
            self.fail(str(e))

    def test_file_like_destination(self):
        downloader = eventlet_downloader.HTTPEventletDownloader(DownloaderConfig())
        request_list = self._download_requests()[:1]
        request_list[0].destination = StringIO()
        downloader.download(request_list)

        contents = request_list[0].destination.getvalue()

        self.assertEqual(len(contents), self.file_sizes[0])

        try:
            request_list[0].destination.close()
        except Exception, e:
            self.fail(str(e))

    def test_download_event_listener(self):
        listener = MockEventListener()
        downloader = eventlet_downloader.HTTPEventletDownloader(DownloaderConfig(), listener)
        request_list = self._download_requests()[:1]
        downloader.download(request_list)

        self.assertEqual(listener.download_started.call_count, 1)
        self.assertNotEqual(listener.download_progress.call_count, 0) # not sure how many times
        self.assertEqual(listener.download_succeeded.call_count, 1)
        self.assertEqual(listener.download_failed.call_count, 0)


class EventletConnectionTests(unittest.TestCase):

    def test_instantiation(self):
        host = 'myserver.com'

        try:
            urllib2_utils.HTTPDownloaderConnection(urllib2_utils.HTTP_SCHEME, host)
        except:
            self.fail('instantiation with %s scheme and %s host failed' % (urllib2_utils.HTTP_SCHEME, host))

        try:
            urllib2_utils.HTTPDownloaderConnection(urllib2_utils.HTTPS_SCHEME, host)
        except:
            self.fail('instantiation with %s scheme and %s host failed' % (urllib2_utils.HTTPS_SCHEME, host))

    def test_properties(self):
        kwargs = {'scheme': 'http',
                  'host': 'myhost.com',
                  'proxy_scheme': 'http',
                  'proxy_host': 'myproxy.com',
                  'proxy_port': 3456}

        connection = urllib2_utils.HTTPDownloaderConnection(**kwargs)

        self.assertEqual(connection.url, 'http://myhost.com')
        self.assertEqual(connection.host, 'myhost.com')
        self.assertEqual(connection.server, 'myhost.com')
        self.assertEqual(connection.port, 80)
        self.assertEqual(connection.proxy_url, 'http://myproxy.com:3456')
        self.assertEqual(connection.proxy_host, 'myproxy.com:3456')
        self.assertEqual(connection.proxy_server, 'myproxy.com')
        self.assertEqual(connection.proxy_port, 3456)
        self.assertEqual(connection.proxy_credentials, None)


MOCK_RESPONSE = mock.MagicMock()
MOCK_RESPONSE.code = 200
MOCK_RESPONSE.msg = 'OK'

class EventletHandlerTests(unittest.TestCase):

    def test_instantiation(self):
        try:
            urllib2_utils.HTTPDownloaderHandler()
        except:
            self.fail('instantiation failed')

    @mock.patch('pulp.common.download.downloaders.urllib2_utils.HTTPDownloaderHandler.proxy_open', return_value=None)
    @mock.patch('pulp.common.download.downloaders.urllib2_utils.HTTPDownloaderHandler.https_open', return_value=None)
    @mock.patch('pulp.common.download.downloaders.urllib2_utils.HTTPDownloaderHandler.http_open', return_value=MOCK_RESPONSE)
    @mock.patch('pulp.common.download.downloaders.urllib2_utils.HTTPDownloaderHandler.default_open', return_value=None)
    def test_http_open(self, mock_default_open, mock_http_open, mock_https_open, mock_proxy_open):
        url = 'http://myserver.com/path/to/resource'
        req = urllib2.Request(url)
        opener = urllib2.build_opener(urllib2_utils.HTTPDownloaderHandler())

        response = opener.open(req)

        self.assertTrue(response is MOCK_RESPONSE)
        self.assertEqual(mock_default_open.call_count, 1)
        self.assertEqual(mock_http_open.call_count, 1)
        self.assertEqual(mock_https_open.call_count, 0)
        self.assertEqual(mock_proxy_open.call_count, 0)

    @mock.patch('pulp.common.download.downloaders.urllib2_utils.HTTPDownloaderHandler.proxy_open', return_value=None)
    @mock.patch('pulp.common.download.downloaders.urllib2_utils.HTTPDownloaderHandler.https_open', return_value=MOCK_RESPONSE)
    @mock.patch('pulp.common.download.downloaders.urllib2_utils.HTTPDownloaderHandler.http_open', return_value=None)
    @mock.patch('pulp.common.download.downloaders.urllib2_utils.HTTPDownloaderHandler.default_open', return_value=None)
    def test_http_open(self, mock_default_open, mock_http_open, mock_https_open, mock_proxy_open):
        url = 'https://myserver.com/path/to/resource'
        req = urllib2.Request(url)
        opener = urllib2.build_opener(urllib2_utils.HTTPDownloaderHandler())

        response = opener.open(req)

        self.assertTrue(response is MOCK_RESPONSE)
        self.assertEqual(mock_default_open.call_count, 1)
        self.assertEqual(mock_http_open.call_count, 0)
        self.assertEqual(mock_https_open.call_count, 1)
        self.assertEqual(mock_proxy_open.call_count, 0)
