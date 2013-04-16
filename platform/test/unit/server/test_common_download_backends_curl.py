# -*- coding: utf-8 *-*
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

from datetime import datetime
import os
import mock
import unittest
import urlparse

import pycurl

from pulp.common.download.config import DownloaderConfig
from pulp.common.download.listener import AggregatingEventListener
from pulp.common.download.downloaders.curl import (
    DEFAULT_FOLLOW_LOCATION, DEFAULT_MAX_REDIRECTS, DEFAULT_CONNECT_TIMEOUT, DEFAULT_LOW_SPEED_LIMIT,
    DEFAULT_LOW_SPEED_TIME, DEFAULT_NO_PROGRESS, HTTPCurlDownloader, HTTPSCurlDownloader)
from pulp.common.download.report import DOWNLOAD_FAILED, DownloadReport, DOWNLOAD_SUCCEEDED

from test_common_download import DownloadTests, mock_curl_easy_factory, mock_curl_multi_factory, MockObjFactory


def mock_curl_multi_factory_with_errors():
    """
    This multi factory mock will cause the generated CurlMulti to report that it had errors for all downloads.
    """
    mock_curl_multi = mock_curl_multi_factory()

    def _info_read():
        err_list = [(c, 999, 'ERROR!') for c in mock_curl_multi._curls if c._is_active]
        return 0, [], err_list

    mock_curl_multi.info_read = _info_read

    return mock_curl_multi


class TestAddConnectionConfiguration(unittest.TestCase):
    """
    This test module tests the HTTPSCurlDownloadBackend._add_connection_configuration method. It asserts that
    all the appropriate default values are passed to pycurl, no more and no less. It uses Mocks to make these
    assertions, and we will trust that the features in pycurl are tested by that project.
    """
    def test_defaults(self):
        """
        Assert that the default configuration options are handed to the pycurl easy_handle.
        """
        config = DownloaderConfig('https')
        curl_downloader = HTTPSCurlDownloadBackend(config)
        easy_handle = mock.MagicMock()

        curl_downloader._add_connection_configuration(easy_handle)

        # There are currently 6 settings that this method should set. If this assertion fails due to changes you
        # intentionally made to _add_connection_configuration, please update this count, and please also update
        # the setting assertions below it so that they are complete.
        self.assertEqual(easy_handle.setopt.call_count, 6)
        easy_handle.setopt.assert_any_call(pycurl.FOLLOWLOCATION, DEFAULT_FOLLOW_LOCATION)
        easy_handle.setopt.assert_any_call(pycurl.MAXREDIRS, DEFAULT_MAX_REDIRECTS)
        easy_handle.setopt.assert_any_call(pycurl.CONNECTTIMEOUT, DEFAULT_CONNECT_TIMEOUT)
        easy_handle.setopt.assert_any_call(pycurl.LOW_SPEED_LIMIT, DEFAULT_LOW_SPEED_LIMIT)
        easy_handle.setopt.assert_any_call(pycurl.LOW_SPEED_TIME, DEFAULT_LOW_SPEED_TIME)
        easy_handle.setopt.assert_any_call(pycurl.NOPROGRESS, DEFAULT_NO_PROGRESS)


