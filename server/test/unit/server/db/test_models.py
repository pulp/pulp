# -*- coding: utf-8 -*-

"""
Tests for the pulp.server.db.models module.
"""

from mock import patch, Mock

from mongoengine import ValidationError, DateTimeField, DictField, Document, IntField, StringField

from pulp.common import error_codes, dateutils
from pulp.common.compat import unittest
from pulp.server.exceptions import PulpCodedException
from pulp.server.db import models
from pulp.server.db.fields import ISO8601StringField
from pulp.server.db.querysets import CriteriaQuerySet


@patch('pulp.server.db.models.UnsafeRetry')
class TestAutoRetryDocument(unittest.TestCase):
    """
    Test base class for pulp docs.
    """

    def test_decorate_on_init(self, m_retry):
        """
        Ensure that subclass's of AutoRetryDocuments are decorated on init.
        """

        class MockDoc(models.AutoRetryDocument):
            pass

        doc = MockDoc()
        m_retry.decorate_instance.assert_called_once_with(instance=doc, full_name=type(doc))

    def test_abstact(self, m_retry):
        """
        Ensure that AutoRetryDocument is an abstract document.
        """
        self.assertDictEqual(models.AutoRetryDocument._meta, {'abstract': True})


class TestContentUnit(unittest.TestCase):
    """
    Test ContentUnit model
    """

    def test_model_fields(self):
        self.assertTrue(isinstance(models.ContentUnit.id, StringField))
        self.assertTrue(models.ContentUnit.id.primary_key)

        self.assertTrue(isinstance(models.ContentUnit.last_updated, IntField))
        self.assertTrue(models.ContentUnit.last_updated.required)
        self.assertEquals(models.ContentUnit.last_updated.db_field, '_last_updated')

        self.assertTrue(isinstance(models.ContentUnit.user_metadata, DictField))
        self.assertEquals(models.ContentUnit.user_metadata.db_field, 'pulp_user_metadata')

        self.assertTrue(isinstance(models.ContentUnit.storage_path, StringField))
        self.assertEquals(models.ContentUnit.storage_path.db_field, '_storage_path')

        self.assertTrue(isinstance(models.ContentUnit._ns, StringField))
        self.assertTrue(models.ContentUnit._ns)
        self.assertTrue(isinstance(models.ContentUnit.unit_type_id, StringField))
        self.assertTrue(models.ContentUnit.unit_type_id)

    def test_meta_abstract(self):
        self.assertEquals(models.ContentUnit._meta['abstract'], True)

    @patch('pulp.server.db.models.signals')
    def test_attach_signals(self, mock_signals):
        class ContentUnitHelper(models.ContentUnit):
            unit_type_id = StringField(default='foo')
            unit_key_fields = ['apple', 'pear']

        ContentUnitHelper.attach_signals()

        mock_signals.pre_save.connect.assert_called_once_with(ContentUnitHelper.pre_save_signal,
                                                              sender=ContentUnitHelper)

        self.assertEquals('foo', ContentUnitHelper.NAMED_TUPLE.__name__)
        self.assertEquals(('apple', 'pear'), ContentUnitHelper.NAMED_TUPLE._fields)

    def test_attach_signals_without_unit_key_fields_defined(self):
        class ContentUnitHelper(models.ContentUnit):
            unit_type_id = StringField(default='foo')

        try:
            ContentUnitHelper.attach_signals()
            self.fail("Previous call should have raised a PulpCodedException")
        except PulpCodedException, raised_error:
            self.assertEquals(raised_error.error_code, error_codes.PLP0035)
            self.assertEqual(raised_error.error_data, {'class_name': 'ContentUnitHelper'})

    @patch('pulp.server.db.models.dateutils.now_utc_timestamp')
    def test_pre_save_signal(self, mock_now_utc):
        """
        Test the pre_save signal handler
        """
        class ContentUnitHelper(models.ContentUnit):
            id = None
            last_updated = None

        mock_now_utc.return_value = 'foo'
        helper = ContentUnitHelper()
        helper.last_updated = 50

        models.ContentUnit.pre_save_signal({}, helper)

        self.assertIsNotNone(helper.id)

        # make sure the last updated time has been updated
        self.assertEquals(helper.last_updated, 'foo')

    def test_pre_save_signal_leaves_existing_id(self):
        """
        Test the pre_save signal handler leaves an existing id on an object in place
        """
        class ContentUnitHelper(models.ContentUnit):
            id = None
            last_updated = None

        helper = ContentUnitHelper()
        helper.id = "foo"

        models.ContentUnit.pre_save_signal({}, helper)

        # make sure the id wasn't replaced
        self.assertEquals(helper.id, 'foo')

    @patch('pulp.server.db.models.Repository.objects')
    @patch('pulp.server.db.models.RepositoryContentUnit.objects')
    def test_get_repositories(self, mock_rcu_query, mock_repository_query):
        class ContentUnitHelper(models.ContentUnit):
            pass

        c1 = models.RepositoryContentUnit(repo_id='repo1')
        c2 = models.RepositoryContentUnit(repo_id='repo2')

        mock_rcu_query.return_value = [c1, c2]
        mock_repository_query.return_value = ['apples']

        unit = ContentUnitHelper(id='foo_id')

        self.assertEquals(unit.get_repositories(), ['apples'])

        mock_rcu_query.assert_called_once_with(unit_id='foo_id')
        mock_repository_query.assert_called_once_with(repo_id__in=['repo1', 'repo2'])

    @patch('pulp.server.db.models.signals')
    def test_as_named_tuple(self, m_signal):
        class ContentUnitHelper(models.ContentUnit):
            apple = StringField()
            pear = StringField()
            unit_key_fields = ('apple', 'pear')
            unit_type_id = StringField(default='bar')

        # create the named tuple
        ContentUnitHelper.attach_signals()

        helper = ContentUnitHelper(apple='foo', pear='bar')

        n_tuple = helper.unit_key_as_named_tuple

        self.assertEquals(n_tuple, ContentUnitHelper.NAMED_TUPLE(apple='foo', pear='bar'))

    def test_id_to_dict(self):
        class ContentUnitHelper(models.ContentUnit):
            apple = StringField()
            pear = StringField()
            unit_key_fields = ('apple', 'pear')
            unit_type_id = StringField(default='bar')
        my_unit = ContentUnitHelper(apple='apple', pear='pear')
        ret = my_unit.to_id_dict()
        expected_dict = {'unit_key': {'pear': u'pear', 'apple': u'apple'}, 'type_id': 'bar'}
        self.assertEqual(ret, expected_dict)

    def test_type_id(self):
        class ContentUnitHelper(models.ContentUnit):
            unit_type_id = StringField()
        my_unit = ContentUnitHelper(unit_type_id='apple')
        self.assertEqual(my_unit.type_id, 'apple')


