# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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

from pulp.server.db.model import criteria
from pulp.server import exceptions

FIELDS = set(('sort', 'skip', 'limit', 'filters', 'fields'))

class TestAsDict(unittest.TestCase):
    def test_empty(self):
        c = criteria.Criteria()
        ret = c.as_dict()
        self.assertTrue(isinstance(ret, dict))
        for field in FIELDS:
            self.assertTrue(ret[field] is None)

    def test_full(self):
        c = criteria.Criteria(
            filters = {'name':{'$in':['a','b']}},
            sort = (('name','ascending'),),
            limit = 10,
            skip = 10,
            fields = ('name', 'id')
        )
        ret = c.as_dict()
        self.assertTrue(isinstance(ret['filters'], dict))
        self.assertEqual(ret['limit'], 10)
        self.assertEqual(ret['skip'], 10)
        self.assertEqual(ret['fields'], c.fields)
        self.assertEqual(set(ret.keys()), FIELDS)


class TestClientInputValidation(unittest.TestCase):
    def test_as_dict(self):
        # this should work
        criteria.Criteria.from_client_input({})

    def test_as_string(self):
        self.assertRaises(exceptions.InvalidValue,
            criteria.Criteria.from_client_input, 'abc 123')

    def test_as_int(self):
        self.assertRaises(exceptions.InvalidValue,
            criteria.Criteria.from_client_input, 123)

    def test_as_none(self):
        self.assertRaises(exceptions.InvalidValue,
            criteria.Criteria.from_client_input, None)

    def test_as_bool(self):
        self.assertRaises(exceptions.InvalidValue,
            criteria.Criteria.from_client_input, True)

    def test_as_list(self):
        self.assertRaises(exceptions.InvalidValue,
            criteria.Criteria.from_client_input, [])


class TestValidateFilters(unittest.TestCase):
    def test_as_dict(self):
        input = {'id':'repo1'}
        ret = criteria._validate_filters(input)
        self.assertEqual(ret, input)

    def test_as_string(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_filters,
            'abc 123')

    def test_as_int(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_filters,
            123)

    def test_as_none(self):
        ret = criteria._validate_filters(None)
        self.assertTrue(ret is None)

    def test_as_bool(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_filters,
            True)

    def test_as_list(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_filters,
            [])


class TestValidateSort(unittest.TestCase):
    def test_as_list(self):
        input = []
        ret = criteria._validate_sort(input)
        self.assertEqual(ret, input)

    def test_as_tuple(self):
        input = ()
        ret = criteria._validate_sort(input)
        self.assertEqual(ret, [])

    def test_as_string(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_sort,
            'abc 123')

    def test_as_int(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_sort, 123)

    def test_as_none(self):
        ret = criteria._validate_sort(None)
        self.assertTrue(ret is None)

    def test_as_bool(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_sort,
            True)

    def test_as_dict(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_sort, {})


class TestValidateLimit(unittest.TestCase):
    def test_as_int(self):
        input = 20
        ret = criteria._validate_limit(input)
        self.assertEqual(ret, input)

    def test_as_int_string(self):
        input = '20'
        ret = criteria._validate_limit(input)
        self.assertEqual(ret, 20)

    def test_as_zero(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_limit, 0)

    def test_as_negative(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_limit, -1)

    def test_as_tuple(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_limit, ())

    def test_as_string(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_limit,
            'abc 123')

    def test_as_list(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_limit, [])

    def test_as_none(self):
        ret = criteria._validate_limit(None)
        self.assertTrue(ret is None)

    def test_as_bool(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_limit,
            True)

    def test_as_dict(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_limit, {})


class TestValidateSkip(unittest.TestCase):
    def test_as_int(self):
        input = 20
        ret = criteria._validate_skip(input)
        self.assertEqual(ret, input)

    def test_as_int_string(self):
        input = '20'
        ret = criteria._validate_skip(input)
        self.assertEqual(ret, 20)

    def test_as_zero(self):
        input = 0
        ret = criteria._validate_skip(input)
        self.assertEqual(ret, input)

    def test_as_negative(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_skip, -1)

    def test_as_tuple(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_skip, ())

    def test_as_string(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_skip,
            'abc 123')

    def test_as_list(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_skip, [])

    def test_as_none(self):
        ret = criteria._validate_skip(None)
        self.assertTrue(ret is None)

    def test_as_bool(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_skip,
            True)

    def test_as_dict(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_skip, {})


class TestValidateFields(unittest.TestCase):
    def test_as_list(self):
        input = []
        ret = criteria._validate_fields(input)
        self.assertEqual(ret, input)

    def test_as_tuple(self):
        input = ()
        ret = criteria._validate_fields(input)
        self.assertEqual(ret, list(input))

    def test_as_string(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields,
            'abc 123')

    def test_as_int(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields, 123)

    def test_as_none(self):
        ret = criteria._validate_fields(None)
        self.assertTrue(ret is None)

    def test_as_bool(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields,
            True)

    def test_as_dict(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields, {})

    def test_items_as_string(self):
        input = ['id', 'name']
        ret = criteria._validate_fields(input)
        self.assertEqual(ret, input)

    def test_items_as_int(self):
        input = ['id', 3]
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields,
            input)

    def test_items_as_dict(self):
        input = ['id', {}]
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields,
            input)

    def test_items_as_list(self):
        input = ['id', []]
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields,
            input)

    def test_items_as_bool(self):
        input = ['id', True]
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields,
            input)

