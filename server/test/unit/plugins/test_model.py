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

import functools
import unittest

from pulp.plugins.model import Unit, Repository


unit_key_factory = functools.partial(dict, a='foo', b='bar', c=3)
unit_factory = functools.partial(Unit, 'my_type', unit_key_factory(), {}, '')


class TestUnitEquality(unittest.TestCase):
    def test_equal(self):
        unit1 = unit_factory()
        unit2 = unit_factory()
        self.assertEqual(unit1, unit2)

    def test_not_equal(self):
        unit1 = unit_factory()
        unit2 = unit_factory()
        unit2.unit_key = unit_key_factory(a='xyz')
        self.assertNotEqual(unit1, unit2)

    def test_type_id_not_equal(self):
        unit1 = unit_factory()
        unit2 = unit_factory()
        unit2.type_id = 'notthesameasunit1'
        self.assertNotEqual(unit1, unit2)


class TestUnitHash(unittest.TestCase):
    def test_hashequality(self):
        unit1 = unit_factory()
        unit2 = unit_factory()
        self.assertEqual(hash(unit1), hash(unit2))

    def test_hash_inequality(self):
        unit1 = unit_factory()
        unit2 = unit_factory()
        unit2.unit_key = unit_key_factory(a='xyz')
        self.assertNotEqual(hash(unit1), hash(unit2))

    def test_equal_unit_key_instances(self):
        unit1 = unit_factory()
        unit2 = unit_factory()
        # give unit2 a new instance of unit_key
        unit2.unit_key = unit_key_factory()
        self.assertEqual(hash(unit1), hash(unit2))

    def test_type_in_hash(self):
        unit1 = unit_factory()
        unit2 = unit_factory()
        unit2.type_id = 'xyz'
        self.assertNotEqual(hash(unit1), hash(unit2))

    def test_metadata_not_in_hash(self):
        unit1 = unit_factory()
        unit2 = unit_factory()
        unit2.metadata = {'a':'foo'}
        self.assertEqual(hash(unit1), hash(unit2))

    def test_path_not_in_hash(self):
        unit1 = unit_factory()
        unit2 = unit_factory()
        unit2.storage_path = '/foo/bar'
        self.assertEqual(hash(unit1), hash(unit2))

    def test_opposite_values(self):
        # the original algorithm failed this test
        unit1 = unit_factory()
        unit2 = unit_factory()
        # give unit2 a new instance of unit_key with values of "a" and "b"
        # swapped compared to unit1
        unit2.unit_key = unit_key_factory(a=unit1.unit_key['b'], b=unit1.unit_key['a'])
        self.assertNotEqual(hash(unit1), hash(unit2))


class TestRepository(unittest.TestCase):

    def test_init_no_values(self):
        repo = Repository('foo')
        self.assertEquals('foo', repo.id)
        self.assertEquals(None, repo.display_name)
        self.assertEquals(None, repo.description)
        self.assertEquals(None, repo.notes)
        self.assertEquals(None, repo.working_dir)
        self.assertEquals({}, repo.content_unit_counts)
        self.assertEquals(None, repo.last_unit_added)
        self.assertEquals(None, repo.last_unit_removed)

    def test_init_with_values(self):
        repo = Repository('foo',
                          display_name='bar',
                          description='baz',
                          notes={'apple': 'core'},
                          working_dir='wdir',
                          content_unit_counts={'unit': 3},
                          last_unit_added=1,
                          last_unit_removed=2
                          )
        self.assertEquals('foo', repo.id)
        self.assertEquals('bar', repo.display_name)
        self.assertEquals('baz', repo.description)
        self.assertEquals({'apple': 'core'}, repo.notes)
        self.assertEquals('wdir', repo.working_dir)
        self.assertEquals({'unit': 3}, repo.content_unit_counts)
        self.assertEquals(1, repo.last_unit_added)
        self.assertEquals(2, repo.last_unit_removed)

    def test_str(self):
        repo = Repository('foo')
        self.assertEquals('Repository [foo]', str(repo))