class TestFileContentUnit(unittest.TestCase):

    class TestUnit(models.FileContentUnit):
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

    @patch('pulp.server.db.models.FileStorage.put')
    @patch('pulp.server.db.models.FileStorage.open')
    @patch('pulp.server.db.models.FileStorage.close')
    def test_pre_save_signal(self, close, _open, put):
        sender = Mock()
        kwargs = {'a': 1, 'b': 2}

        # test
        unit = TestFileContentUnit.TestUnit()
        unit._source_location = '1234'
        with patch('pulp.server.db.models.ContentUnit.pre_save_signal') as base:
            unit.pre_save_signal(sender, unit, **kwargs)

        # validation
        base.assert_called_once_with(sender, unit, **kwargs)
        _open.assert_called_once_with()
        close.assert_called_once_with()
        put.assert_called_once_with(unit, unit._source_location)

    @patch('pulp.server.db.models.FileStorage.put')
    @patch('pulp.server.db.models.FileStorage.open')
    @patch('pulp.server.db.models.FileStorage.close')
    def test_pre_save_signal_no_content(self, close, _open, put):
        sender = Mock()
        kwargs = {'a': 1, 'b': 2}

        # test
        unit = TestFileContentUnit.TestUnit()
        unit._source_location = None
        with patch('pulp.server.db.models.ContentUnit.pre_save_signal') as base:
            unit.pre_save_signal(sender, unit, **kwargs)

        # validation
        base.assert_called_once_with(sender, unit, **kwargs)
        self.assertFalse(_open.called)
        self.assertFalse(close.called)
        self.assertFalse(put.called)


