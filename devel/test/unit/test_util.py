# -*- coding: utf-8 -*-
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
from xml.etree import ElementTree

from pulp.devel.unit import util


class TestCompareDic(unittest.TestCase):

    def test_compare_dict_equality(self):
        """
        Tests the correct API in the bindings is replaced by the simulator.
        """
        source = {'foo': 'bar', 'baz': 'qux'}
        util.compare_dict(source, source)

    def test_compare_dict_inequality_keys(self):
        """
        Tests the correct API in the bindings is replaced by the simulator.
        """
        source = {'foo': 'bar', 'baz': 'qux'}
        target = {'quack': 'duck'}
        self.assertRaises(AssertionError, util.compare_dict, source, target)

    def test_compare_dict_inequality_values(self):
        """
        Tests the correct API in the bindings is replaced by the simulator.
        """
        source = {'foo': 'bar', 'baz': 'qux'}
        target = {'foo': 'bar', 'baz': 'duck'}
        self.assertRaises(AssertionError, util.compare_dict, source, target)

    def test_compare_dict_source_not_dict(self):
        """
        Tests the correct API in the bindings is replaced by the simulator.
        """
        source = 'foo'
        target = {'foo': 'bar', 'baz': 'duck'}
        self.assertRaises(AssertionError, util.compare_dict, source, target)

    def test_compare_dict_target_not_dict(self):
        """
        Tests the correct API in the bindings is replaced by the simulator.
        """
        source = {'foo': 'bar', 'baz': 'qux'}
        target = 'bar'
        self.assertRaises(AssertionError, util.compare_dict, source, target)


class TestCompareEtree(unittest.TestCase):

    def test_compare_element_equality(self):
        source_string = '<foo alpha="bar">some text <baz></baz></foo>'
        source = ElementTree.fromstring(source_string)
        target = ElementTree.fromstring(source_string)
        util.compare_element(source, target)

    def test_compare_element_inequality_tags(self):
        source_string = '<foo></foo>'
        target_string = '<bar></bar>'
        source = ElementTree.fromstring(source_string)
        target = ElementTree.fromstring(target_string)
        self.assertRaises(AssertionError, util.compare_element, source, target)

    def test_compare_element_inequality_text(self):
        source_string = '<foo>alpha</foo>'
        target_string = '<foo>beta</foo>'
        source = ElementTree.fromstring(source_string)
        target = ElementTree.fromstring(target_string)
        self.assertRaises(AssertionError, util.compare_element, source, target)

    def test_compare_element_inequality_keys(self):
        source_string = '<foo alpha="bar"></foo>'
        target_string = '<foo beta="bar"></foo>'
        source = ElementTree.fromstring(source_string)
        target = ElementTree.fromstring(target_string)
        self.assertRaises(AssertionError, util.compare_element, source, target)

    def test_compare_element_inequality_values(self):
        source_string = '<foo alpha="bar"></foo>'
        target_string = '<foo alpha="foo"></foo>'
        source = ElementTree.fromstring(source_string)
        target = ElementTree.fromstring(target_string)
        self.assertRaises(AssertionError, util.compare_element, source, target)

    def test_compare_element_source_not_element(self):
        source_string = '<foo alpha="bar"></foo>'
        target_string = '<foo alpha="foo"></foo>'
        target = ElementTree.fromstring(target_string)
        self.assertRaises(AssertionError, util.compare_element, source_string, target)

    def test_compare_element_target_not_element(self):
        source_string = '<foo alpha="bar"></foo>'
        target_string = '<foo alpha="foo"></foo>'
        source = ElementTree.fromstring(source_string)
        self.assertRaises(AssertionError, util.compare_element, source, target_string)

    def test_compare_element_child_different(self):
        source_string = '<foo alpha="bar">some text <baz>qux</baz></foo>'
        target_string = '<foo alpha="bar">some text <baz>zap</baz></foo>'
        source = ElementTree.fromstring(source_string)
        target = ElementTree.fromstring(target_string)
        self.assertRaises(AssertionError, util.compare_element, source, target)

    def test_compare_element_child_different_number(self):
        source_string = '<foo alpha="bar">some text <baz>qux</baz></foo>'
        target_string = '<foo alpha="bar">some text <baz>zap</baz><fuz></fuz></foo>'
        source = ElementTree.fromstring(source_string)
        target = ElementTree.fromstring(target_string)
        self.assertRaises(AssertionError, util.compare_element, source, target)

