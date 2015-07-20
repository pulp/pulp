# -*- coding: utf-8 -*-

"""
Tests for the pulp.server.db.model module.
"""

from mock import patch, Mock

from mongoengine import ValidationError, DateTimeField, DictField, Document, IntField, StringField

from pulp.common import error_codes, dateutils
from pulp.common.compat import unittest
from pulp.server.exceptions import PulpCodedException
from pulp.server.db import model
from pulp.server.db.fields import ISO8601StringField
from pulp.server.db.querysets import CriteriaQuerySet


class TestContentUnit(unittest.TestCase):
    """
    Test ContentUnit model
    """

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
            unit_type_id = StringField(default='foo')
            unit_key_fields = ['apple', 'pear']

        ContentUnitHelper.attach_signals()

        mock_signals.post_init.connect.assert_called_once_with(ContentUnitHelper.post_init_signal,
                                                               sender=ContentUnitHelper)
        mock_signals.pre_save.connect.assert_called_once_with(ContentUnitHelper.pre_save_signal,
                                                              sender=ContentUnitHelper)

        self.assertEquals('foo', ContentUnitHelper.NAMED_TUPLE.__name__)
        self.assertEquals(('apple', 'pear'), ContentUnitHelper.NAMED_TUPLE._fields)

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

    @patch('pulp.server.db.model.signals')
    def test_as_named_tuple(self, m_signal):
        class ContentUnitHelper(model.ContentUnit):
            apple = StringField()
            pear = StringField()
            unit_key_fields = ('apple', 'pear')
            unit_type_id = StringField(default='bar')

        # create the named tuple
        ContentUnitHelper.attach_signals()

        helper = ContentUnitHelper(apple='foo', pear='bar')

        n_tuple = helper.unit_key_as_named_tuple

        self.assertEquals(n_tuple, ContentUnitHelper.NAMED_TUPLE(apple='foo', pear='bar'))


class TestFileContentUnit(unittest.TestCase):

    class TestUnit(model.FileContentUnit):
        pass

    def test_init(self):
        unit = TestFileContentUnit.TestUnit()
        self.assertEqual(unit._source_location, None)

    @patch('os.path.exists')
    def test_set_content(self, exists):
        path = '1234'
        unit = TestFileContentUnit.TestUnit()
        exists.return_value = True
        unit.set_content(path)
        exists.assert_called_once_with(path)
        self.assertEquals(unit._source_location, path)

    @patch('os.path.exists')
    def test_set_content_bad_source_location(self, exists):
        """
        Test that the appropriate exception is raised when set_content
        is called with a non existent source_location
        """
        exists.return_value = False
        unit = TestFileContentUnit.TestUnit()
        try:
            unit.set_content('1234')
            self.fail("Previous call should have raised a PulpCodedException")
        except PulpCodedException as raised_error:
            self.assertEquals(raised_error.error_code, error_codes.PLP0036)

    @patch('pulp.server.db.model.FileStorage.put')
    @patch('pulp.server.db.model.FileStorage.open')
    @patch('pulp.server.db.model.FileStorage.close')
    def test_pre_save_signal(self, close, _open, put):
        sender = Mock()
        kwargs = {'a': 1, 'b': 2}

        # test
        unit = TestFileContentUnit.TestUnit()
        unit._source_location = '1234'
        with patch('pulp.server.db.model.ContentUnit.pre_save_signal') as base:
            unit.pre_save_signal(sender, unit, **kwargs)

        # validation
        base.assert_called_once_with(sender, unit, **kwargs)
        _open.assert_called_once_with()
        close.assert_called_once_with()
        put.assert_called_once_with(unit, unit._source_location)

    @patch('pulp.server.db.model.FileStorage.put')
    @patch('pulp.server.db.model.FileStorage.open')
    @patch('pulp.server.db.model.FileStorage.close')
    def test_pre_save_signal_no_content(self, close, _open, put):
        sender = Mock()
        kwargs = {'a': 1, 'b': 2}

        # test
        unit = TestFileContentUnit.TestUnit()
        unit._source_location = None
        with patch('pulp.server.db.model.ContentUnit.pre_save_signal') as base:
            unit.pre_save_signal(sender, unit, **kwargs)

        # validation
        base.assert_called_once_with(sender, unit, **kwargs)
        self.assertFalse(_open.called)
        self.assertFalse(close.called)
        self.assertFalse(put.called)


