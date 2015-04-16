"""
Tests for the pulp.server.db.model module.
"""
try:
    import unittest2 as unittest
except ImportError:
    import unittest


from mongoengine import Document, StringField

from pulp.server.db import model
from pulp.server.db.model.fields import ISO8601StringField


class TestRepositoryContentUnit(unittest.TestCase):

    def test_model_superclass(self):
        sample_model = model.RepositoryContentUnit()
        self.assertTrue(isinstance(sample_model, Document))

    def test_model_fields(self):
        self.assertTrue(isinstance(model.RepositoryContentUnit.repo_id, StringField))
        self.assertTrue(model.RepositoryContentUnit.repo_id.required)

        self.assertTrue(isinstance(model.RepositoryContentUnit.unit_id, StringField))
        self.assertTrue(model.RepositoryContentUnit.unit_id.required)

        self.assertTrue(isinstance(model.RepositoryContentUnit.unit_type_id, StringField))
        self.assertTrue(model.RepositoryContentUnit.unit_type_id.required)

        self.assertTrue(isinstance(model.RepositoryContentUnit.created, ISO8601StringField))
        self.assertTrue(model.RepositoryContentUnit.created.required)

        self.assertTrue(isinstance(model.RepositoryContentUnit.updated, ISO8601StringField))
        self.assertTrue(model.RepositoryContentUnit.updated.required)

        self.assertTrue(isinstance(model.RepositoryContentUnit._ns, StringField))
        self.assertEquals(model.RepositoryContentUnit._ns.default, 'repo_content_units')

    def test_meta_collection(self):
        self.assertEquals(model.RepositoryContentUnit._meta['collection'], 'repo_content_units')

    def test_meta_allow_inheritance(self):
        self.assertEquals(model.RepositoryContentUnit._meta['allow_inheritance'], False)

    def test_meta_allow_indexes(self):
        indexes = model.RepositoryContentUnit._meta['indexes']
        self.assertDictEqual(indexes[0], {'fields': ['repo_id', 'unit_type_id', 'unit_id'],
                                          'unique': True})
        self.assertDictEqual(indexes[1], {'fields': ['unit_id']})