class TestAddProxyConfiguration(unittest.TestCase):
    """
    This test module tests the HTTPCurlDownloader._add_proxy_configuration method.
    It asserts that the proxy related settings are all appropriately handed
    to pycurl. It uses Mocks to make these assertions, and we will trust that the proxy
    features in pycurl are tested by that project.
    """
    def test_no_proxy_settings(self):
        """
        Test the HTTPCurlDownloader._add_proxy_configuration method for the case
        when there are no proxy settings. It should not make any calls that are proxy
        related. In fact, due to the nature of the _add_proxy_configuration method, it
        should just not make any calls to setopt() at all, which is what we assert here.
        """
        config = DownloaderConfig()
        curl_downloader = HTTPCurlDownloader(config)
        easy_handle = mock.MagicMock()

        curl_downloader._add_proxy_configuration(easy_handle)

        # We can be sure that no proxy settings were set on the easy_handle if no calls
        # to its setopt method were called.
        self.assertEqual(easy_handle.setopt.call_count, 0)

    def test_proxy_port_set(self):
        """
        Test correct behavior when proxy_url and proxy_port are set.
        """
        proxy_url = u'http://proxy.com/server/'
        proxy_port = '3128'
        config = DownloaderConfig(proxy_url=proxy_url, proxy_port=proxy_port)
        curl_downloader = HTTPCurlDownloader(config)
        easy_handle = mock.MagicMock()

        curl_downloader._add_proxy_configuration(easy_handle)

        # There should be three calls to setopt(). One to set the URL, one another to set
        # the proxy type to HTTP, and a third to set the proxy port.
        self.assertEqual(easy_handle.setopt.call_count, 3)
        easy_handle.setopt.assert_any_call(pycurl.PROXY, str(proxy_url))
        easy_handle.setopt.assert_any_call(pycurl.PROXYTYPE, pycurl.PROXYTYPE_HTTP)
        easy_handle.setopt.assert_any_call(pycurl.PROXYPORT, int(proxy_port))
        self._assert_all_strings_handed_to_pycurl_are_strs(easy_handle.setopt.mock_calls)

    def test_proxy_url_set(self):
        """
        Test correct behavior when only proxy_url is set.
        """
        proxy_url = u'http://proxy.com/server/'
        config = DownloaderConfig(proxy_url=proxy_url)
        curl_downloader = HTTPCurlDownloader(config)
        easy_handle = mock.MagicMock()

        curl_downloader._add_proxy_configuration(easy_handle)

        # There should be two calls to setopt(). One to set the URL, and another to set
        # the proxy type to HTTP
        self.assertEqual(easy_handle.setopt.call_count, 2)
        easy_handle.setopt.assert_any_call(pycurl.PROXY, unicode(str(proxy_url)))
        easy_handle.setopt.assert_any_call(pycurl.PROXYTYPE, pycurl.PROXYTYPE_HTTP)
        self._assert_all_strings_handed_to_pycurl_are_strs(easy_handle.setopt.mock_calls)

    def test_proxy_username_password_set(self):
        """
        Test correct behavior when proxy_url, proxy_username, and proxy_password are all
        set.
        """
        proxy_url = u'http://proxy.com/server/'
        proxy_username = u'steve'
        proxy_password = u'1luvpr0xysrvrs'
        config = DownloaderConfig(proxy_url=proxy_url, proxy_username=proxy_username,
                                  proxy_password=proxy_password)
        curl_downloader = HTTPCurlDownloader(config)
        easy_handle = mock.MagicMock()

        curl_downloader._add_proxy_configuration(easy_handle)

        # There should be four calls to setopt(). One to set the URL, one to set
        # the proxy type to HTTP, one to set the auth type to HTTP basic auth, and
        # another to pass the username and password.
        self.assertEqual(easy_handle.setopt.call_count, 4)
        easy_handle.setopt.assert_any_call(pycurl.PROXY, str(proxy_url))
        easy_handle.setopt.assert_any_call(pycurl.PROXYTYPE, pycurl.PROXYTYPE_HTTP)
        easy_handle.setopt.assert_any_call(pycurl.PROXYAUTH, pycurl.HTTPAUTH_BASIC)
        easy_handle.setopt.assert_any_call(pycurl.PROXYUSERPWD, '%s:%s'%(proxy_username, proxy_password))
        self._assert_all_strings_handed_to_pycurl_are_strs(easy_handle.setopt.mock_calls)

    def _assert_all_strings_handed_to_pycurl_are_strs(self, mock_calls):
        """
        pycurl gets very upset if unicode objects are handed to it when a string should
        be given to it, so this method inspects the given list of mock_calls from
        setopt(), scanning for unicode objects. It will assert that all basestrings are
        of type str.
        """
        for mock_call in mock_calls:
            setting_name, setting_value = mock_call[1]
            if isinstance(setting_value, basestring):
                self.assertTrue(isinstance(setting_value, str))