class TestSharedContentUnit(unittest.TestCase):

    class TestUnit(models.SharedContentUnit):
        pass

    def test_abstract(self):
        unit = TestSharedContentUnit.TestUnit()
        self.assertRaises(NotImplementedError, getattr, unit, 'storage_provider')
        self.assertRaises(NotImplementedError, getattr, unit, 'storage_id')

    @patch('pulp.server.db.models.SharedStorage.link')
    @patch('pulp.server.db.models.SharedStorage.open')
    @patch('pulp.server.db.models.SharedStorage.close')
    @patch('pulp.server.db.models.SharedContentUnit.storage_provider', 'git')
    @patch('pulp.server.db.models.SharedContentUnit.storage_id', '1234')
    def test_pre_save_signal(self, close, _open, link):
        sender = Mock()
        kwargs = {'a': 1, 'b': 2}

        # test
        unit = TestSharedContentUnit.TestUnit()
        with patch('pulp.server.db.models.ContentUnit.pre_save_signal') as base:
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
        sample_model = models.RepositoryContentUnit()
        self.assertTrue(isinstance(sample_model, Document))

    def test_model_fields(self):
        self.assertTrue(isinstance(models.RepositoryContentUnit.repo_id, StringField))
        self.assertTrue(models.RepositoryContentUnit.repo_id.required)

        self.assertTrue(isinstance(models.RepositoryContentUnit.unit_id, StringField))
        self.assertTrue(models.RepositoryContentUnit.unit_id.required)

        self.assertTrue(isinstance(models.RepositoryContentUnit.unit_type_id, StringField))
        self.assertTrue(models.RepositoryContentUnit.unit_type_id.required)

        self.assertTrue(isinstance(models.RepositoryContentUnit.created, ISO8601StringField))
        self.assertTrue(models.RepositoryContentUnit.created.required)

        self.assertTrue(isinstance(models.RepositoryContentUnit.updated, ISO8601StringField))
        self.assertTrue(models.RepositoryContentUnit.updated.required)

        self.assertTrue(isinstance(models.RepositoryContentUnit._ns, StringField))
        self.assertEquals(models.RepositoryContentUnit._ns.default, 'repo_content_units')

    def test_meta_collection(self):
        self.assertEquals(models.RepositoryContentUnit._meta['collection'], 'repo_content_units')

    def test_meta_allow_inheritance(self):
        self.assertEquals(models.RepositoryContentUnit._meta['allow_inheritance'], False)

    def test_meta_allow_indexes(self):
        indexes = models.RepositoryContentUnit._meta['indexes']
        self.assertDictEqual(indexes[0], {'fields': ['repo_id', 'unit_type_id', 'unit_id'],
                                          'unique': True})
        self.assertDictEqual(indexes[1], {'fields': ['unit_id']})


class TestReservedResource(unittest.TestCase):
    """
    Test ReservedResource model
    """

    def test_model_superclass(self):
        sample_model = models.ReservedResource()
        self.assertTrue(isinstance(sample_model, Document))

    def test_attributes(self):
        self.assertTrue(isinstance(models.ReservedResource.task_id, StringField))
        self.assertTrue(models.ReservedResource.task_id.primary_key)
        self.assertEqual(models.ReservedResource.task_id.db_field, '_id')

        self.assertTrue(isinstance(models.ReservedResource.worker_name, StringField))
        self.assertTrue(isinstance(models.ReservedResource.resource_id, StringField))

        self.assertTrue(isinstance(models.ReservedResource._ns, StringField))
        self.assertEqual(models.ReservedResource._ns.default, 'reserved_resources')

        self.assertFalse('_id' in models.ReservedResource._fields)
        self.assertFalse('id' in models.ReservedResource._fields)

    def test_indexes(self):
        self.assertEqual(models.ReservedResource._meta['indexes'],
                         ['-worker_name', '-resource_id'])

    def test_meta_collection(self):
        self.assertEqual(models.ReservedResource._meta['collection'], 'reserved_resources')

    def test_meta_inheritance(self):
        self.assertEqual(models.ReservedResource._meta['allow_inheritance'], False)


