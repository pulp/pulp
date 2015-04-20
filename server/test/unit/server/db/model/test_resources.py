"""
This module contains tests for the pulp.server.db.model.resources module.
"""
import unittest

from mongoengine import Document, StringField

from pulp.server.db.model import resources


class TestReservedResource(unittest.TestCase):

    def test_model_superclass(self):
        sample_model = resources.ReservedResource()
        self.assertTrue(isinstance(sample_model, Document))

    def test_attributes(self):
        self.assertTrue(isinstance(resources.ReservedResource.task_id, StringField))
        self.assertEqual(resources.ReservedResource.task_id.primary_key, True)
        self.assertEqual(resources.ReservedResource.task_id.db_field, '_id')

        self.assertTrue(isinstance(resources.ReservedResource.worker_name, StringField))
        self.assertTrue(isinstance(resources.ReservedResource.resource_id, StringField))

        self.assertTrue(isinstance(resources.ReservedResource._ns, StringField))
        self.assertEqual(resources.ReservedResource._ns.default, 'reserved_resources')

        self.assertFalse('_id' in resources.ReservedResource._fields)
        self.assertFalse('id' in resources.ReservedResource._fields)

    def test_indexes(self):
        self.assertEqual(resources.ReservedResource._meta['indexes'],
                         ['-worker_name', '-resource_id'])

    def test_meta_collection(self):
        self.assertEqual(resources.ReservedResource._meta['collection'], 'reserved_resources')

    def test_meta_inheritance(self):
        self.assertEqual(resources.ReservedResource._meta['allow_inheritance'], False)