class TestBuildEasyHandle(unittest.TestCase):
    """
    This test suite tests the _build_easy_handle() method.
    """
    @mock.patch('pycurl.Curl', mock.MagicMock)
    @mock.patch('pulp.common.download.downloaders.curl.HTTPCurlDownloader'
                '._add_connection_configuration')
    def test__build_easy_handle_calls__add_connection_configuration(self,
                                                                    _add_connection_configuration):
        """
        This test simply asserts that _build_easy_handle() passes the easy_handle to
        _add_connection_configuration().
        """
        config = DownloaderConfig()
        curl_downloader = HTTPCurlDownloader(config)

        easy_handle = curl_downloader._build_easy_handle()

        _add_connection_configuration.assert_called_with(easy_handle)

    @mock.patch('pycurl.Curl', mock.MagicMock)
    @mock.patch('pulp.common.download.downloaders.curl.HTTPCurlDownloader'
                '._add_proxy_configuration')
    def test__build_easy_handle_calls__add_proxy_configuration(self,
                                                               _add_proxy_configuration):
        """
        This test simply asserts that _build_easy_handle() passes the easy_handle to
        _add_proxy_configuration().
        """
        config = DownloaderConfig()
        curl_downloader = HTTPCurlDownloader(config)

        easy_handle = curl_downloader._build_easy_handle()

        _add_proxy_configuration.assert_called_with(easy_handle)


class TestAddConnectionConfiguration(unittest.TestCase):
    """
    Test the HTTPCurlDownloader._add_connection_configuration() method.
    """
    @mock.patch('pycurl.Curl', mock.MagicMock)
    def test_max_speed_set(self):
        """
        Assert that the max speed gets passed to pycurl when it is set.
        """
        # Let's try specifying the max speed as a string of a valid integer, to verify that we correctly
        # cast it to an integer.
        max_speed = '57'
        config = DownloaderConfig(max_speed=max_speed)
        curl_downloader = HTTPCurlDownloader(config)
        easy_handle = mock.MagicMock()

        curl_downloader._add_connection_configuration(easy_handle)

        # Make sure that the max_speed setting was passed to our easy_handle
        easy_handle.setopt.assert_any_call(pycurl.MAX_RECV_SPEED_LARGE, int(max_speed))

    @mock.patch('pycurl.Curl', mock.MagicMock)
    def test_max_speed_unset(self):
        """
        Assert that the max speed does not get passed to pycurl when it is not set.
        """
        # Let's leave max_speed out of this config
        config = DownloaderConfig()
        curl_downloader = HTTPCurlDownloader(config)

        easy_handle = curl_downloader._build_easy_handle()

        # Now let's assert that MAX_RECV_SPEED_LARGE wasn't passed to setopt
        setopt_setting_args = [call[0][0] for call in easy_handle.setopt.call_args_list]
        self.assertTrue(pycurl.MAX_RECV_SPEED_LARGE not in setopt_setting_args)


