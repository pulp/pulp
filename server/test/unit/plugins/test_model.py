"""
This module contains tests for pulp.plugins.model.
"""
import datetime
import functools
import unittest

import mock

from pulp.common import dateutils
from pulp.plugins.model import Unit, Repository
from pulp.server import constants


unit_key_factory = functools.partial(dict, a='foo', b='bar', c=3)
unit_factory = functools.partial(Unit, 'my_type', unit_key_factory(), {}, '')


class TestUnit(unittest.TestCase):
    """
    This class contains tests for the Unit class.
    """
    def test___init___adds_user_metadata(self):
        """
        Ensure that the __init__() method adds the pulp_user_metadata field if it is not present in
        the supplied metadata.
        """
        type_id = 'some_type'
        unit_key = {'some': 'key'}
        metadata = {'some': 'metadata'}
        storage_path = '/some/path'

        u = Unit(type_id, unit_key, metadata, storage_path)

        self.assertEqual(u.metadata,
                         {'some': 'metadata', constants.PULP_USER_METADATA_FIELDNAME: {}})

    def test___init___ignores_existing_user_metadata(self):
        """
        Ensure that __init__() leaves existing pulp_user_metadata fields alone if they are already
        present in the supplied metadata.
        """
        type_id = 'some_type'
        unit_key = {'some': 'key'}
        metadata = {'some': 'metadata',
                    constants.PULP_USER_METADATA_FIELDNAME: {'user': 'metadata'}}
        storage_path = '/some/path'

        u = Unit(type_id, unit_key, metadata, storage_path)

        # The metadata should not have been altered
        self.assertEqual(u.metadata, metadata)


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
        unit2.metadata = {'a': 'foo'}
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

    @mock.patch('pulp.plugins.model.Repository._ensure_tz_specified')
    def test_init_with_values(self, mock_tz):
        """
        Make sure that the repo contains the appropriate values following initialization.
        """
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
        self.assertTrue(repo.last_unit_added is mock_tz.return_value)
        self.assertTrue(repo.last_unit_removed is mock_tz.return_value)
        mock_tz.assert_has_calls([mock.call(1), mock.call(2)])

    def test_ensure_tz_not_specified(self):
        """
        Make sure that a date without a timezone is given one.
        """
        dt = datetime.datetime.utcnow()
        new_date = Repository._ensure_tz_specified(dt)
        self.assertEquals(new_date.tzinfo, dateutils.utc_tz())

    def test_ensure_tz_none_object(self):
        """
        Test _ensure_tz_specified with None.
        """
        dt = None
        new_date = Repository._ensure_tz_specified(dt)
        self.assertEquals(new_date, None)

    def test_ensure_tz_specified(self):
        """
        If the timezone is specified, the result should be the same.
        """
        dt = datetime.datetime.now(dateutils.local_tz())
        new_date = Repository._ensure_tz_specified(dt)
        self.assertEquals(new_date.tzinfo, dateutils.utc_tz())

    def test_str(self):
        repo = Repository('foo')
        self.assertEquals('Repository [foo]', str(repo))
