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

from pulp.server.db.model.criteria import Criteria
import pulp.server.exceptions as exceptions
from pulp.server.webservices.controllers.search import SearchController

class TestGetQueryResultsFromPost(unittest.TestCase):
    PARAMS = {'criteria' : {}}

    def setUp(self):
        self.mock_query_method = mock.MagicMock()
        self.controller = SearchController(self.mock_query_method)
        self.controller.params = mock.MagicMock(return_value=self.PARAMS)

    def test_requires_criteria(self):
        self.controller.params = mock.MagicMock(return_value={})
        self.assertRaises(exceptions.MissingValue, self.controller._get_query_results_from_post)

    def test_calls_query(self):
        self.controller._get_query_results_from_post()
        self.assertEqual(self.mock_query_method.call_count, 1)
        self.assertTrue(isinstance(self.mock_query_method.call_args[0][0], Criteria))

class TestGetQueryResultsFromGet(unittest.TestCase):
    def setUp(self):
        self.mock_query_method = mock.MagicMock()
        self.controller = SearchController(self.mock_query_method)

    @mock.patch('web.input', return_value={'field':[]})
    def test_calls_query(self, mock_input):
        self.controller._get_query_results_from_get()
        self.assertEqual(mock_input.call_count, 1)
        self.assertEqual(self.mock_query_method.call_count, 1)
        self.assertTrue(isinstance(self.mock_query_method.call_args[0][0], Criteria))

    @mock.patch('web.input', return_value={'field':[], 'limit':10, 'foo':1, 'bar':2})
    @mock.patch('pulp.server.db.model.criteria.Criteria.from_client_input')
    def test_ignore_fields(self, mock_from_client, mock_input):
        self.controller._get_query_results_from_get(('foo','bar'))
        mock_from_client.assert_called_once_with({'limit':10})