class TestDownload(DownloadTests):
    """
    This suite of tests are for the HTTPCurlDownloader.download() method.
    """
    @mock.patch('pycurl.CurlMulti', MockObjFactory(mock_curl_multi_factory_with_errors))
    @mock.patch('pycurl.Curl', MockObjFactory(mock_curl_easy_factory))
    @mock.patch('pulp.common.download.downloaders.curl.HTTPCurlDownloader._process_completed_download')
    def test_calls__process_completed_download_err_list(self, _process_completed_download):
        """
        In this test, we assert that download() calls _process_completed_download() correctly when pycurl
        reports a completed download through the error list.
        """
        # If we set max_concurrent to 1, it's easy to deterministically find the mocked curl for assertions
        # later
        config = DownloaderConfig(max_concurrent=1)
        curl_downloader = HTTPCurlDownloader(config)
        request_list = self._download_requests()[:1]

        curl_downloader.download(request_list)

        mock_easy_handle = pycurl.Curl.mock_objs[0]
        mock_multi_handle = pycurl.CurlMulti.mock_objs[0]
        self.assertEqual(_process_completed_download.call_count, 1)
        args = _process_completed_download.mock_calls[0][1]
        # There should be four args, since there were errors
        self.assertEqual(len(args), 4)
        # Now let's assert that the arguments were correct
        self.assertEqual(args[0], mock_easy_handle)
        self.assertEqual(args[1], mock_multi_handle)
        # There should be no free handles, since there was only one and it's being reported on
        self.assertEqual(args[2], [])
        # Assert that the error condition was passed
        self.assertEqual(args[3], {'code': 999, 'message': 'ERROR!'})

    @mock.patch('pycurl.CurlMulti', MockObjFactory(mock_curl_multi_factory))
    @mock.patch('pycurl.Curl', MockObjFactory(mock_curl_easy_factory))
    @mock.patch('pulp.common.download.downloaders.curl.HTTPCurlDownloader._process_completed_download')
    def test_calls__process_completed_download_ok_list(self, _process_completed_download):
        """
        In this test, we assert that download() calls _process_completed_download() correctly when pycurl
        reports a completed download through the OK list.
        """
        # If we set max_concurrent to 1, it's easy to deterministically find the mocked curl for assertions
        # later
        config = DownloaderConfig(max_concurrent=1)
        curl_downloader = HTTPCurlDownloader(config)
        request_list = self._download_requests()[:1]

        curl_downloader.download(request_list)

        mock_easy_handle = pycurl.Curl.mock_objs[0]
        mock_multi_handle = pycurl.CurlMulti.mock_objs[0]
        self.assertEqual(_process_completed_download.call_count, 1)
        args = _process_completed_download.mock_calls[0][1]
        # There should only be three args, since there were no errors
        self.assertEqual(len(args), 3)
        # Now let's assert that the arguments were correct
        self.assertEqual(args[0], mock_easy_handle)
        self.assertEqual(args[1], mock_multi_handle)
        # There should be no free handles, since there was only one and it's being reported on
        self.assertEqual(args[2], [])

    def test_file_scheme(self):
        """
        In this test, we're making sure that file:// URLs work and is reported as succeeded
        when the path is valid.
        """
        # Test
        config = DownloaderConfig(max_concurrent=1)
        downloader = HTTPCurlDownloader(config)
        request_list = self._file_download_requests()[:1]
        listener = AggregatingEventListener()
        downloader.event_listener = listener
        downloader.download(request_list)
        # Verify
        self.assertEqual(len(listener.succeeded_reports), 1)
        self.assertEqual(len(listener.failed_reports), 0)
        self.assertTrue(os.path.exists(request_list[0].destination))
        # verify the downloaded file matches
        path_in = urlparse.urlparse(request_list[0].url).path
        fp = open(path_in)
        original_content = fp.read()
        fp.close()
        fp = open(request_list[0].destination)
        destination_content = fp.read()
        fp.close()
        self.assertEqual(original_content, destination_content)

    def test_file_scheme_with_invalid_path(self):
        """
        In this test, we're making sure that file:// URLs work and is reported as failed
        when the path is invalid.
        """
        # Test
        config = DownloaderConfig(max_concurrent=1)
        downloader = HTTPCurlDownloader(config)
        request_list = self._file_download_requests()[:1]
        request_list[0].url += 'BADPATHBADPATHBADPATH'  # booger up the path
        listener = AggregatingEventListener()
        downloader.event_listener = listener
        downloader.download(request_list)
        # Verify
        self.assertEqual(len(listener.succeeded_reports), 0)
        self.assertEqual(len(listener.failed_reports), 1)
        report = listener.failed_reports[0]
        self.assertEqual(report.bytes_downloaded, 0)
        self.assertEqual(report.error_report['response_code'], 0)

    @mock.patch('pycurl.CurlMulti', MockObjFactory(mock_curl_multi_factory))
    @mock.patch('pycurl.Curl', MockObjFactory(mock_curl_easy_factory))
    def test_is_canceled_false(self):
        """
        In this test, we leave the is_canceled boolean unset on the downloader, and we verify that the main
        loop executes once. Because our pycurl mocks "download" the entire file in one go, it will only
        execute one time, which means we can simply count that the select() call was made exactly once.
        """
        config = DownloaderConfig()
        curl_downloader = HTTPCurlDownloader(config)
        request_list = self._download_requests()[:1]

        curl_downloader.download(request_list)

        mock_multi_curl = pycurl.CurlMulti.mock_objs[0]
        # The call_count on the select() should be 1 since our pycurl Mock "downloads" the file in one go
        self.assertEqual(mock_multi_curl.select.call_count, 1)

    @mock.patch('pycurl.CurlMulti', MockObjFactory(mock_curl_multi_factory))
    @mock.patch('pycurl.Curl', MockObjFactory(mock_curl_easy_factory))
    def test_is_canceled_true(self):
        """
        In this test, we set the is_canceled boolean on the downloader, and we verify that the main loop
        does not execute.
        """
        config = DownloaderConfig()
        curl_downloader = HTTPCurlDownloader(config)
        # Let's go ahead and set the cancellation flag, so the loop should not execute
        curl_downloader.cancel()
        request_list = self._download_requests()[:1]

        curl_downloader.download(request_list)

        mock_multi_curl = pycurl.CurlMulti.mock_objs[0]
        # Because we cancelled the download, the call_count on the select() should be 0
        self.assertEqual(mock_multi_curl.select.call_count, 0)


