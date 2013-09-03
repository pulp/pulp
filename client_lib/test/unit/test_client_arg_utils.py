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
import mock

from pulp.client import arg_utils


class TestConvertRemovedOptions(unittest.TestCase):
    """
    Tests pulp.client.arg_utils.convert_removed_options, which strips out any keys with a None value,
    and then converts any keys with a value of "" to None
    """

    def test_non_empty_values(self):
        # Setup
        args = {'key1': 'real_val', 'key2': 'another_val'}
        original_args = args.copy()

        # Test to make sure none of the keys or values are touched
        arg_utils.convert_removed_options(args)
        self.assertEqual(args, original_args)

    def test_null_values(self):
        # Setup
        args = {'key1': None}

        # Assert that all the args with a value of None are removed
        arg_utils.convert_removed_options(args)
        self.assertEqual({}, args)

    def test_empty_value(self):
        # Setup
        args = {'key1': ''}

        # Assert that args with a '' value are converted to None
        arg_utils.convert_removed_options(args)
        self.assertTrue(args['key1'] is None)


class TestConvertBooleanArguments(unittest.TestCase):
    """
    Tests pulp.client.arg_utils.convert_boolean_arguments, which takes a list or tuple of keys, and an
    args dict, which is then converted from strings to boolean values
    """

    def test_valid_input(self):
        # Setup
        key_list = ['key1', 'key2', 'key3']
        args = {'key1': 'false', 'key2': 'FALSE', 'key3': 'true'}

        # Test that the boolean equivalents were written to args
        arg_utils.convert_boolean_arguments(key_list, args)
        self.assertFalse(args['key1'])
        self.assertFalse(args['key2'])
        self.assertTrue(args['key3'])

    def test_key_not_in_args(self):
        # Setup
        key_list = ['key1', 'key2']
        args = {'other_key1': 'false', 'other_key2': 'true'}
        original_args = args.copy()

        # Assert no keys got changed
        arg_utils.convert_boolean_arguments(key_list, args)
        self.assertEqual(args, original_args)

    @mock.patch('pulp.client.arg_utils.arg_to_bool', autospec=True)
    def test_args_value_none(self, mock_arg_to_bool):
        # Setup
        key_list = ['key1', 'key2']
        args = {'key1': None, 'key2': None}

        # Assert arg_to_bool is never called
        arg_utils.convert_boolean_arguments(key_list, args)
        self.assertEqual(0, mock_arg_to_bool.call_count)

    def test_non_boolean_values(self):
        """
        Tests that when a value that can't be converted to true or false is given, an
        arg_utils.InvalidConfig is raised
        """
        # Setup
        key_list = ['key1', 'key2']
        args = {'key1': 'maybe', 'key2': 'truish'}

        # Assert InvalidConfig is raised
        self.assertRaises(arg_utils.InvalidConfig, arg_utils.convert_boolean_arguments, key_list, args)


class TestConvertFileContents(unittest.TestCase):
    """
    This class tests the pulp.client.arg_utils.convert_file_contents function, which takes a list or
    tuple of keys to read in as files and a dict of key-value pairs to convert (may include keys not
    in the file_keys list). The file is then written to the value of the dict for each key in the list.
    """

    @mock.patch('__builtin__.open', autospec=True)
    def test_keys_in_args(self, mock_open):
        """
        Tests that when a key is in the the arg dict (and the arg[key] is not none), the function
        attempts to open the file
        """
        # Setup
        file_keys = ('key1', 'key2')
        args = {'key1': 'filename1', 'key2': 'filename2', 'key3': 'filename3'}
        # Mock a file for mock_open to return, and a return value for the read call
        mock_file = mock.MagicMock(spec=file)
        mock_file.read.return_value = 'Fake return to a read call'
        mock_open.return_value = mock_file

        # Call convert_file_contents and assert open was called 3 times with the correct filename
        arg_utils.convert_file_contents(file_keys, args)
        self.assertEqual(2, mock_open.call_count)
        self.assertEqual(mock_open.call_args_list[0][0], ('filename1',))
        self.assertEqual(mock_open.call_args_list[1][0], ('filename2',))
        # Assert that read's return value was placed in the args dict
        self.assertEqual(args['key1'], mock_file.read.return_value)
        self.assertEqual(args['key2'], mock_file.read.return_value)
        self.assertEqual(args['key3'], 'filename3')

    @mock.patch('__builtin__.open', autospec=True)
    def test_keys_not_in_args(self, mock_open):
        """
        Tests that when a key is not in the args dict, nothing is done
        """
        # Setup
        file_keys = ('key1', 'key2')
        args = {'other_key1': 'file2', 'other_key2': 'file2'}

        # Call convert_file_contents and assert open was never called
        arg_utils.convert_file_contents(file_keys, args)
        self.assertEqual(0, mock_open.call_count)

    @mock.patch('__builtin__.open', autospec=True)
    def test_args_key_is_none(self, mock_open):
        """
        Tests that when the args[key] is none, the function does not attempt to open the file
        """
        # Setup
        file_keys = ('key1', 'key2')
        args = {'key1': None, 'key2': None}

        # Call convert_file_contents and assert open was never called
        arg_utils.convert_file_contents(file_keys, args)
        self.assertEqual(0, mock_open.call_count)

    @mock.patch('__builtin__.open', autospec=True)
    def test_unreadable_file(self, mock_open):
        """
        Tests that when a file fails to open an InvalidConfig exception is raised
        """
        # Setup
        file_keys = ('key1',)
        args = {'key1': 'filename1'}
        mock_open.side_effect = IOError('Oh no!')

        # Call convert_file_contents and assert the IOError is caught and a InvalidConfig is raised
        self.assertRaises(arg_utils.InvalidConfig, arg_utils.convert_file_contents, file_keys, args)


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

    def test_dict_arg(self):
        """
        Tests to make sure that attempting to parse a dict returns the dict
        """
        # Setup
        test_dict = {'key': 'value', 'key2': 'value2'}

        # Test
        result = arg_utils.args_to_notes_dict(test_dict)
        self.assertTrue(test_dict is result)
