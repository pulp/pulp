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

from pulp.client.search import SearchCommand

class TestSearchCommand(unittest.TestCase):
    def setUp(self):
        self.command = SearchCommand(mock.MagicMock)

    def test_name(self):
        self.assertEqual(self.command.name, 'search')

    def test_options_present(self):
        OPTION_NAMES = set(('--limit', '--skip', '--filters', '--fields',
                            '--sort',))
        FG_OPTION_NAMES = set(('--gt', '--gte', '--lt', '--lte', '--not',
                               '--str-eq', '--int-eq', '--match', '--in'))

        options_present = set([option.name for option in self.command.options])
        self.assertEqual(OPTION_NAMES, options_present)

        fg_options_present = set([option.name for option in self.command.option_groups[0].options])
        self.assertEqual(FG_OPTION_NAMES, fg_options_present)


class TestValidateSort(unittest.TestCase):
    def test_empty(self):
        SearchCommand._validate_sort([])

    def test_valid(self):
        SearchCommand._validate_sort(['name,descending'])

    def test_missing_field_name(self):
        self.assertRaises(ValueError, SearchCommand._validate_sort, [',descending'])

    def test_missing_field_name_after_valid(self):
        self.assertRaises(ValueError, SearchCommand._validate_sort,
            ['name,ascending',',descending'])

    def test_missing_both(self):
        self.assertRaises(ValueError, SearchCommand._validate_sort, [','])

    def test_invalid_direction(self):
        self.assertRaises(ValueError, SearchCommand._validate_sort, ['name,blah'])


class TestParseSort(unittest.TestCase):
    def test_empty(self):
        ret = SearchCommand._parse_sort([])
        self.assertEqual(ret, [])

    def test_valid(self):
        DATA = ('name', 'id,descending')
        ret = SearchCommand._parse_sort(DATA)
        self.assertEqual(ret, [('name', 'ascending'), ('id', 'descending')])

    def test_invalid_direction(self):
        self.assertRaises(CommandUsage, SearchCommand._parse_sort, ('name,blah',))


class TestExplodePieces(unittest.TestCase):
    def test_simple(self):
        field_name, direction = SearchCommand._explode_sort_arg_pieces('name,descending')
        self.assertEqual(field_name, 'name')
        self.assertEqual(direction, 'descending')

    def test_default_direction(self):
        field_name, direction = SearchCommand._explode_sort_arg_pieces('name')
        self.assertEqual(field_name, 'name')
        self.assertEqual(direction, 'ascending')

    def test_trailing_comma(self):
        field_name, direction = SearchCommand._explode_sort_arg_pieces('name,')
        self.assertEqual(field_name, 'name')
        self.assertEqual(direction, 'ascending')