class TestProcessCompletedDownload(unittest.TestCase):
    """
    Test the HTTPCurlDownloader._process_completed_download() method.
    """
    @mock.patch('pulp.common.download.downloaders.curl.HTTPCurlDownloader._clear_easy_handle_download')
    @mock.patch('pulp.common.download.downloaders.curl.HTTPCurlDownloader.fire_download_failed')
    @mock.patch('pulp.common.download.downloaders.curl.HTTPCurlDownloader.fire_download_succeeded')
    @mock.patch('pycurl.CurlMulti', MockObjFactory(mock_curl_multi_factory))
    @mock.patch('pycurl.Curl', MockObjFactory(mock_curl_easy_factory))
    def test_download_successful(self, fire_download_succeeded, fire_download_failed,
                                 _clear_easy_handle_download):
        """
        Assert correct behavior for a successful download.
        """
        config = DownloaderConfig(max_concurrent=1)
        curl_downloader = HTTPCurlDownloader(config)
        multi_handle = curl_downloader._build_multi_handle()
        easy_handle = multi_handle.handles[0]
        easy_handle.report = DownloadReport('http://fake.com/doesntmatter.html', '/dev/null')
        multi_handle._curls = [easy_handle]
        free_handles = []
        start_time = datetime.now()

        curl_downloader._process_completed_download(easy_handle, multi_handle, free_handles)

        # The easy_handle should have been removed from the multi_handle
        multi_handle.remove_handle.assert_called_once_with(easy_handle)
        # _clear_easy_handle_download should have been handed the easy_handle
        _clear_easy_handle_download.assert_called_once_wth(easy_handle)
        # The free_handles list should have the easy_handle
        self.assertEqual(free_handles, [easy_handle])
        # fire_download_failed should not have been called
        self.assertEqual(fire_download_failed.call_count, 0)

        # fire_download_succeeded should have been called once with the report. Let's assert that, and assert
        # that the report looks good
        self.assertEqual(fire_download_succeeded.call_count, 1)
        report = fire_download_succeeded.mock_calls[0][1][0]
        self.assertTrue(isinstance(report, DownloadReport))
        self.assertTrue(report.state, DOWNLOAD_SUCCEEDED)
        # It's difficult to know what the finish_time on the report will be exactly, so we'll just assert that
        # it's after the start_time we recorded earlier
        self.assertTrue(report.finish_time > start_time)

    @mock.patch('pulp.common.download.downloaders.curl.HTTPCurlDownloader._clear_easy_handle_download')
    @mock.patch('pulp.common.download.downloaders.curl.HTTPCurlDownloader.fire_download_failed')
    @mock.patch('pulp.common.download.downloaders.curl.HTTPCurlDownloader.fire_download_succeeded')
    @mock.patch('pycurl.CurlMulti', MockObjFactory(mock_curl_multi_factory))
    @mock.patch('pycurl.Curl', MockObjFactory(mock_curl_easy_factory))
    def test_http_error_code(self, fire_download_succeeded, fire_download_failed, _clear_easy_handle_download):
        """
        Assert correct behavior when the HTTP status is not 200, but there were no pycurl errors.
        """
        config = DownloaderConfig(max_concurrent=1)
        curl_downloader = HTTPCurlDownloader(config)
        multi_handle = curl_downloader._build_multi_handle()
        easy_handle = multi_handle.handles[0]
        easy_handle.report = DownloadReport('http://fake.com/doesntmatter.html', '/dev/null')
        multi_handle._curls = [easy_handle]

        def return_code(ignored_param):
            """
            This function will allow us to fake a non-200 response code.
            """
            return 404

        easy_handle.getinfo = return_code
        free_handles = []
        start_time = datetime.now()

        curl_downloader._process_completed_download(easy_handle, multi_handle, free_handles)

        # The easy_handle should have been removed from the multi_handle
        multi_handle.remove_handle.assert_called_once_with(easy_handle)
        # _clear_easy_handle_download should have been handed the easy_handle
        _clear_easy_handle_download.assert_called_once_wth(easy_handle)
        # The free_handles list should have the easy_handle
        self.assertEqual(free_handles, [easy_handle])
        # fire_download_succeeded should not have been called
        self.assertEqual(fire_download_succeeded.call_count, 0)

        # fire_download_failed should have been called once with the report. Let's assert that, and assert
        # that the report looks good
        self.assertEqual(fire_download_failed.call_count, 1)
        report = fire_download_failed.mock_calls[0][1][0]
        self.assertTrue(isinstance(report, DownloadReport))
        self.assertTrue(report.state, DOWNLOAD_FAILED)
        self.assertEqual(report.error_report['response_code'], 404)
        # It's difficult to know what the finish_time on the report will be exactly, so we'll just assert that
        # it's after the start_time we recorded earlier
        self.assertTrue(report.finish_time > start_time)

    @mock.patch('pulp.common.download.downloaders.curl.HTTPCurlDownloader._clear_easy_handle_download')
    @mock.patch('pulp.common.download.downloaders.curl.HTTPCurlDownloader.fire_download_failed')
    @mock.patch('pulp.common.download.downloaders.curl.HTTPCurlDownloader.fire_download_succeeded')
    @mock.patch('pycurl.CurlMulti', MockObjFactory(mock_curl_multi_factory))
    @mock.patch('pycurl.Curl', MockObjFactory(mock_curl_easy_factory))
    def test_pycurl_errors(self, fire_download_succeeded, fire_download_failed, _clear_easy_handle_download):
        """
        Assert correct behavior when error is not None.
        """
        config = DownloaderConfig(max_concurrent=1)
        curl_downloader = HTTPCurlDownloader(config)
        multi_handle = curl_downloader._build_multi_handle()
        easy_handle = multi_handle.handles[0]
        easy_handle.report = DownloadReport('http://fake.com/doesntmatter.html', '/dev/null')
        multi_handle._curls = [easy_handle]

        def return_code(ignored_param):
            """
            This function will allow us to fake the response code when pycurl didn't reach the server, which
            will be 0.
            """
            return 0

        easy_handle.getinfo = return_code
        free_handles = []
        start_time = datetime.now()

        curl_downloader._process_completed_download(
            easy_handle, multi_handle, free_handles,
            {'code': pycurl.E_COULDNT_CONNECT, 'message': "Couldn't Connect"})

        # The easy_handle should have been removed from the multi_handle
        multi_handle.remove_handle.assert_called_once_with(easy_handle)
        # _clear_easy_handle_download should have been handed the easy_handle
        _clear_easy_handle_download.assert_called_once_wth(easy_handle)
        # The free_handles list should have the easy_handle
        self.assertEqual(free_handles, [easy_handle])
        # fire_download_succeeded should not have been called
        self.assertEqual(fire_download_succeeded.call_count, 0)

        # fire_download_failed should have been called once with the report. Let's assert that, and assert
        # that the report looks good
        self.assertEqual(fire_download_failed.call_count, 1)
        report = fire_download_failed.mock_calls[0][1][0]
        self.assertTrue(isinstance(report, DownloadReport))
        self.assertTrue(report.state, DOWNLOAD_FAILED)
        self.assertEqual(report.error_report['response_code'], 0)
        self.assertEqual(report.error_report['error_code'], pycurl.E_COULDNT_CONNECT)
        self.assertEqual(report.error_report['error_message'], "Couldn't Connect")
        # It's difficult to know what the finish_time on the report will be exactly, so we'll just assert that
        # it's after the start_time we recorded earlier
        self.assertTrue(report.finish_time > start_time)


