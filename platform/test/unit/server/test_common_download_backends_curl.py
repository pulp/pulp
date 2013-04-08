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

import unittest

import mock
import pycurl

from pulp.common.download.config import DownloaderConfig
from pulp.common.download.backends.curl import HTTPSCurlDownloadBackend

from test_common_download import DownloadTests, mock_curl_multi_factory, MockObjFactory


class TestAddProxyConfiguration(unittest.TestCase):
    """
    This test module tests the HTTPSCurlDownloadBackend._add_proxy_configuration method.
    It asserts that the proxy related settings are all appropriately handed
    to pycurl. It uses Mocks to make these assertions, and we will trust that the proxy
    features in pycurl are tested by that project.
    """
    def test_no_proxy_settings(self):
        """
        Test the HTTPSCurlDownloadBackend._add_proxy_configuration method for the case
        when there are no proxy settings. It should not make any calls that are proxy
        related. In fact, due to the nature of the _add_proxy_configuration method, it
        should just not make any calls to setopt() at all, which is what we assert here.
        """
        config = DownloaderConfig('https')
        curl_downloader = HTTPSCurlDownloadBackend(config)
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
        config = DownloaderConfig('https', proxy_url=proxy_url, proxy_port=proxy_port)
        curl_downloader = HTTPSCurlDownloadBackend(config)
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
        config = DownloaderConfig('https', proxy_url=proxy_url)
        curl_downloader = HTTPSCurlDownloadBackend(config)
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
        config = DownloaderConfig('https', proxy_url=proxy_url, proxy_username=proxy_username,
                                  proxy_password=proxy_password)
        curl_downloader = HTTPSCurlDownloadBackend(config)
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
    @mock.patch('pulp.common.download.backends.curl.HTTPSCurlDownloadBackend'
                '._add_proxy_configuration')
    def test__build_easy_handle_calls__add_proxy_configuration(self,
                                                               _add_proxy_configuration):
        """
        This test simply asserts that _build_easy_handle() passes the easy_handle to
        _add_proxy_configuration().
        """
        config = DownloaderConfig('https')
        curl_downloader = HTTPSCurlDownloadBackend(config)

        easy_handle = curl_downloader._build_easy_handle()

        _add_proxy_configuration.assert_called_with(easy_handle)
