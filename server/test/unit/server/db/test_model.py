"""
Tests for the pulp.server.db.model module.
"""
import os
import shutil
from tempfile import mkdtemp

from mock import patch

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from mongoengine import DateTimeField, DictField, Document, IntField, StringField

from pulp.common import error_codes
from pulp.devel.unit.util import touch
from pulp.server.exceptions import PulpCodedException
from pulp.server.db import model
from pulp.server.db.fields import ISO8601StringField
from pulp.server.db.querysets import CriteriaQuerySet


class TestContentUnit(unittest.TestCase):
    """
    Test ContentUnit model
    """

    def setUp(self):
        self.working_dir = mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.working_dir, ignore_errors=True)

    def test_model_fields(self):
        self.assertTrue(isinstance(model.ContentUnit.id, StringField))
        self.assertTrue(model.ContentUnit.id.primary_key)

        self.assertTrue(isinstance(model.ContentUnit.last_updated, IntField))
        self.assertTrue(model.ContentUnit.last_updated.required)
        self.assertEquals(model.ContentUnit.last_updated.db_field, '_last_updated')

        self.assertTrue(isinstance(model.ContentUnit.user_metadata, DictField))
        self.assertEquals(model.ContentUnit.user_metadata.db_field, 'pulp_user_metadata')

        self.assertTrue(isinstance(model.ContentUnit.storage_path, StringField))
        self.assertEquals(model.ContentUnit.storage_path.db_field, '_storage_path')

        self.assertTrue(isinstance(model.ContentUnit._ns, StringField))
        self.assertTrue(model.ContentUnit._ns)
        self.assertTrue(isinstance(model.ContentUnit.unit_type_id, StringField))
        self.assertTrue(model.ContentUnit.unit_type_id)

    def test_meta_abstract(self):
        self.assertEquals(model.ContentUnit._meta['abstract'], True)

    @patch('pulp.server.db.model.signals')
    def test_attach_signals(self, mock_signals):
        class ContentUnitHelper(model.ContentUnit):
            pass

        ContentUnitHelper.attach_signals()

        mock_signals.post_init.connect.assert_called_once_with(ContentUnitHelper.post_init_signal,
                                                               sender=ContentUnitHelper)
        mock_signals.pre_save.connect.assert_called_once_with(ContentUnitHelper.pre_save_signal,
                                                              sender=ContentUnitHelper)

    def test_post_init_signal_with_unit_key_fields_defined(self):
        """
        Test the init signal handler that validates the existence of the
        unit_key_fields list
        """
        class ContentUnitHelper(model.ContentUnit):
            unit_key_fields = ['id']

        model.ContentUnit.post_init_signal({}, ContentUnitHelper())

    def test_post_init_signal_without_unit_key_fields_defined(self):
        """
        Test the init signal handler that raises an exception if the unit_key_fields list
        has not been defined.
        """
        try:
            model.ContentUnit.post_init_signal({}, {})
            self.fail("Previous call should have raised a PulpCodedException")
        except PulpCodedException, raised_error:
            self.assertEquals(raised_error.error_code, error_codes.PLP0035)

    @patch('pulp.server.db.model.dateutils.now_utc_timestamp')
    def test_pre_save_signal(self, mock_now_utc):
        """
        Test the pre_save signal handler
        """
        class ContentUnitHelper(model.ContentUnit):
            id = None
            last_updated = None

        mock_now_utc.return_value = 'foo'
        helper = ContentUnitHelper()
        helper.last_updated = 50

        model.ContentUnit.pre_save_signal({}, helper)

        self.assertIsNotNone(helper.id)

        # make sure the last updated time has been updated
        self.assertEquals(helper.last_updated, 'foo')

    def test_pre_save_signal_leaves_existing_id(self):
        """
        Test the pre_save signal handler leaves an existing id on an object in place
        """
        class ContentUnitHelper(model.ContentUnit):
            id = None
            last_updated = None

        helper = ContentUnitHelper()
        helper.id = "foo"

        model.ContentUnit.pre_save_signal({}, helper)

        # make sure the id wasn't replaced
        self.assertEquals(helper.id, 'foo')

    def test_set_content(self):
        class ContentUnitHelper(model.ContentUnit):
            pass
        helper = ContentUnitHelper()
        helper.set_content(self.working_dir, 'apples')
        self.assertEquals(helper._source_location, self.working_dir)
        self.assertEquals(helper._relative_path, 'apples')

    def test_set_content_bad_source_location(self):
        """
        Test that the appropriate exception is raised when set_content
        is called with a non existent source_location
        """
        class ContentUnitHelper(model.ContentUnit):
            pass
        helper = ContentUnitHelper()
        try:
            helper.set_content(os.path.join(self.working_dir, 'foo'), 'apples')
            self.fail("Previous call should have raised a PulpCodedException")
        except PulpCodedException as raised_error:
            self.assertEquals(raised_error.error_code, error_codes.PLP0036)

    def test_set_content_no_relative_path(self):
        """
        Test that the appropriate exception is raised when set_content
        is called with None for the relative_path
        """
        class ContentUnitHelper(model.ContentUnit):
            pass
        helper = ContentUnitHelper()
        try:
            helper.set_content(self.working_dir, None)
            self.fail("Previous call should have raised a PulpCodedException")
        except PulpCodedException, raised_error:
            self.assertEquals(raised_error.error_code, error_codes.PLP0037)

    def test_set_content_empty_relative_path(self):
        """
        Test that the appropriate exception is raised when set_content
        is called with an empty relative_path
        """
        class ContentUnitHelper(model.ContentUnit):
            pass
        helper = ContentUnitHelper()
        try:
            helper.set_content(self.working_dir, '  ')
            self.fail("Previous call should have raised a PulpCodedException")
        except PulpCodedException as raised_error:
            self.assertEquals(raised_error.error_code, error_codes.PLP0037)

    @patch('pulp.server.db.model.config')
    def test_pre_save_signal_directory_content(self, mock_config):
        source_dir = os.path.join(self.working_dir, 'src')
        target_dir = os.path.join(self.working_dir, 'target')
        os.mkdir(source_dir)
        os.mkdir(target_dir)
        mock_config.config.get.return_value = target_dir
        # create something in the source directory to test the copy
        touch(os.path.join(source_dir, 'foo', 'bar'))

        class ContentUnitHelper(model.ContentUnit):
            unit_type_id = 'foo_unit'
        foo = ContentUnitHelper()
        foo.set_content(source_dir, 'apples')
        model.ContentUnit.pre_save_signal(object(), foo)
        full_path = os.path.join(target_dir, 'content', 'foo_unit', 'apples', 'foo', 'bar')
        self.assertTrue(os.path.exists(full_path))

    @patch('pulp.server.db.model.config')
    def test_pre_save_signal_file_content(self, mock_config):
        source_dir = os.path.join(self.working_dir, 'src')
        target_dir = os.path.join(self.working_dir, 'target')
        os.mkdir(source_dir)
        os.mkdir(target_dir)
        mock_config.config.get.return_value = target_dir
        # create something in the source directory to test the copy
        source_file = os.path.join(source_dir, 'bar')
        touch(source_file)

        class ContentUnitHelper(model.ContentUnit):
            unit_type_id = 'foo_unit'
            pass
        foo = ContentUnitHelper()
        foo.set_content(source_file, 'foo/bar')
        model.ContentUnit.pre_save_signal(object(), foo)
        full_path = os.path.join(target_dir, 'content', 'foo_unit', 'foo', 'bar')
        self.assertTrue(os.path.exists(full_path))

    @patch('pulp.server.db.model.Repository.objects')
    @patch('pulp.server.db.model.RepositoryContentUnit.objects')
    def test_get_repositories(self, mock_rcu_query, mock_repository_query):
        class ContentUnitHelper(model.ContentUnit):
            pass

        c1 = model.RepositoryContentUnit(repo_id='repo1')
        c2 = model.RepositoryContentUnit(repo_id='repo2')

        mock_rcu_query.return_value = [c1, c2]
        mock_repository_query.return_value = ['apples']

        unit = ContentUnitHelper(id='foo_id')

        self.assertEquals(unit.get_repositories(), ['apples'])

        mock_rcu_query.assert_called_once_with(unit_id='foo_id')
        mock_repository_query.assert_called_once_with(repo_id__in=['repo1', 'repo2'])


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