class TestAddSSLConfiguration(unittest.TestCase):
    """
    Assert correct behaviour in the _add_ssl_configuration() method.
    """
    def test_ssl_validation_false(self):
        """
        Assert that Curl is not configured to do SSL validation when ssl_validation is explicitly set to False.
        """
        config = DownloaderConfig(ssl_validation=False)
        curl_downloader = HTTPSCurlDownloader(config)
        easy_handle = mock.Mock()

        curl_downloader._add_ssl_configuration(easy_handle)

        self.assertEqual(easy_handle.setopt.call_count, 2)
        easy_handle.setopt.assert_any_call(pycurl.SSL_VERIFYPEER, 0)
        easy_handle.setopt.assert_any_call(pycurl.SSL_VERIFYHOST, 0)

    def test_ssl_validation_true(self):
        """
        Assert that Curl is configured to do SSL validation when ssl_validation is explicitly set to True.
        """
        config = DownloaderConfig(ssl_validation=True)
        curl_downloader = HTTPSCurlDownloader(config)
        easy_handle = mock.Mock()

        curl_downloader._add_ssl_configuration(easy_handle)

        self.assertEqual(easy_handle.setopt.call_count, 2)
        easy_handle.setopt.assert_any_call(pycurl.SSL_VERIFYPEER, 1)
        easy_handle.setopt.assert_any_call(pycurl.SSL_VERIFYHOST, 2)

    def test_ssl_validation_unset(self):
        """
        Assert that Curl is configured to do SSL validation by default when ssl_validation is unset.
        """
        config = DownloaderConfig()
        curl_downloader = HTTPSCurlDownloader(config)
        easy_handle = mock.Mock()

        curl_downloader._add_ssl_configuration(easy_handle)

        self.assertEqual(easy_handle.setopt.call_count, 2)
        easy_handle.setopt.assert_any_call(pycurl.SSL_VERIFYPEER, 1)
        easy_handle.setopt.assert_any_call(pycurl.SSL_VERIFYHOST, 2)
