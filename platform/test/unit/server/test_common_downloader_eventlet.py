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


class EventletHandlerTests(unittest.TestCase):

    def test_proxy_url(self):
        proxy_host = 'https://slydog.net'
        proxy_port = 9874
        proxy_url = 'https://slydog.net:9874/'
        handler = urllib2_utils.PulpHandler(proxy_url=proxy_host, proxy_port=proxy_port)
        self.assertEqual(proxy_url, handler.proxy_url)

    def test_build_opener(self):
        handler = urllib2_utils.PulpHandler()
        opener = urllib2.build_opener(handler)

        self.assertTrue(handler in opener.handlers)

        # our handler should replace the http, https, and proxy handlers
        for h in opener.handlers:
            if isinstance(h, (urllib2.HTTPHandler, urllib2.HTTPSHandler, urllib2.ProxyHandler)):
                self.assertEqual(h, handler)
                continue

    @mock.patch('pulp.common.download.downloaders.urllib2_utils.PulpHandler.http_open')
    def test_http_handler(self, mock_http_open):
        url = 'http://awesomeserver.org/path/to/latest/awesomeness'
        req = urllib2.Request(url)

        handler = urllib2_utils.PulpHandler()
        opener = urllib2.build_opener(handler)

        try:
            opener.open(req)
        except urllib2.HTTPError:
            pass

        mock_http_open.assert_called_once_with(req)

    @mock.patch('pulp.common.download.downloaders.urllib2_utils.PulpHandler.https_open')
    def test_https_handler(self, mock_https_open):
        url = 'https://awesomeserver.org/path/to/secure/awesomeness'
        req = urllib2.Request(url)

        handler = urllib2_utils.PulpHandler()
        opener = urllib2.build_opener(handler)

        try:
            opener.open(req)
        except urllib2.HTTPError:
            pass

        mock_https_open.assert_called_once_with(req)

    @mock.patch('pulp.common.download.downloaders.urllib2_utils.PulpHandler.proxy_open')
    def test_https_handler(self, mock_proxy_open):
        url = 'https://awesomeserver.org/path/to/secure/awesomeness'
        req = urllib2.Request(url)

        proxy_url = 'https://184.169.138.163'
        proxy_port = 3875

        handler = urllib2_utils.PulpHandler(proxy_url=proxy_url, proxy_port=proxy_port)
        opener = urllib2.build_opener(handler)

        try:
            opener.open(req)
        except urllib2.HTTPError:
            pass

        self.assertEqual(mock_proxy_open.call_count, 1)
        self.assertTrue(req in mock_proxy_open.call_args[0], str(mock_proxy_open.call_args))


class EventletConnectionTests(unittest.TestCase):

    def test_default_port_http(self):
        host = 'my.fakehost.com'
        connection = urllib2_utils.PulpConnection(host)
        self.assertEqual(connection.default_port, 80)

    def test_default_port_https(self):
        host = 'my.fakehost.com'
        connection = urllib2_utils.PulpConnection(host, scheme='https')
        self.assertEqual(connection.default_port, 443)

    @mock.patch('pulp.common.download.downloaders.urllib2_utils.PulpConnection.request')
    def test_request(self, mock_request):
        url = 'http://somenewserver.com/path/old/file'
        req = urllib2.Request(url)
        opener = urllib2.build_opener(urllib2_utils.PulpHandler())

        try:
            opener.open(req)
        except httplib.ResponseNotReady:
            pass

        self.assertEqual(mock_request.call_count, 1)
        self.assertTrue('/path/old/file' in mock_request.call_args[0], str(mock_request.call_args[0]))

    @mock.patch('pulp.common.download.downloaders.urllib2_utils.PulpConnection.connect')
    def test_connect(self, mock_connect):
        url = 'http://somenewserver.com/path/old/file'
        req = urllib2.Request(url)
        opener = urllib2.build_opener(urllib2_utils.PulpHandler())

        try:
            opener.open(req)
        except AttributeError: # raised when None gets passed to the socket
            pass

        self.assertEqual(mock_connect.call_count, 1)
