"""
Tests for the pulp.server.db.model module.
"""
try:
    import unittest2 as unittest
except ImportError:
    import unittest


from mongoengine import DateTimeField, DictField, Document, IntField, StringField

from pulp.server.db import model
from pulp.server.db.model.base import CriteriaQuerySet
from pulp.server.db.model.fields import ISO8601StringField


class TestRepositoryContentUnit(unittest.TestCase):
    """
    Test RepositoryContentUnit model
    """

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


class TestReservedResource(unittest.TestCase):
    """
    Test ReservedResource model
    """

    def test_model_superclass(self):
        sample_model = model.ReservedResource()
        self.assertTrue(isinstance(sample_model, Document))

    def test_attributes(self):
        self.assertTrue(isinstance(model.ReservedResource.task_id, StringField))
        self.assertTrue(model.ReservedResource.task_id.primary_key)
        self.assertEqual(model.ReservedResource.task_id.db_field, '_id')

        self.assertTrue(isinstance(model.ReservedResource.worker_name, StringField))
        self.assertTrue(isinstance(model.ReservedResource.resource_id, StringField))

        self.assertTrue(isinstance(model.ReservedResource._ns, StringField))
        self.assertEqual(model.ReservedResource._ns.default, 'reserved_resources')

        self.assertFalse('_id' in model.ReservedResource._fields)
        self.assertFalse('id' in model.ReservedResource._fields)

    def test_indexes(self):
        self.assertEqual(model.ReservedResource._meta['indexes'],
                         ['-worker_name', '-resource_id'])

    def test_meta_collection(self):
        self.assertEqual(model.ReservedResource._meta['collection'], 'reserved_resources')

    def test_meta_inheritance(self):
        self.assertEqual(model.ReservedResource._meta['allow_inheritance'], False)


class TestWorkerModel(unittest.TestCase):
    """
    Test the Worker Model
    """

    def test_model_superclass(self):
        sample_model = model.Worker()
        self.assertTrue(isinstance(sample_model, Document))

    def test_queue_name(self):
        worker = model.Worker()
        worker.name = "fake-worker"
        self.assertEquals(worker.queue_name, 'fake-worker.dq')

    def test_attributes(self):
        self.assertTrue(isinstance(model.Worker.name, StringField))
        self.assertTrue(model.Worker.name.primary_key)

        self.assertTrue(isinstance(model.Worker.last_heartbeat, DateTimeField))

        self.assertFalse('_ns' in model.Worker._fields)

    def test_indexes(self):
        self.assertEqual(model.Worker._meta['indexes'], [])

    def test_meta_collection(self):
        self.assertEqual(model.Worker._meta['collection'], 'workers')

    def test_meta_inheritance(self):
        self.assertEqual(model.Worker._meta['allow_inheritance'], False)

    def test_meta_queryset(self):
        self.assertEqual(model.Worker._meta['queryset_class'], CriteriaQuerySet)


class TestMigrationTracker(unittest.TestCase):
    """
    Test MigrationTracker model
    """

    def test_model_superclass(self):
        sample_model = model.MigrationTracker()
        self.assertTrue(isinstance(sample_model, Document))

    def test_attributes(self):
        self.assertTrue(isinstance(model.MigrationTracker.name, StringField))
        self.assertTrue(model.MigrationTracker.name.unique)
        self.assertTrue(model.MigrationTracker.name.required)

        self.assertTrue(isinstance(model.MigrationTracker.version, IntField))
        self.assertEqual(model.MigrationTracker.version.default, 0)

        self.assertTrue(isinstance(model.MigrationTracker._ns, StringField))
        self.assertEqual(model.MigrationTracker._ns.default, 'migration_trackers')

    def test_indexes(self):
        self.assertEqual(model.MigrationTracker._meta['indexes'], [])

    def test_meta_collection(self):
        self.assertEqual(model.MigrationTracker._meta['collection'], 'migration_trackers')

    def test_meta_inheritance(self):
        self.assertEqual(model.ReservedResource._meta['allow_inheritance'], False)


class TestRepository(unittest.TestCase):

    """
    Tests for the Repository model.
    """

    def test_model_superclass(self):
        """
        Ensure that the Repository model is a subclass of Mongoengine's Document class.
        """
        sample_model = model.Repository()
        self.assertTrue(isinstance(sample_model, Document))

    def test_model_fields(self):
        """
        Assert that each field has the correct type and `required` status.
        """
        self.assertTrue(isinstance(model.Repository.repo_id, StringField))
        self.assertTrue(model.Repository.repo_id.required)

        self.assertEqual(model.Repository.repo_id.db_field, 'id')

        self.assertTrue(isinstance(model.Repository.display_name, StringField))
        self.assertTrue(model.Repository.display_name.required)

        self.assertTrue(isinstance(model.Repository.description, StringField))
        self.assertFalse(model.Repository.description.required)

        self.assertTrue(isinstance(model.Repository.notes, DictField))
        self.assertFalse(model.Repository.notes.required)

        self.assertTrue(isinstance(model.Repository.scratchpad, DictField))
        self.assertFalse(model.Repository.scratchpad.required)

        self.assertTrue(isinstance(model.Repository.content_unit_counts, DictField))
        self.assertFalse(model.Repository.content_unit_counts.required)

        self.assertTrue(isinstance(model.Repository.last_unit_added, DateTimeField))
        self.assertFalse(model.Repository.last_unit_added.required)

        self.assertTrue(isinstance(model.Repository.last_unit_removed, DateTimeField))
        self.assertFalse(model.Repository.last_unit_removed.required)

        self.assertTrue(isinstance(model.Repository._ns, StringField))
        self.assertEquals(model.Repository._ns.default, 'repos')

    def test_meta_collection(self):
        """
        Assert that the collection name is correct.
        """
        self.assertEquals(model.Repository._meta['collection'], 'repos')

    def test_meta_allow_inheritance(self):
        """
        Ensure that inheritance is not allowed.
        """
        self.assertEquals(model.Repository._meta['allow_inheritance'], False)

    def test_meta_allow_indexes(self):
        """
        Test that the indexes are set correctly.
        """
        indexes = model.Repository._meta['indexes']
        self.assertDictEqual(indexes[0], {'fields': ['-repo_id'], 'unique': True})
