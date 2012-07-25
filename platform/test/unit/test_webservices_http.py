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