class TestWorkerModel(unittest.TestCase):
    """
    Test the Worker Model
    """

    def test_model_superclass(self):
        sample_model = models.Worker()
        self.assertTrue(isinstance(sample_model, Document))

    def test_queue_name(self):
        worker = models.Worker()
        worker.name = "fake-worker"
        self.assertEquals(worker.queue_name, 'fake-worker.dq')

    def test_attributes(self):
        self.assertTrue(isinstance(models.Worker.name, StringField))
        self.assertTrue(models.Worker.name.primary_key)

        self.assertTrue(isinstance(models.Worker.last_heartbeat, DateTimeField))

        self.assertTrue('_ns' in models.Worker._fields)

    def test_indexes(self):
        self.assertEqual(models.Worker._meta['indexes'], [])

    def test_meta_collection(self):
        self.assertEqual(models.Worker._meta['collection'], 'workers')

    def test_meta_inheritance(self):
        self.assertEqual(models.Worker._meta['allow_inheritance'], False)

    def test_meta_queryset(self):
        self.assertEqual(models.Worker._meta['queryset_class'], CriteriaQuerySet)


class TestMigrationTracker(unittest.TestCase):
    """
    Test MigrationTracker model
    """

    def test_model_superclass(self):
        sample_model = models.MigrationTracker()
        self.assertTrue(isinstance(sample_model, Document))

    def test_attributes(self):
        self.assertTrue(isinstance(models.MigrationTracker.name, StringField))
        self.assertTrue(models.MigrationTracker.name.unique)
        self.assertTrue(models.MigrationTracker.name.required)

        self.assertTrue(isinstance(models.MigrationTracker.version, IntField))
        self.assertEqual(models.MigrationTracker.version.default, 0)

        self.assertTrue(isinstance(models.MigrationTracker._ns, StringField))
        self.assertEqual(models.MigrationTracker._ns.default, 'migration_trackers')

    def test_indexes(self):
        self.assertEqual(models.MigrationTracker._meta['indexes'], [])

    def test_meta_collection(self):
        self.assertEqual(models.MigrationTracker._meta['collection'], 'migration_trackers')

    def test_meta_inheritance(self):
        self.assertEqual(models.ReservedResource._meta['allow_inheritance'], False)


