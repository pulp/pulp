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
from pulp.server.webservices.controllers.advanced_search import AdvancedSearchController

class TestGetQueryResults(unittest.TestCase):
    PARAMS = {'criteria' : {}}

    def setUp(self):
        self.mock_collection = mock.MagicMock()
        self.controller = AdvancedSearchController(self.mock_collection)
        self.controller.params = mock.MagicMock(return_value=self.PARAMS)

    def test_requires_criteria(self):
        self.controller.params = mock.MagicMock(return_value={})
        self.assertRaises(exceptions.MissingValue, self.controller._get_query_results)

    def test_calls_query(self):
        self.controller._get_query_results()
        self.assertEqual(self.mock_collection.query.call_count, 1)
        self.assertTrue(isinstance(self.mock_collection.query.call_args[0][0], Criteria))
