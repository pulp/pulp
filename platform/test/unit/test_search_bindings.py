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

from pulp.bindings.search import SearchAPI

class TestSearchAPI(unittest.TestCase):
    def test_calls_post(self):
        api = SearchAPI(mock.MagicMock())
        api.PATH = '/some/path'
        api.search(limit=12)

        self.assertEqual(api.server.POST.call_count, 1)
        self.assertEqual(api.server.POST.call_args[0][0], '/some/path')
        self.assertEqual(api.server.POST.call_args[0][1], {'criteria':{'limit':12}})

    def test_returns_response_body(self):
        api = SearchAPI(mock.MagicMock())
        ret = api.search()
        self.assertEqual(ret, api.server.POST.return_value.response_body)

