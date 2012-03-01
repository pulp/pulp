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

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + '/../../extensions/')

from repo import pulp_cli

class RepoExtensionTest(unittest.TestCase):

    def test_parse_unknown_args_1(self):
        """
        Simple case where only key/value pairs are specified, no fuplicates, no flags.
        """
        # Test
        args = ['--foo', 'f', '--bar', 'b', '-c', 'c']
        parsed = pulp_cli.parse_unknown_args(args)

        # Verify
        self.assertEqual(3, len(parsed))
        self.assertEqual(parsed['foo'], 'f')
        self.assertEqual(parsed['bar'], 'b')
        self.assertEqual(parsed['c'], 'c')

    def test_parse_unknown_args_2(self):
        """
        Mix of arguments and flags.
        """
        # Test
        args = ['--fus', '--ro', 'r', '--dah']
        parsed = pulp_cli.parse_unknown_args(args)

        # Verify
        self.assertEqual(3, len(parsed))
        self.assertEqual(parsed['fus'], True)
        self.assertEqual(parsed['ro'], 'r')
        self.assertEqual(parsed['dah'], True)

    def test_parse_unknown_args_3(self):
        """
        Multiple values for a single argument.
        """
        # Test
        args = ['--aaa', '1', '-b', '--aaa', '2', '--ccc', 'c']
        parsed = pulp_cli.parse_unknown_args(args)

        # Verify
        self.assertEqual(3, len(parsed))
        self.assertEqual(parsed['aaa'], ['1', '2'])
        self.assertEqual(parsed['b'], True)
        self.assertEqual(parsed['ccc'], 'c')

    def test_parse_unknown_args_empty(self):
        """
        Empty argument list.
        """
        # Test
        parsed = pulp_cli.parse_unknown_args([])

        # Verify
        self.assertTrue(isinstance(parsed, dict))
        self.assertEqual(0, len(parsed))

    def test_parse_unknown_args_fail(self):
        """
        There aren't many invalid argument lists, but if it starts with a value
        instead of an argument, that's bad.
        """
        # Test
        args = ['value', '--key']
        self.assertRaises(pulp_cli.Unparsable, pulp_cli.parse_unknown_args, args)
