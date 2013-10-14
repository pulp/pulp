#!/usr/bin/python
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

import isodate
from okaara import parsers as okaara_parsers

from pulp.client import parsers


class TestBackwardsCompatibility(unittest.TestCase):

    def test_mapping_to_okaara(self):
        self.assertEqual(parsers.csv, okaara_parsers.parse_csv_string)
        self.assertEqual(parsers.parse_nonnegative_int, okaara_parsers.parse_non_negative_int)
        self.assertEqual(parsers.parse_optional_nonnegative_int,
                         okaara_parsers.parse_optional_non_negative_int)


class TestNotes(unittest.TestCase):
    def test_valid(self):
        ret = parsers.parse_notes(['a=z', 'b=y'])
        self.assertEqual(ret, {'a' : 'z', 'b' : 'y'})

    def test_invalid(self):
        self.assertRaises(ValueError, parsers.parse_notes, 'foo')


class TestISO8601(unittest.TestCase):
    def test_type_error(self):
        self.assertRaises(TypeError, parsers.iso8601, 123)

    def test_date(self):
        ret = parsers.iso8601('2012-03-15')
        self.assertTrue(isinstance(ret, basestring))
        # make sure the returned value can be parsed
        isodate.parse_datetime(ret)

    def test_datetime(self):
        ret = parsers.iso8601('2012-03-15')
        self.assertTrue(isinstance(ret, basestring))
        # make sure the returned value can be parsed
        isodate.parse_datetime(ret)

    def test_value_error(self):
        self.assertRaises(ValueError, parsers.iso8601, 'abcde')


class TestKeyCSV(unittest.TestCase):
    def test_single_value(self):
        ret = parsers.key_csv('x=foo')
        self.assertEqual(ret, ('x', ['foo']))

    def test_multiple_values(self):
        ret = parsers.key_csv('x=foo,bar,stuff')
        self.assertEqual(ret, ('x', ['foo', 'bar', 'stuff']))

    def test_no_value(self):
        ret = parsers.key_csv('x=')
        self.assertEqual(ret, ('x', []))

    def test_quote_a_comma(self):
        ret = parsers.key_csv('x=foo,"ba,r"')
        self.assertEqual(ret, ('x', ['foo', 'ba,r']))

    def test_no_equals_sign(self):
        self.assertRaises(ValueError, parsers.key_csv, 'x')


class TestKeyCSVMultiple(unittest.TestCase):
    def test_none(self):
        ret = parsers.key_csv_multiple(None)
        self.assertEqual(ret, [])

    def test_multiple_statements(self):
        ret = parsers.key_csv_multiple(['x=foo', 'y=bar'])
        self.assertEqual(ret, [('x', ['foo']), ('y', ['bar'])])

    def test_no_equals_sign(self):
        self.assertRaises(ValueError, parsers.key_csv_multiple, ['x'])


class TestKeyValueMultiple(unittest.TestCase):
    def test_one_value(self):
        ret = parsers.key_value_multiple(['x=foo'])
        self.assertEqual(ret, [['x', 'foo']])

    def test_multiple_values(self):
        ret = parsers.key_value_multiple(['x=foo', 'y=bar'])
        self.assertEqual(ret, [['x', 'foo'], ['y', 'bar']])

    def test_no_equals_sign(self):
        self.assertRaises(ValueError, parsers.key_value_multiple, ['x'])

    def test_none(self):
        ret = parsers.key_value_multiple(None)
        self.assertEqual(ret, [])


class ParserEmptyStringTests(unittest.TestCase):

    def test_parse_positive_int(self):
        self.assertEquals(5, parsers.pulp_parse_optional_positive_int('5'))

    def test_parse_positive_int_empty(self):
        self.assertEquals('', parsers.pulp_parse_optional_positive_int(''))

    def test_parse_positive_int_none(self):
        self.assertEquals('', parsers.pulp_parse_optional_positive_int(None))

    def test_parse_optional_boolean(self):
        self.assertEquals(True, parsers.pulp_parse_optional_boolean('true'))

    def test_parse_optional_boolean_empty(self):
        self.assertEquals('', parsers.pulp_parse_optional_boolean(''))

    def test_parse_optional_boolean_none(self):
        self.assertEquals('', parsers.pulp_parse_optional_boolean(None))

    def test_parse_optional_nonnegative_int(self):
        self.assertEquals(0, parsers.pulp_parse_optional_nonnegative_int('0'))

    def test_parse_optional_nonnegative_int_empty(self):
        self.assertEquals('', parsers.pulp_parse_optional_nonnegative_int(''))

    def test_parse_optional_nonnegative_int_none(self):
        self.assertEquals('', parsers.pulp_parse_optional_nonnegative_int(None))