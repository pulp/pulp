import unittest

import mock

from pulp.server.webservices import http

class TestHTTP(unittest.TestCase):
    @mock.patch.object(http, 'uri_path', return_value='/base/uri/')
    def test_extend_uri_path(self, mock_path):
        ret = http.extend_uri_path('repo1')
        # verify
        mock_path.assert_called_once_with()
        self.assertEqual(ret, '/base/uri/repo1/')

    @mock.patch.object(http, 'uri_path', return_value='/base/uri')
    def test_extend_uri_path_no_trailing_slash(self, mock_path):
        ret = http.extend_uri_path('repo1')
        # verify
        mock_path.assert_called_once_with()
        self.assertEqual(ret, '/base/uri/repo1/')

    @mock.patch.object(http, 'uri_path')
    def test_extend_uri_path_with_prefix(self, mock_path):
        ret = http.extend_uri_path('repo1', '/base/uri/')
        # verify
        self.assertEqual(mock_path.call_count, 0)
        self.assertEqual(ret, '/base/uri/repo1/')