class TestRepository(unittest.TestCase):

    """
    Tests for the Repository model.
    """

    def test_model_superclass(self):
        """
        Ensure that the Repository model is a subclass of Mongoengine's Document class.
        """
        sample_model = models.Repository()
        self.assertTrue(isinstance(sample_model, Document))

    def test_model_fields(self):
        """
        Assert that each field has the correct type and `required` status.
        """
        self.assertTrue(isinstance(models.Repository.repo_id, StringField))
        self.assertTrue(models.Repository.repo_id.required)
        self.assertEqual(models.Repository.repo_id.db_field, 'repo_id')

        self.assertTrue(isinstance(models.Repository.display_name, StringField))
        self.assertFalse(models.Repository.display_name.required)

        self.assertTrue(isinstance(models.Repository.description, StringField))
        self.assertFalse(models.Repository.description.required)

        self.assertTrue(isinstance(models.Repository.notes, DictField))
        self.assertFalse(models.Repository.notes.required)

        self.assertTrue(isinstance(models.Repository.scratchpad, DictField))
        self.assertFalse(models.Repository.scratchpad.required)

        self.assertTrue(isinstance(models.Repository.content_unit_counts, DictField))
        self.assertFalse(models.Repository.content_unit_counts.required)

        self.assertTrue(isinstance(models.Repository.last_unit_added, DateTimeField))
        self.assertFalse(models.Repository.last_unit_added.required)

        self.assertTrue(isinstance(models.Repository.last_unit_removed, DateTimeField))
        self.assertFalse(models.Repository.last_unit_removed.required)

        self.assertTrue(isinstance(models.Repository._ns, StringField))
        self.assertEquals(models.Repository._ns.default, 'repos')

    def test_meta_collection(self):
        """
        Assert that the collection name is correct.
        """
        self.assertEquals(models.Repository._meta['collection'], 'repos')

    def test_meta_allow_inheritance(self):
        """
        Ensure that inheritance is not allowed.
        """
        self.assertEquals(models.Repository._meta['allow_inheritance'], False)

    def test_meta_allow_indexes(self):
        """
        Test that the indexes are set correctly.
        """
        indexes = models.Repository._meta['indexes']
        self.assertDictEqual(indexes[0], {'fields': ['-repo_id'], 'unique': True})

    def test_invalid_repo_id(self):
        """
        Ensure that validation raises as expected when invalid characters are present.
        """
        repo_obj = models.Repository('invalid_char%')
        self.assertRaises(ValidationError, repo_obj.validate)

    def test_create_i18n(self):
        """
        Test use of international text for fields that are not repo_id.
        """
        i18n_text = 'Brasília'
        repo_obj = models.Repository('limited_characters', i18n_text, i18n_text)
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
        repo_obj = models.Repository(**data)
        repo = repo_obj.to_transfer_repo()

        self.assertEquals('foo', repo.id)
        self.assertFalse(hasattr(repo, 'repo_id'))
        self.assertEquals('bar', repo.display_name)
        self.assertEquals('baz', repo.description)
        self.assertEquals('qux', repo.notes)
        self.assertEquals({'units': 1}, repo.content_unit_counts)
        self.assertEquals(dt, repo.last_unit_added)
        self.assertEquals(dt, repo.last_unit_removed)
        self.assertEquals(repo_obj, repo.repo_obj)

    def test_update_from_delta(self):
        """
        Update repository information from a delta dictionary.
        """
        repo_obj = models.Repository('mock_repo')
        repo_obj.update_from_delta({'display_name': 'dn_updated', 'description': 'd_update'})
        self.assertEqual(repo_obj.display_name, 'dn_updated')
        self.assertEqual(repo_obj.description, 'd_update')

    def test_update_from_delta_skips_prohibited_fields(self):
        """
        Attempt to update a prohibited field. Make sure it is ignored.
        """
        repo_obj = models.Repository('mock_repo')
        repo_obj.update_from_delta({'repo_id': 'id_updated'})
        self.assertEqual(repo_obj.repo_id, 'mock_repo')

    def test_update_from_delta_notes(self):
        """
        Test the update of notes.

        Make sure new fields are added, fields changed to `None` are removed, and existing fields
        are modified.
        """
        repo_obj = models.Repository('mock_repo', notes={'remove': 1, 'leave': 2, 'modify': 3})
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
        sample_model = models.CeleryBeatLock()
        self.assertTrue(isinstance(sample_model, Document))

    def test_attributes(self):
        self.assertTrue(isinstance(models.CeleryBeatLock.celerybeat_name, StringField))
        self.assertTrue(models.CeleryBeatLock.celerybeat_name.required)

        self.assertTrue(isinstance(models.CeleryBeatLock.timestamp, DateTimeField))
        self.assertTrue(models.CeleryBeatLock.timestamp.required)

        self.assertTrue(isinstance(models.CeleryBeatLock.lock, StringField))
        self.assertTrue(models.CeleryBeatLock.lock.required)
        self.assertTrue(models.CeleryBeatLock.lock.default, 'locked')
        self.assertTrue(models.CeleryBeatLock.lock.unique)

        self.assertTrue('_ns' in models.CeleryBeatLock._fields)

    def test_meta_collection(self):
        """
        Assert that the collection name is correct.
        """
        self.assertEquals(models.CeleryBeatLock._meta['collection'], 'celery_beat_lock')
