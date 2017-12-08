from random import randrange

from django.db import IntegrityError
from django.test import TestCase

from pulpcore.app.models import generic, Repository


class GenericMutableMappingTestCase(TestCase):
    def _gen_notes(self, name):
        # Generate an instance of a generic key/value store attached to a single test model
        instance = Repository(name=name)
        instance.save()
        return instance.notes

    def setUp(self):
        # can use any model with a GenericKeyValueMapping relation (e.g. notes/config)
        self.notes = self._gen_notes('test instance')

    def test_mapping_types(self):
        # the notes field is an instance of our custom manager
        self.assertTrue(isinstance(self.notes, generic.GenericKeyValueManager))

        # the custom manager provides the mapping attr of the correct type
        self.assertTrue(isinstance(self.notes.mapping, generic.GenericKeyValueMutableMapping))

    def test_contraints(self):
        # ensure that the DB constraints don't allow for duplicate keys in a single dict
        self.notes.create(key='key', value='value')

        with self.assertRaises(IntegrityError):
            self.notes.create(key='key', value='value')

    def test_mapping_interface_setget(self):
        # go through basic set and get
        self.notes.mapping['key'] = 'value'
        self.assertEqual(self.notes.mapping['key'], 'value')
        self.assertEqual(self.notes.count(), 1)

        # this is what getting a value looks like without the mapping interface :)
        self.assertEqual(self.notes.get(key='key').value, 'value')

    def test_mapping_interface_len(self):
        num_keys = randrange(10)
        for i in range(num_keys):
            self.notes.mapping['key{}'.format(i)] = 'value'
        self.assertEqual(self.notes.count(), num_keys)
        self.assertEqual(self.notes.count(), len(self.notes.mapping))

    def test_mapping_interface_duplicate_key(self):
        self.notes.mapping['key'] = 'value'
        self.assertEqual(self.notes.mapping['key'], 'value')

        self.notes.mapping['key'] = 'newvalue'
        self.assertEqual(self.notes.mapping['key'], 'newvalue')

    def test_mapping_interface_update(self):
        self.notes.mapping.update({'key1': 'value1', 'key2': 'value2'})
        self.assertEqual(self.notes.count(), 2)
        self.assertEqual(self.notes.mapping['key1'], 'value1')
        self.assertEqual(self.notes.mapping['key2'], 'value2')

    def test_mapping_interface_keys(self):
        self.notes.mapping.update({'key1': 'value1', 'key2': 'value2'})
        self.assertTrue('key1' in self.notes.mapping.keys())
        self.assertTrue('key2' in self.notes.mapping.keys())

    def test_mapping_interface_values(self):
        self.notes.mapping.update({'key1': 'value1', 'key2': 'value2'})
        self.assertTrue('value1' in self.notes.mapping.values())
        self.assertTrue('value2' in self.notes.mapping.values())

    def test_mapping_interface_items(self):
        self.notes.mapping['key'] = 'value'
        items = list(self.notes.mapping.items())
        self.assertEqual(items, [('key', 'value')])

    def test_mapping_interface_clear(self):
        self.notes.mapping['key'] = 'value'
        self.notes.mapping.clear()
        self.assertEqual(self.notes.count(), 0)

    def test_instance_local_keys(self):
        new_instance_notes = self._gen_notes('second instance')

        # ensure that the generic k/v relations are local to a single instance
        self.notes.mapping['key'] = 'value'
        self.assertIn('key', self.notes.mapping)
        self.assertNotIn('key', new_instance_notes.mapping)

    def test_keyerror_get(self):
        with self.assertRaises(KeyError):
            self.notes.mapping['key']

    def test_keyerror_del(self):
        with self.assertRaises(KeyError):
            del(self.notes.mapping['key'])

    def test_repr(self):
        # keeping coverage happy :)
        self.notes.mapping['key'] = 'value'
        self.assertEqual(repr(self.notes.mapping), "Notes({'key': 'value'})")