class TestSharedContentUnit(unittest.TestCase):

    class TestUnit(model.SharedContentUnit):
        pass

    def test_abstract(self):
        unit = TestSharedContentUnit.TestUnit()
        try:
            unit.storage_id
            self.fail('NotImplementedError expected and not raised')
        except NotImplementedError:
            pass

    @patch('pulp.server.db.model.SharedStorage.link')
    @patch('pulp.server.db.model.SharedStorage.open')
    @patch('pulp.server.db.model.SharedStorage.close')
    @patch('pulp.server.db.model.SharedContentUnit.storage_id', '1234')
    def test_pre_save_signal(self, close, _open, link):
        sender = Mock()
        kwargs = {'a': 1, 'b': 2}

        # test
        unit = TestSharedContentUnit.TestUnit()
        with patch('pulp.server.db.model.ContentUnit.pre_save_signal') as base:
            unit.pre_save_signal(sender, unit, **kwargs)

        # validation
        base.assert_called_once_with(sender, unit, **kwargs)
        _open.assert_called_once_with()
        close.assert_called_once_with()
        link.assert_called_once_with(unit)


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

        self.assertTrue('_ns' in model.Worker._fields)

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
        self.assertEqual(model.Repository.repo_id.db_field, 'repo_id')

        self.assertTrue(isinstance(model.Repository.display_name, StringField))
        self.assertFalse(model.Repository.display_name.required)

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

    def test_invalid_repo_id(self):
        """
        Ensure that validation raises as expected when invalid characters are present.
        """
        repo_obj = model.Repository('invalid_char%')
        self.assertRaises(ValidationError, repo_obj.validate)

    def test_create_i18n(self):
        """
        Test use of international text for fields that are not repo_id.
        """
        i18n_text = 'Brasília'
        repo_obj = model.Repository('limited_characters', i18n_text, i18n_text)
        repo_obj.validate()

    def test_to_transfer_repo(self):
        """
        Test changing a repository object into a transfer unit for plugins.
        """
        dt = dateutils.now_utc_datetime_with_tzinfo()
        data = {
            'repo_id': 'foo',
            'display_name': 'bar',
            'description': 'baz',
            'notes': 'qux',
            'content_unit_counts': {'units': 1},
            'last_unit_added': dt,
            'last_unit_removed': dt
        }
        repo_obj = model.Repository(**data)
        repo = repo_obj.to_transfer_repo()

        self.assertEquals('foo', repo.id)
        self.assertFalse(hasattr(repo, 'repo_id'))
        self.assertEquals('bar', repo.display_name)
        self.assertEquals('baz', repo.description)
        self.assertEquals('qux', repo.notes)
        self.assertEquals({'units': 1}, repo.content_unit_counts)
        self.assertEquals(dt, repo.last_unit_added)
        self.assertEquals(dt, repo.last_unit_removed)

    def test_update_from_delta(self):
        """
        Update repository information from a delta dictionary.
        """
        repo_obj = model.Repository('mock_repo')
        repo_obj.update_from_delta({'display_name': 'dn_updated', 'description': 'd_update'})
        self.assertEqual(repo_obj.display_name, 'dn_updated')
        self.assertEqual(repo_obj.description, 'd_update')

    def test_update_from_delta_skips_prohibited_fields(self):
        """
        Attempt to update a prohibited field. Make sure it is ignored.
        """
        repo_obj = model.Repository('mock_repo')
        repo_obj.update_from_delta({'repo_id': 'id_updated'})
        self.assertEqual(repo_obj.repo_id, 'mock_repo')

    def test_update_from_delta_notes(self):
        """
        Test the update of notes.

        Make sure new fields are added, fields changed to `None` are removed, and existing fields
        are modified.
        """
        repo_obj = model.Repository('mock_repo', notes={'remove': 1, 'leave': 2, 'modify': 3})
        repo_obj.update_from_delta({'notes': {'remove': None, 'modify': 4, 'add': 5}})
        self.assertEqual(repo_obj.repo_id, 'mock_repo')
        self.assertFalse('remove' in repo_obj.notes)
        self.assertEqual(repo_obj.notes['leave'], 2)
        self.assertEqual(repo_obj.notes['modify'], 4)
        self.assertEqual(repo_obj.notes['add'], 5)


class TestCeleryBeatLock(unittest.TestCase):
    """
    Test the CeleryBeatLock class.
    """
    def test_model_superclass(self):
        sample_model = model.CeleryBeatLock()
        self.assertTrue(isinstance(sample_model, Document))

    def test_attributes(self):
        self.assertTrue(isinstance(model.CeleryBeatLock.celerybeat_name, StringField))
        self.assertTrue(model.CeleryBeatLock.celerybeat_name.required)

        self.assertTrue(model.CeleryBeatLock.timestamp, DateTimeField)
        self.assertTrue(model.CeleryBeatLock.timestamp.required)

        self.assertTrue(model.CeleryBeatLock.lock, StringField)
        self.assertTrue(model.CeleryBeatLock.lock.required)
        self.assertTrue(model.CeleryBeatLock.lock.default, 'locked')
        self.assertTrue(model.CeleryBeatLock.lock.unique)

        self.assertTrue('_ns' in model.CeleryBeatLock._fields)

    def test_meta_collection(self):
        """
        Assert that the collection name is correct.
        """
        self.assertEquals(model.CeleryBeatLock._meta['collection'], 'celery_beat_lock')
