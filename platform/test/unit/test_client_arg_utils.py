# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 Red Hat, Inc.
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

from pulp.client import arg_utils


class TestArgToBool(unittest.TestCase):
    """
    This class tests the pulp.client.arg_utils.arg_to_bool function, which takes a str and returns the
    bool equivalent, or None if it is not True or False.
    """

    def test_true(self):
        # Setup
        test_list = [' true ', ' TRUE', 'True ']

        # Test that all the test list values are evaluated to True
        for item in test_list:
            self.assertTrue(arg_utils.arg_to_bool(item))

    def test_false(self):
        # Setup
        test_list = [' false ', ' FALSE', 'False ']

        # Test that all the test list values are evaluated to False
        for item in test_list:
            self.assertFalse(arg_utils.arg_to_bool(item))

    def test_invalid_bool(self):
        # Setup
        test_list = ['f', 't', 'potato']

        # Test that values that are neither true nor false return None
        for item in test_list:
            self.assertTrue(arg_utils.arg_to_bool(item) is None)


class TestArgsToNotesDict(unittest.TestCase):
    """
    This class tests the pulp.client.arg_utils.args_to_notes_dict function, which takes a list of notes
    in the format 'key=value' and a boolean which determines whether None is a valid value
    """

    def test_include_none_true(self):
        """
        Tests to make sure keys with null values are returned with a value
        of None
        """
        # Setup
        test_list = ['key=value', 'key2=', 'key3=""']

        # Test
        result = arg_utils.args_to_notes_dict(test_list, include_none=True)
        self.assertTrue('key' in result)
        self.assertEqual(result['key'], 'value')
        self.assertTrue('key2' in result)
        self.assertTrue(result['key2'] is None)
        self.assertTrue('key3' in result)
        self.assertTrue(result['key3'] is None)

    def test_include_none_false(self):
        """
        Tests to make sure keys with null values are not returned when include_none=False
        """
        # Setup
        test_list = ['key=value', 'key2=', 'key3=""']

        # Test
        result = arg_utils.args_to_notes_dict(test_list, include_none=False)
        self.assertTrue('key' in result)
        self.assertEqual(result['key'], 'value')
        self.assertFalse('key2' in result)
        self.assertFalse('key3' in result)

    def test_null_key(self):
        """
        Tests to make sure null keys are not allowed
        """
        # Setup
        test_list = ['=value', '""=value', "''=value"]

        # Assert all the notes in the test list raise exceptions
        for note in test_list:
            self.assertRaises(arg_utils.InvalidConfig, arg_utils.args_to_notes_dict, note)

    def test_invalid_format(self):
        """
        Notes are expected to be in the format 'key=value'
        """
        test_list = ['not_a_note', 'incorrect format']

        # Assert all the notes in the test list raise exceptions
        self.assertRaises(arg_utils.InvalidConfig, arg_utils.args_to_notes_dict, test_list)
