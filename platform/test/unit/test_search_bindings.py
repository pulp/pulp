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
from okaara.cli import CommandUsage

from pulp.bindings.search import SearchAPI, Operator, IntOperator, CSVOperator

class TestSearchAPI(unittest.TestCase):
    def setUp(self):
        super(TestSearchAPI, self).setUp()
        self.api = SearchAPI(mock.MagicMock())
        self.api.PATH = '/some/path'

    def test_calls_post(self):
        self.api.search(limit=12)

        self.assertEqual(self.api.server.POST.call_count, 1)
        self.assertEqual(self.api.server.POST.call_args[0][0], '/some/path')
        self.assertEqual(self.api.server.POST.call_args[0][1], {'criteria':{'limit':12}})

    def test_returns_response_body(self):
        ret = self.api.search()
        self.assertEqual(ret, self.api.server.POST.return_value.response_body)

    def test_invalid_kwargs(self):
        self.assertRaises(CommandUsage, self.api.search, foo=True)

    @mock.patch('pulp.bindings.search.SearchAPI._compose_filters')
    def test_calls_compose(self, mock_compose):
        self.api.search(limit=20)
        mock_compose.assert_called_once_with(limit=20)

    def test_remove_non_criteria(self):
        self.api.search(gt=['count=20'])
        spec = self.api.server.POST.call_args[0][1]['criteria']
        self.assertTrue('gt' not in spec)
        self.assertTrue('filters' in spec)

    def test_compose_prefers_filters(self):
        kwargs = {'filters' : '{}', 'gt': ['count=20']}
        ret = self.api._compose_filters(**kwargs)
        self.assertTrue('gt' not in ret)
        self.assertEqual(ret, '{}')

    @mock.patch('pulp.bindings.search.Operator.compose_filters')
    def test_compose_calls_operator(self, mock_compose):
        ret = self.api._compose_filters(gt=['count=20'])
        mock_compose.assert_called_once_with(['count=20'])


class TestOperator(unittest.TestCase):
    def setUp(self):
        super(TestOperator, self).setUp()

    def test_split_valid(self):
        ret = Operator._split_arg('id=repo1')
        self.assertEqual(ret, ['id', 'repo1'])

    def test_split_one(self):
        # missing an '=' sign and value
        self.assertRaises(CommandUsage, Operator._split_arg, 'repo1')

    def test_split_three(self):
        # additional '=' characters are included in the value
        ret = Operator._split_arg('id=repo1=awesome')
        self.assertEqual(ret, ['id', 'repo1=awesome'])

    def test_string_compose(self):
        ret = Operator('$not').compose_filters(['id=repo1'])
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0], {'id':{'$not':'repo1'}})


class TestCSVOperator(unittest.TestCase):
    def test_split_valid(self):
        field_name, value = CSVOperator._split_arg('id=repo1,repo2')
        self.assertEqual(field_name, 'id')
        self.assertEqual(value, ['repo1', 'repo2'])

    def test_split_valid_one(self):
        field_name, value = CSVOperator._split_arg('id=repo1')
        self.assertEqual(field_name, 'id')
        self.assertEqual(value, ['repo1'])

    def test_split_one(self):
        # missing an '=' sign and value
        self.assertRaises(CommandUsage, CSVOperator._split_arg, 'repo1')


class TestIntOperator(unittest.TestCase):
    def test_compose_valid(self):
        ret = IntOperator('$gt').compose_filters(['count=2', 'price=20'])
        self.assertEqual(len(ret), 2)
        self.assertEqual(ret, [{'count':{'$gt':2}}, {'price':{'$gt':20}}])

    def test_compose_invalid(self):
        operator = IntOperator('$gt')
        self.assertRaises(CommandUsage, operator.compose_filters, 'x=foo')

