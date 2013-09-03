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

from pulp.client.commands.criteria import (CriteriaCommand,
                                           DisplayUnitAssociationsCommand,
                                           UnitAssociationCriteriaCommand)


class TestCriteriaCommand(unittest.TestCase):
    OPTION_NAMES = set(('--limit', '--skip', '--filters', '--fields',
                        '--sort',))
    FG_OPTION_NAMES = set(('--gt', '--gte', '--lt', '--lte', '--not',
                           '--str-eq', '--int-eq', '--match', '--in'))

    def setUp(self):
        self.command = CriteriaCommand(mock.MagicMock())

    def test_name(self):
        self.assertEqual(self.command.name, 'search')

    def test_options_present(self):
        options_present = set([option.name for option in self.command.options])
        self.assertEqual(self.OPTION_NAMES, options_present)

        fg_options_present = set([option.name for option in self.command.option_groups[0].options])
        self.assertEqual(self.FG_OPTION_NAMES, fg_options_present)

    def test_without_filtering(self):
        self.command = CriteriaCommand(mock.MagicMock(), filtering=False)
        self.assertEqual(len(self.command.option_groups), 0)

        options_present = set([option.name for option in self.command.options])
        self.assertTrue('--filters' not in options_present)

    def test_without_criteria(self):
        self.command = CriteriaCommand(mock.MagicMock(), include_search=False)
        self.assertEqual(len(self.command.option_groups), 1)
        options_present = set([option.name for option in self.command.options])
        self.assertEqual(options_present, set(['--filters']))


class TestValidateSort(unittest.TestCase):
    def test_empty(self):
        CriteriaCommand._validate_sort([])

    def test_valid(self):
        CriteriaCommand._validate_sort(['name,descending'])

    def test_missing_field_name(self):
        self.assertRaises(ValueError, CriteriaCommand._validate_sort, [',descending'])

    def test_missing_field_name_after_valid(self):
        self.assertRaises(ValueError, CriteriaCommand._validate_sort,
            ['name,ascending',',descending'])

    def test_missing_both(self):
        self.assertRaises(ValueError, CriteriaCommand._validate_sort, [','])

    def test_invalid_direction(self):
        self.assertRaises(ValueError, CriteriaCommand._validate_sort, ['name,blah'])


class TestParseSort(unittest.TestCase):
    def test_empty(self):
        ret = CriteriaCommand._parse_sort([])
        self.assertEqual(ret, [])

    def test_valid(self):
        DATA = ('name', 'id,descending')
        ret = CriteriaCommand._parse_sort(DATA)
        self.assertEqual(ret, [('name', 'ascending'), ('id', 'descending')])

    def test_invalid_direction(self):
        self.assertRaises(CommandUsage, CriteriaCommand._parse_sort, ('name,blah',))


class TestExplodePieces(unittest.TestCase):
    def test_simple(self):
        field_name, direction = CriteriaCommand._explode_sort_arg_pieces('name,descending')
        self.assertEqual(field_name, 'name')
        self.assertEqual(direction, 'descending')

    def test_default_direction(self):
        field_name, direction = CriteriaCommand._explode_sort_arg_pieces('name')
        self.assertEqual(field_name, 'name')
        self.assertEqual(direction, 'ascending')

    def test_trailing_comma(self):
        field_name, direction = CriteriaCommand._explode_sort_arg_pieces('name,')
        self.assertEqual(field_name, 'name')
        self.assertEqual(direction, 'ascending')


class TestParseKeyValue(unittest.TestCase):
    def test_basic(self):
        ret = CriteriaCommand._parse_key_value(['id=repo1'])
        self.assertEqual(ret, [['id', 'repo1']])

    def test_multiple_equals(self):
        # the second '=' should not be split
        ret = CriteriaCommand._parse_key_value(['id=repo=1'])
        self.assertEqual(ret, [['id', 'repo=1']])

    def test_no_equals(self):
        self.assertRaises(ValueError, CriteriaCommand._parse_key_value, ['idrepo1'])

    def test_multiple_args(self):
        ret = CriteriaCommand._parse_key_value(['id=repo1', 'name=foo'])
        self.assertEqual(ret, [['id', 'repo1'], ['name', 'foo']])


class TestUnitAssociationCriteriaCommand(unittest.TestCase):
    def setUp(self):
        self.command = UnitAssociationCriteriaCommand(mock.MagicMock())

    def test_command_presence(self):
        options_present = set([option.name for option in self.command.options])
        self.assertTrue('--after' in options_present)
        self.assertTrue('--before' in options_present)
        self.assertTrue('--repo-id' in options_present)

    def test_inherits_search(self):
        # make sure this inherits features that were tested elsewhere.
        self.assertTrue(isinstance(self.command, CriteriaCommand))


class TestDisplayUnitAssociationsCommand(unittest.TestCase):
    def setUp(self):
        self.command = DisplayUnitAssociationsCommand(mock.MagicMock())

    def test_command_presence(self):
        options_present = set([option.name for option in self.command.options])
        self.assertTrue('--after' in options_present)
        self.assertTrue('--before' in options_present)
        self.assertTrue('--repo-id' in options_present)
        self.assertTrue('--details' in options_present)

    def test_inherits_search(self):
        # make sure this inherits features that were tested elsewhere.
        self.assertTrue(isinstance(self.command, CriteriaCommand))
