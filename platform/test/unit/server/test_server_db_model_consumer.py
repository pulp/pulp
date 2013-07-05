# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
This module contains tests for the pulp.server.db.model.consumer module.
"""

from copy import deepcopy
import math
import unittest

import mock

from pulp.server.db.model import consumer


class TestUnitProfile(unittest.TestCase):
    """
    Test the UnitProfile class.
    """
    def test___hash___different_profiles(self):
        """
        Test that two different profiles have different hashes.
        """
        profile_1 = consumer.UnitProfile('consumer_1', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'perl-Filter', 'epoch': 0, 'version': '1.49',
             'release': '1.fc18',   'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'python-slip-dbus', 'epoch': 0, 'version': '0.4.0',
             'release': '1.fc18', 'arch': 'noarch'},
            {'vendor': 'Fedora Project', 'name': 'kmod', 'epoch': 0, 'version': '12',
             'release': '3.fc18', 'arch': 'x86_64'}])
        profile_2 = consumer.UnitProfile('consumer_2', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'libestr',  'epoch': 0, 'version': '0.1.5',
             'release': '1.fc18', 'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'openssh-clients', 'epoch': 0, 'version': '6.1p1',
             'release': '8.fc18', 'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'procps-ng', 'epoch': 0, 'version': '3.3.3',
             'release': '4.20120807git.fc18', 'arch': 'x86_64'}])

        self.assertNotEqual(hash(profile_1), hash(profile_2))

    def test___hash___identical_profiles(self):
        """
        Test that the hashes of two identical profiles are equal.
        """
        profile_1 = consumer.UnitProfile('consumer_1', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'perl-Filter', 'epoch': 0, 'version': '1.49',
             'release': '1.fc18',   'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'python-slip-dbus', 'epoch': 0, 'version': '0.4.0',
             'release': '1.fc18', 'arch': 'noarch'},
            {'vendor': 'Fedora Project', 'name': 'kmod', 'epoch': 0, 'version': '12',
             'release': '3.fc18', 'arch': 'x86_64'}])
        profile_2 = consumer.UnitProfile('consumer_2', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'perl-Filter', 'epoch': 0, 'version': '1.49',
             'release': '1.fc18',   'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'python-slip-dbus', 'epoch': 0, 'version': '0.4.0',
             'release': '1.fc18', 'arch': 'noarch'},
            {'vendor': 'Fedora Project', 'name': 'kmod', 'epoch': 0, 'version': '12',
             'release': '3.fc18', 'arch': 'x86_64'}])

        self.assertEqual(hash(profile_1), hash(profile_2))

    def test___hash___reordered_profiles(self):
        """
        Test that the hashes of two equivalent, but differently ordered profile lists are not the same.
        """
        profile_1 = consumer.UnitProfile('consumer_1', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'perl-Filter', 'epoch': 0, 'version': '1.49',
             'release': '1.fc18',   'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'python-slip-dbus', 'epoch': 0, 'version': '0.4.0',
             'release': '1.fc18', 'arch': 'noarch'},
            {'vendor': 'Fedora Project', 'name': 'kmod', 'epoch': 0, 'version': '12',
             'release': '3.fc18', 'arch': 'x86_64'}])
        profile_2 = consumer.UnitProfile('consumer_2', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'python-slip-dbus', 'epoch': 0, 'version': '0.4.0',
             'release': '1.fc18', 'arch': 'noarch'},
            {'vendor': 'Fedora Project', 'name': 'perl-Filter', 'epoch': 0, 'version': '1.49',
             'release': '1.fc18',   'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'kmod', 'epoch': 0, 'version': '12',
             'release': '3.fc18', 'arch': 'x86_64'}])

        self.assertNotEqual(hash(profile_1), hash(profile_2))

    def test___hash___similar_profiles(self):
        """
        Test hashing "similar" profiles to make sure they get different results.
        """
        profile_1 = consumer.UnitProfile('consumer_1', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'perl-Filter', 'epoch': 0, 'version': '1.49',
             'release': '1.fc18',   'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'python-slip-dbus', 'epoch': 0, 'version': '0.4.0',
             'release': '1.fc18', 'arch': 'noarch'},
            {'vendor': 'Fedora Project', 'name': 'kmod', 'epoch': 0, 'version': '12',
             'release': '3.fc18', 'arch': 'x86_64'}])
        # profile_2 is almost the same as profile_1, but it has a different release on the python-slip-dbus
        # package
        profile_2 = consumer.UnitProfile('consumer_2', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'perl-Filter', 'epoch': 0, 'version': '1.49',
             'release': '1.fc18',   'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'python-slip-dbus', 'epoch': 0, 'version': '0.4.0',
             'release': '2.fc18', 'arch': 'noarch'},
            {'vendor': 'Fedora Project', 'name': 'kmod', 'epoch': 0, 'version': '12',
             'release': '3.fc18', 'arch': 'x86_64'}])

        self.assertNotEqual(hash(profile_1), hash(profile_2))

    @mock.patch('pulp.server.db.model.consumer.Model.__init__', side_effect=consumer.Model.__init__,
                autospec=True)
    def test___init__(self, __init__):
        """
        Test the constructor.
        """
        profile = consumer.UnitProfile('consumer_id', 'content_type', 'profile')

        self.assertEqual(profile.consumer_id, 'consumer_id')
        self.assertEqual(profile.content_type, 'content_type')
        self.assertEqual(profile.profile, 'profile')
        self.assertEqual(profile.profile_hash, hash(profile.profile))

        # The superclass __init__ should have been called
        __init__.assert_called_once_with(profile)

    @mock.patch('pulp.server.db.model.consumer.Model.__init__', side_effect=consumer.Model.__init__,
                autospec=True)
    def test___init___with_hash(self, __init__):
        """
        Test the constructor, passing the optional profile_hash
        """
        profile = consumer.UnitProfile('consumer_id', 'content_type', 'profile', 'profile_hash')

        self.assertEqual(profile.consumer_id, 'consumer_id')
        self.assertEqual(profile.content_type, 'content_type')
        self.assertEqual(profile.profile, 'profile')
        self.assertEqual(profile.profile_hash, 'profile_hash')

        # The superclass __init__ should have been called
        __init__.assert_called_once_with(profile)

    def test__convert_to_hashable_basic_types(self):
        """
        Assert that _convert_to_hashable() does not alter basic types, such as ints and strings.
        """
        self.assertEqual(consumer.UnitProfile._convert_to_hashable(42), 42)
        self.assertEqual(consumer.UnitProfile._convert_to_hashable(math.pi), math.pi)
        self.assertEqual(consumer.UnitProfile._convert_to_hashable('Hello, World!'), 'Hello, World!')
        self.assertEqual(consumer.UnitProfile._convert_to_hashable(False), False)
        self.assertTrue(consumer.UnitProfile._convert_to_hashable(None) is None)

    def test__convert_to_hashable_dict(self):
        """
        Assert that _convert_to_hashable() correctly converts dictionaries into frozensets.
        """
        test_dict = {'an int': 42, 'a string': u'Heyó', 'true?': False}

        hashable_dict = consumer.UnitProfile._convert_to_hashable(test_dict)

        expected_frozenset = frozenset([('an int', 42), ('a string', u'Heyó'), ('true?', False)])
        self.assertEqual(hashable_dict, expected_frozenset)
        self.assertEqual(hash(hashable_dict), hash(expected_frozenset))

    def test__convert_to_hashable_dict_of_lists(self):
        """
        Assert that _convert_to_hashable() correctly converts dictionaries of lists into frozensets of tuples.
        """
        test_dict = {'an int': 42, 'a string': u'Heyó', 'true?': False, 'a list': ['here is a thing', 88],
                     'another list': [{'a': 'dictionary'}, 'Alright, I think this is good enough.']}

        hashable_dict = consumer.UnitProfile._convert_to_hashable(test_dict)

        expected_frozenset = frozenset(
            [('an int', 42), ('a string', u'Heyó'), ('true?', False), ('a list', ('here is a thing', 88)),
             ('another list', (frozenset([('a', 'dictionary')]), 'Alright, I think this is good enough.'))])
        self.assertEqual(hashable_dict, expected_frozenset)
        self.assertEqual(hash(hashable_dict), hash(expected_frozenset))

    def test__convert_to_hashable_empty_dict(self):
        """
        Assert that _convert_to_hashable() correctly converts empty dictionaries into frozensets.
        """
        hashable_dict = consumer.UnitProfile._convert_to_hashable({})

        expected_frozenset = frozenset([])
        self.assertEqual(hashable_dict, expected_frozenset)
        self.assertEqual(hash(hashable_dict), hash(expected_frozenset))

    def test__convert_to_hashable_empty_list(self):
        """
        Assert that _convert_to_hashable() correctly converts empty lists into tuples.
        """
        hashable_list = consumer.UnitProfile._convert_to_hashable([])

        expected_tuple = tuple()
        self.assertEqual(hashable_list, expected_tuple)
        self.assertEqual(hash(hashable_list), hash(expected_tuple))

    def test__convert_to_hashable_list(self):
        """
        Assert that _convert_to_hashable() correctly converts lists into tuples.
        """
        test_list = [1, 2, 3, 'hello', True]

        hashable_list = consumer.UnitProfile._convert_to_hashable(test_list)

        expected_tuple = (1, 2, 3, 'hello', True)
        self.assertEqual(hashable_list, expected_tuple)
        self.assertEqual(hash(hashable_list), hash(expected_tuple))

    def test__convert_to_hashable_list_of_dicts(self):
        """
        Assert that _convert_to_hashable() correctly converts lists of dicts into tuples of frozensets.
        """
        test_list = [1, {'a': 'dictionary'}, {'another dictionary': 'with a list', 'a list': [1, 2, 3]}]

        hashable_list = consumer.UnitProfile._convert_to_hashable(test_list)

        expected_tuple = (1, frozenset([('a', 'dictionary')]),
                          frozenset([('another dictionary', 'with a list'), ('a list', (1, 2, 3))]))
        self.assertEqual(hashable_list, expected_tuple)
        self.assertEqual(hash(hashable_list), hash(expected_tuple))

    def test__convert_to_hashable_unaltered_dict(self):
        """
        Assert that _convert_to_hashable() does not alter the reference passed to it.
        """
        test_dict = {'an int': 42, 'a string': u'Heyó', 'true?': False, 'a list': ['here is a thing', 88],
                     'another list': [{'a': 'dictionary'}, 'Alright, I think this is good enough.']}
        dict_copy = deepcopy(test_dict)

        consumer.UnitProfile._convert_to_hashable(dict_copy)

        self.assertEqual(test_dict, dict_copy)

    def test__convert_to_hashable_unaltered_list(self):
        """
        Assert that _convert_to_hashable() does not alter the reference passed to it.
        """
        test_list = [1, {'a': 'dictionary'}, {'another dictionary': 'with a list', 'a list': [1, 2, 3]}]
        list_copy = deepcopy(test_list)

        consumer.UnitProfile._convert_to_hashable(list_copy)

        self.assertEqual(test_list, list_copy)
