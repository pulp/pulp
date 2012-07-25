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

from pulp.server.webservices.serialization import link

class TestSerializationLink(unittest.TestCase):
    @mock.patch('pulp.server.webservices.http.uri_path',
        return_value='/base/uri/search/')
    def test_with_search(self, mock_path):
        ret = link.search_safe_link_obj('repo1')
        self.assertEqual(ret, {'_href':'/base/uri/repo1/'})

    @mock.patch('pulp.server.webservices.http.uri_path', return_value='/base/uri/')
    def test_without_search(self, mock_path):
        ret = link.search_safe_link_obj('repo1')
        self.assertEqual(ret, {'_href':'/base/uri/repo1/'})

