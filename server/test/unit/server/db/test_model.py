# -*- coding: utf-8 -*-

"""
Tests for the pulp.server.db.model module.
"""
from mock import patch, Mock, call

from mongoengine import (ValidationError, BooleanField, DateTimeField, DictField,
                         Document, IntField, ListField, StringField, QuerySetNoCache)

from pulp.common import error_codes, dateutils
from pulp.common.compat import unittest
from pulp.common.error_codes import PLP0036, PLP0037
from pulp.server import exceptions
from pulp.server.exceptions import PulpCodedException
from pulp.server.db import model
from pulp.server.db.fields import ISO8601StringField
from pulp.server.db.querysets import CriteriaQuerySet
from pulp.server.webservices.views import serializers


class TestAutoRetryDocument(unittest.TestCase):
    """
    Test base class for pulp docs.
    """

    @patch('pulp.server.db.model.UnsafeRetry')
    def test_decorate_on_init(self, m_retry):
        """
        Ensure that subclass's of AutoRetryDocuments are decorated on init.
        """
        class MockDoc(model.AutoRetryDocument):
            pass

        doc = MockDoc()
        m_retry.decorate_instance.assert_called_once_with(instance=doc, full_name=type(doc))

    def test_abstact(self):
        """
        Ensure that AutoRetryDocument is an abstract document.
        """
        self.assertTrue(model.AutoRetryDocument._meta['abstract'])

    def test_no_cache_query_set(self):
        """Ensure the QuerySet class is the non-caching variety."""
        self.assertTrue(issubclass(model.AutoRetryDocument._meta['queryset_class'],
                                   QuerySetNoCache))

    def test_clean_raises_nothing_if_properly_defined(self):
        class MockDoc(model.AutoRetryDocument):
            _ns = StringField(default='dummy_collection_name')

        try:
            MockDoc().clean()
        except Exception:
            self.fail("MockDoc is properly defined and should validate correctly")

    def test__ns_is_not_defined_on_abstract_class(self):
        self.assertFalse(hasattr(model.ContentUnit, '_ns'))


class TestAutoRetryDocumentClean(unittest.TestCase):

    def test_clean_raises_ValidationError_when__ns_field_is_not_defined(self):
        class MockDoc(model.AutoRetryDocument):
            pass

        self.assertRaises(ValidationError, MockDoc().clean)

    def test_clean_raises_ValidationError_when__ns_field_is_wrong_type(self):
        class MockDoc(model.AutoRetryDocument):
            _ns = IntField(default=1)

        self.assertRaises(ValidationError, MockDoc().clean)

    def test_clean_raises_ValidationError_when__ns_field_default_is_not_defined(self):
        class MockDoc(model.AutoRetryDocument):
            _ns = StringField()

        self.assertRaises(ValidationError, MockDoc().clean)


class ContentUnitHelper(model.ContentUnit):
    """Used to test ContentUnit since it must be sub-classed to be used."""
    apple = StringField()
    pear = StringField()
    unit_key_fields = ('apple', 'pear')
    _content_type_id = StringField(default='mock_type_id')


class TestContentUnit(unittest.TestCase):
    """
    Test ContentUnit model
    """

    def test_model_fields(self):
        self.assertTrue(isinstance(model.ContentUnit.id, StringField))
        self.assertTrue(model.ContentUnit.id.primary_key)
        self.assertTrue(callable(model.ContentUnit.id.default))
        self.assertTrue(isinstance(model.ContentUnit._last_updated, IntField))
        self.assertTrue(model.ContentUnit._last_updated.required)
        self.assertTrue(isinstance(model.ContentUnit._storage_path, StringField))
        self.assertTrue(isinstance(model.ContentUnit.pulp_user_metadata, DictField))

    @patch('pulp.server.db.model.uuid')
    def test_default_id(self, uuid):
        uuid.uuid4.return_value = '1234'
        unit = ContentUnitHelper()
        uuid.uuid4.assert_called_once_with()
        self.assertEqual(unit.id, uuid.uuid4.return_value)

    def test_meta_abstract(self):
        self.assertEquals(model.ContentUnit._meta['abstract'], True)

    @patch('pulp.server.db.model.signals')
    def test_attach_signals(self, mock_signals):
        ContentUnitHelper.attach_signals()

        mock_signals.pre_save.connect.assert_called_once_with(ContentUnitHelper.pre_save_signal,
                                                              sender=ContentUnitHelper)

    @patch('pulp.server.db.model.dateutils.now_utc_timestamp')
    def test_pre_save_signal(self, mock_now_utc):
        """
        Test the pre_save signal handler
        """
        mock_now_utc.return_value = 'foo'
        helper = ContentUnitHelper()
        helper._last_updated = 50

        model.ContentUnit.pre_save_signal({}, helper)

        self.assertIsNotNone(helper.id)

        # make sure the last updated time has been updated
        self.assertEquals(helper._last_updated, 'foo')

    @patch('pulp.server.db.model.Repository.objects')
    @patch('pulp.server.db.model.RepositoryContentUnit.objects')
    def test_get_repositories(self, mock_rcu_query, mock_repository_query):
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
            _content_type_id = StringField(default='bar')

        helper = ContentUnitHelper(apple='foo', pear='bar')

        n_tuple = helper.unit_key_as_named_tuple

        self.assertEquals(n_tuple, ContentUnitHelper.NAMED_TUPLE(apple='foo', pear='bar'))

    def test_id_to_dict(self):
        my_unit = ContentUnitHelper(apple='apple', pear='pear')
        ret = my_unit.to_id_dict()
        expected_dict = {
            'unit_key': {'pear': u'pear', 'apple': u'apple'},
            'type_id': 'mock_type_id'
        }
        self.assertEqual(ret, expected_dict)

    def test_storage_path(self):
        my_unit = ContentUnitHelper(_storage_path='apple')
        self.assertEqual(my_unit.storage_path, my_unit._storage_path)

    def test_type_id(self):
        my_unit = ContentUnitHelper(_content_type_id='apple')
        self.assertEqual(my_unit.type_id, my_unit._content_type_id)

    def test__content_type_id_field_is_not_defined_on_abstract_class(self):
        self.assertFalse(hasattr(model.ContentUnit, '_content_type_id'))

    def test_unit_key_fields_is_not_defined_on_abstract_class(self):
        self.assertFalse(hasattr(model.ContentUnit, 'unit_key_fields'))


class TestContentUnitNamedTuple(unittest.TestCase):
    def setUp(self):
        # Some ContentUnit test classes to test out the namedtuple generator
        self.first_helper = type(
            'FirstContentUnitHelper',
            (model.ContentUnit,),
            {'_content_type_id': StringField(default='foo'), 'unit_key_fields': ['apple', 'pear']}
        )
        self.second_helper = type(
            'SecondContentUnitHelper',
            (model.ContentUnit,),
            {'_content_type_id': StringField(default='bar'), 'unit_key_fields': ['lemon', 'lime']}
        )

        # mock out the descriptor cache to keep our dirty test classes contained
        cache_mock = patch.dict(model._ContentUnitNamedTupleDescriptor._cache, clear=True)
        cache_mock.start()
        self.addCleanup(cache_mock.stop)

    def test_values(self):
        # NAMED_TUPLE has the expected values
        self.assertEqual('foo', self.first_helper.NAMED_TUPLE.__name__)
        self.assertEqual(('apple', 'pear'), self.first_helper.NAMED_TUPLE._fields)

        # NAMED_TUPLE on a class with different values is also correct
        self.assertEqual('bar', self.second_helper.NAMED_TUPLE.__name__)
        self.assertEqual(('lemon', 'lime'), self.second_helper.NAMED_TUPLE._fields)

    def test_identity(self):
        # Multiple calls to NAMED_TUPLE return the same instance
        # This looks silly, but NAMED_TUPLE is a dynamic class property, so this makes sure the
        # cache is working properly by checking that the same objects are returned...
        self.assertTrue(self.first_helper.NAMED_TUPLE is self.first_helper.NAMED_TUPLE)
        self.assertTrue(self.second_helper.NAMED_TUPLE is self.second_helper.NAMED_TUPLE)

        # ...but the same objects aren't returned for different classes
        self.assertTrue(self.first_helper.NAMED_TUPLE is not self.second_helper.NAMED_TUPLE)

    def test_cache(self):
        # descriptor cache is only filled when NAMED_TUPLE is accessed...
        self.assertEqual(len(model._ContentUnitNamedTupleDescriptor._cache), 0)

        # ...and contains the expected objects when it is filled
        self.first_helper.NAMED_TUPLE
        self.assertEqual(len(model._ContentUnitNamedTupleDescriptor._cache), 1)
        self.assertTrue(self.first_helper in model._ContentUnitNamedTupleDescriptor._cache)

        self.second_helper.NAMED_TUPLE
        self.assertEqual(len(model._ContentUnitNamedTupleDescriptor._cache), 2)
        self.assertTrue(self.second_helper in model._ContentUnitNamedTupleDescriptor._cache)

    @patch('pulp.server.db.model.namedtuple')
    def test_namedtuple_call_counts(self, mock_namedtuple):
        # namedtuple itself isn't called until NAMED_TUPLE is accessed
        self.assertEqual(mock_namedtuple.call_count, 0)

        # multiple calls to the same property don't call namedtuple again
        self.first_helper.NAMED_TUPLE
        self.assertEqual(mock_namedtuple.call_count, 1)
        self.first_helper.NAMED_TUPLE
        self.assertEqual(mock_namedtuple.call_count, 1)

        # generating another namedtuple type results in another call
        self.second_helper.NAMED_TUPLE
        self.assertEqual(mock_namedtuple.call_count, 2)


class TestContentUnitValidateModelDefinition(unittest.TestCase):

    def test_clean_raises_nothing_if_properly_defined(self):
        class ContentUnitHelper(model.ContentUnit):
            _ns = StringField(default='dummy_content_name')
            _content_type_id = StringField(required=True, default='rpm')
            unit_key_fields = ('author', 'name', 'version')

        try:
            ContentUnitHelper.validate_model_definition()
        except Exception:
            self.fail("ContentUnitHelper is properly defined and should validate correctly")

    def test_clean_raises_ValidationError_when__content_type_id_field_is_not_defined(self):
        class ContentUnitHelper(model.ContentUnit):
            _ns = StringField(default='dummy_content_name')
            unit_key_fields = ('author', 'name', 'version')

        try:
            ContentUnitHelper.validate_model_definition()
        except PulpCodedException as raised_error:
            self.assertEquals(raised_error.error_code, error_codes.PLP0035)
            expected_dict = {'class_name': 'ContentUnitHelper', 'field_name': '_content_type_id'}
            self.assertEqual(raised_error.error_data, expected_dict)

    def test_clean_raises_ValidationError_when__content_type_id_field_is_wrong_type(self):
        class ContentUnitHelper(model.ContentUnit):
            _ns = StringField(default='dummy_content_name')
            _content_type_id = IntField(required=True, default=1)
            unit_key_fields = ('author', 'name', 'version')

        try:
            ContentUnitHelper.validate_model_definition()
        except PulpCodedException as raised_error:
            self.assertEquals(raised_error.error_code, error_codes.PLP0035)
            expected_dict = {'class_name': 'ContentUnitHelper', 'field_name': '_content_type_id'}
            self.assertEqual(raised_error.error_data, expected_dict)

    def test_clean_raises_ValidationError_when__content_type_id_field_default_is_not_defined(self):
        class ContentUnitHelper(model.ContentUnit):
            _ns = StringField(default='dummy_content_name')
            _content_type_id = StringField(required=True)
            unit_key_fields = ('author', 'name', 'version')

        try:
            ContentUnitHelper.validate_model_definition()
        except PulpCodedException as raised_error:
            self.assertEquals(raised_error.error_code, error_codes.PLP0035)
            expected_dict = {'class_name': 'ContentUnitHelper', 'field_name': '_content_type_id'}
            self.assertEqual(raised_error.error_data, expected_dict)

    def test_clean_raises_ValidationError_when__content_type_id_field_is_not_required(self):
        class ContentUnitHelper(model.ContentUnit):
            _ns = StringField(default='dummy_content_name')
            _content_type_id = StringField(default='rpm')
            unit_key_fields = ('author', 'name', 'version')

        try:
            ContentUnitHelper.validate_model_definition()
        except PulpCodedException as raised_error:
            self.assertEquals(raised_error.error_code, error_codes.PLP0035)
            expected_dict = {'class_name': 'ContentUnitHelper', 'field_name': '_content_type_id'}
            self.assertEqual(raised_error.error_data, expected_dict)

    def test_clean_raises_ValidationError_when_unit_key_fields_is_not_defined(self):
        class ContentUnitHelper(model.ContentUnit):
            _ns = StringField(default='dummy_content_name')
            _content_type_id = StringField(required=True, default='rpm')

        try:
            ContentUnitHelper.validate_model_definition()
        except PulpCodedException as raised_error:
            self.assertEquals(raised_error.error_code, error_codes.PLP0035)
            expected_dict = {'class_name': 'ContentUnitHelper', 'field_name': 'unit_key_fields'}
            self.assertEqual(raised_error.error_data, expected_dict)

    def test_clean_raises_ValidationError_when_unit_key_fields_is_wrong_type(self):
        class ContentUnitHelper(model.ContentUnit):
            _ns = StringField(default='dummy_content_name')
            _content_type_id = StringField(required=True, default='rpm')
            unit_key_fields = ListField(default=[1, 2, 3])

        try:
            ContentUnitHelper.validate_model_definition()
        except PulpCodedException as raised_error:
            self.assertEquals(raised_error.error_code, error_codes.PLP0035)
            expected_dict = {'class_name': 'ContentUnitHelper', 'field_name': 'unit_key_fields'}
            self.assertEqual(raised_error.error_data, expected_dict)

    def test_clean_raises_ValidationError_when_unit_key_fields_is_empty(self):
        class ContentUnitHelper(model.ContentUnit):
            _ns = StringField(default='dummy_content_name')
            _content_type_id = StringField(required=True, default='rpm')
            unit_key_fields = ()

        try:
            ContentUnitHelper.validate_model_definition()
        except PulpCodedException as raised_error:
            self.assertEquals(raised_error.error_code, error_codes.PLP0035)
            expected_dict = {'class_name': 'ContentUnitHelper', 'field_name': 'unit_key_fields'}
            self.assertEqual(raised_error.error_data, expected_dict)


class TestFileContentUnit(unittest.TestCase):

    class TestUnit(model.FileContentUnit):
        _content_type_id = StringField(default='')

    def test_pre_save_signal(self):
        document = Mock(_storage_path='')
        self.TestUnit.pre_save_signal(Mock(), document)
        document.set_storage_path.assert_called_once_with()

    def test_pre_save_signal_storage_path_already_set(self):
        document = Mock(_storage_path='123')
        self.TestUnit.pre_save_signal(Mock(), document)
        self.assertFalse(document.set_storage_path.called)

    def test_fields(self):
        self.assertTrue(isinstance(model.FileContentUnit.downloaded, BooleanField))
        self.assertEqual(model.FileContentUnit.downloaded.default, True)

    @patch('pulp.server.db.model.FileStorage.get_path')
    def test_set_storage_path(self, get_path):
        get_path.return_value = '/tmp'
        unit = TestFileContentUnit.TestUnit()
        unit.set_storage_path('test')
        self.assertEqual(unit._storage_path, '/tmp/test')

    @patch('pulp.server.db.model.FileStorage.get_path')
    def test_set_storage_path_no_filename(self, get_path):
        get_path.return_value = '/tmp'
        unit = TestFileContentUnit.TestUnit()
        unit.set_storage_path()
        self.assertEqual(unit._storage_path, '/tmp')

    @patch('pulp.server.db.model.FileStorage.get_path')
    def test_set_storage_path_absolute(self, get_path):
        get_path.return_value = '/tmp'
        unit = TestFileContentUnit.TestUnit()
        self.assertRaises(ValueError, unit.set_storage_path, '/violation/test')

    @patch('os.path.isdir')
    def test_list_files(self, isdir):
        isdir.return_value = False
        unit = TestFileContentUnit.TestUnit()
        unit._storage_path = '/some/dir/'
        self.assertEqual(unit.list_files(), [unit._storage_path])

    @patch('os.path.isdir')
    def test_list_files_no_path(self, isdir):
        isdir.return_value = False
        unit = TestFileContentUnit.TestUnit()
        self.assertEqual(unit.list_files(), [])

    @patch('os.path.isdir')
    def test_list_files_multi_file(self, isdir):
        isdir.return_value = True
        unit = TestFileContentUnit.TestUnit()
        self.assertEqual(unit.list_files(), [])

    @patch('os.path.isfile')
    @patch('pulp.server.db.model.FileStorage')
    def test_import_content(self, file_storage, isfile):
        path = '/tmp/working/file'
        isfile.return_value = True
        storage = Mock()
        storage.__enter__ = Mock(return_value=storage)
        storage.__exit__ = Mock()
        file_storage.return_value = storage

        # test
        unit = TestFileContentUnit.TestUnit()
        unit._last_updated = 1234
        unit.import_content(path)

        # validation
        file_storage.assert_called_once_with()
        storage.__enter__.assert_called_once_with()
        storage.__exit__.assert_called_once_with(None, None, None)
        storage.put.assert_called_once_with(unit, path, None)

    @patch('os.path.isfile')
    @patch('pulp.server.db.model.FileStorage')
    def test_import_content_with_location(self, file_storage, isfile):
        path = '/tmp/working/file'
        location = 'a/b'
        isfile.return_value = True
        storage = Mock()
        storage.__enter__ = Mock(return_value=storage)
        storage.__exit__ = Mock()
        file_storage.return_value = storage

        # test
        unit = TestFileContentUnit.TestUnit()
        unit._last_updated = 1234
        unit.import_content(path, location)

        # validation
        file_storage.assert_called_once_with()
        storage.__enter__.assert_called_once_with()
        storage.__exit__.assert_called_once_with(None, None, None)
        storage.put.assert_called_once_with(unit, path, location)

    def test_import_content_unit_not_saved(self):
        try:
            unit = TestFileContentUnit.TestUnit()
            unit.import_content('')
            self.fail('Expected coded exception')
        except PulpCodedException, e:
            self.assertEqual(e.error_code, PLP0036)

    @patch('os.path.isfile')
    def test_import_content_not_existing_file(self, isfile):
        isfile.return_value = False
        try:
            unit = TestFileContentUnit.TestUnit()
            unit._last_updated = 1234
            unit.import_content('')
            self.fail('Expected coded exception')
        except PulpCodedException, e:
            self.assertEqual(e.error_code, PLP0037)


class TestSharedContentUnit(unittest.TestCase):

    class TestUnit(model.SharedContentUnit):
        pass

    def test_abstract(self):
        unit = TestSharedContentUnit.TestUnit()
        self.assertRaises(NotImplementedError, getattr, unit, 'storage_provider')
        self.assertRaises(NotImplementedError, getattr, unit, 'storage_id')

    @patch('pulp.server.db.model.SharedStorage.link')
    @patch('pulp.server.db.model.SharedStorage.open')
    @patch('pulp.server.db.model.SharedStorage.close')
    @patch('pulp.server.db.model.SharedContentUnit.storage_provider', 'git')
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
        self.assertTrue(issubclass(model.Worker.objects.__class__, QuerySetNoCache))


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
        self.assertEqual(model.MigrationTracker.version.default, -1)

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
        self.assertEquals(repo_obj, repo.repo_obj)

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


class TestImporter(unittest.TestCase):
    """
    Tests for the importer class.
    """
    def test_model_superclass(self):
        """
        Ensure that the class is a Mongoengine Document.
        """
        sample_model = model.Importer()
        self.assertTrue(isinstance(sample_model, Document))

    def test_attributes(self):
        """
        Ensure the attributes are the correct type and they have the correct values.
        """
        self.assertTrue(isinstance(model.Importer.repo_id, StringField))
        self.assertTrue(model.Importer.repo_id.required)
        self.assertTrue(isinstance(model.Importer.importer_type_id, StringField))
        self.assertTrue(model.Importer.importer_type_id.required)
        self.assertTrue(isinstance(model.Importer.config, DictField))
        self.assertFalse(model.Importer.config.required)
        self.assertTrue(isinstance(model.Importer._ns, StringField))
        self.assertEquals(model.Importer._ns.default, 'repo_importers')

    def test_serializer(self):
        """
        Ensure that the serializer is set.
        """
        self.assertEqual(model.Importer.SERIALIZER, serializers.ImporterSerializer)

    def test_meta_collection(self):
        """
        Assert that the collection name is correct.
        """
        self.assertEquals(model.Importer._meta['collection'], 'repo_importers')

    def test_meta_allow_inheritance(self):
        """
        Ensure that inheritance is not allowed.
        """
        self.assertEquals(model.Importer._meta['allow_inheritance'], False)

    def test_meta_allow_indexes(self):
        """
        Test that the indexes are set correctly.
        """
        indexes = model.Importer._meta['indexes']
        self.assertDictEqual(
            indexes[0], {'fields': ['-repo_id', '-importer_type_id'], 'unique': True})

    @patch('pulp.server.db.model.LazyCatalogEntry.objects')
    def test_pre_delete(self, mock_lazy):
        """Assert that the pre_delete signal deletes lazy catalog entries."""
        model.Importer.pre_delete(None, Mock(id='fake'))
        mock_lazy.assert_called_once_with(importer_id='fake')
        mock_lazy.return_value.delete.assert_called_once_with()

    def test_pre_delete_connect(self):
        self.assertTrue(model.signals.pre_delete.has_receivers_for(model.Importer))


class TestDistributor(unittest.TestCase):
    """
    Tests for the distributor model.
    """
    def test_model_superclass(self):
        """
        Ensure that the class is a Mongoengine Document.
        """
        sample_model = model.Distributor()
        self.assertTrue(isinstance(sample_model, Document))

    def test_attributes(self):
        """
        Ensure the attributes are the correct type and they have the correct values.
        """
        self.assertTrue(isinstance(model.Distributor.repo_id, StringField))
        self.assertTrue(model.Distributor.repo_id.required)
        self.assertTrue(isinstance(model.Distributor.distributor_id, StringField))
        self.assertTrue(model.Distributor.distributor_id.required)
        self.assertTrue(isinstance(model.Distributor.distributor_type_id, StringField))
        self.assertTrue(model.Distributor.distributor_type_id.required)
        self.assertTrue(isinstance(model.Distributor.config, DictField))
        self.assertFalse(model.Distributor.config.required)
        self.assertTrue(isinstance(model.Distributor.auto_publish, BooleanField))
        self.assertEqual(model.Distributor.auto_publish.default, False)
        self.assertTrue(isinstance(model.Distributor.last_publish, DateTimeField))
        self.assertFalse(model.Distributor.last_publish.required)
        self.assertTrue(isinstance(model.Distributor._ns, StringField))
        self.assertEqual(model.Distributor._ns.default, 'repo_distributors')
        self.assertTrue(isinstance(model.Distributor.scratchpad, DictField))
        self.assertFalse(model.Distributor.scratchpad.required)

    def test_serializer(self):
        """
        Ensure that the serializer is set.
        """
        self.assertEqual(model.Distributor.SERIALIZER, serializers.Distributor)

    def test_meta_collection(self):
        """
        Assert that the collection name is correct.
        """
        self.assertEquals(model.Distributor._meta['collection'], 'repo_distributors')

    def test_meta_allow_inheritance(self):
        """
        Ensure that inheritance is not allowed.
        """
        self.assertEquals(model.Distributor._meta['allow_inheritance'], False)

    def test_meta_indexes(self):
        """
        Test that the indexes are set correctly.
        """
        indexes = model.Distributor._meta['indexes']
        self.assertDictEqual(
            indexes[0], {'fields': ['-repo_id', '-distributor_id'], 'unique': True})


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

        self.assertTrue(isinstance(model.CeleryBeatLock.timestamp, DateTimeField))
        self.assertTrue(model.CeleryBeatLock.timestamp.required)

        self.assertTrue(isinstance(model.CeleryBeatLock.lock, StringField))
        self.assertTrue(model.CeleryBeatLock.lock.required)
        self.assertTrue(model.CeleryBeatLock.lock.default, 'locked')
        self.assertTrue(model.CeleryBeatLock.lock.unique)

        self.assertTrue('_ns' in model.CeleryBeatLock._fields)

    def test_meta_collection(self):
        """
        Assert that the collection name is correct.
        """
        self.assertEquals(model.CeleryBeatLock._meta['collection'], 'celery_beat_lock')


class TestLazyCatalogEntry(unittest.TestCase):
    """
    Test the LazyCatalogEntry class.
    """
    COLLECTION_NAME = 'lazy_content_catalog'

    def test_model_superclass(self):
        sample_model = model.LazyCatalogEntry()
        self.assertTrue(isinstance(sample_model, model.AutoRetryDocument))

    def test_attributes(self):
        self.assertTrue(isinstance(model.LazyCatalogEntry.path, StringField))
        self.assertTrue(model.LazyCatalogEntry.path.required)

        self.assertTrue(isinstance(model.LazyCatalogEntry.importer_id, StringField))
        self.assertTrue(model.LazyCatalogEntry.importer_id.required)

        self.assertTrue(isinstance(model.LazyCatalogEntry.unit_id, StringField))
        self.assertTrue(model.LazyCatalogEntry.unit_id.required)

        self.assertTrue(isinstance(model.LazyCatalogEntry.unit_type_id, StringField))
        self.assertTrue(model.LazyCatalogEntry.unit_type_id.required)

        self.assertTrue(isinstance(model.LazyCatalogEntry.checksum, StringField))
        self.assertFalse(model.LazyCatalogEntry.checksum.required)

        self.assertTrue(isinstance(model.LazyCatalogEntry.checksum_algorithm, StringField))
        self.assertFalse(model.LazyCatalogEntry.checksum_algorithm.required)

        self.assertTrue(isinstance(model.LazyCatalogEntry.revision, IntField))
        self.assertFalse(model.LazyCatalogEntry.revision.required)

        self.assertTrue(isinstance(model.LazyCatalogEntry.data, DictField))
        self.assertFalse(model.LazyCatalogEntry.data.required)

        self.assertTrue(isinstance(model.LazyCatalogEntry._ns, StringField))
        self.assertEqual(self.COLLECTION_NAME, model.LazyCatalogEntry._ns.default)

    def test_indexes(self):
        expected = [
            [('importer_id', 1)],
            [('path', -1), ('importer_id', -1), ('revision', -1)],
            [(u'_id', 1)]
        ]
        result = model.LazyCatalogEntry.list_indexes()
        self.assertEqual(expected, result)

    def test_meta_collection(self):
        self.assertEquals(model.LazyCatalogEntry._meta['collection'], self.COLLECTION_NAME)

    @patch('pulp.server.db.model.LazyCatalogEntry.save')
    @patch('pulp.server.db.model.LazyCatalogEntry.objects')
    def test_save_revision(self, objects, save):
        qs = Mock()
        qs.distinct.return_value = [1]
        objects.filter.return_value = qs
        entry = model.LazyCatalogEntry()
        entry.unit_id = '123'
        entry.unit_type_id = 'test'
        entry.importer_id = '44'
        entry.path = '/no/where'

        # test
        entry.save_revision()

        # validation
        self.assertEqual(
            objects.filter.call_args_list,
            [
                call(unit_id=entry.unit_id,
                     unit_type_id=entry.unit_type_id,
                     importer_id=entry.importer_id,
                     path=entry.path),
                call(revision__in=set([0, 1]),
                     unit_id=entry.unit_id,
                     unit_type_id=entry.unit_type_id,
                     importer_id=entry.importer_id,
                     path=entry.path),
            ])
        self.assertEqual(entry.revision, 2)
        save.assert_called_once_with()
        qs.delete.assert_called_once_with()


class TestDeferredDownload(unittest.TestCase):
    """
    Test the DeferredDownload class.
    """

    def test_model_superclass(self):
        sample_model = model.DeferredDownload()
        self.assertTrue(isinstance(sample_model, model.AutoRetryDocument))

    def test_attributes(self):
        self.assertTrue(isinstance(model.DeferredDownload.unit_id, StringField))
        self.assertTrue(model.DeferredDownload.unit_id.required)

        self.assertTrue(isinstance(model.DeferredDownload.unit_type_id, StringField))
        self.assertTrue(model.DeferredDownload.unit_type_id.required)

        self.assertTrue(isinstance(model.DeferredDownload._ns, StringField))
        self.assertEqual('deferred_download', model.DeferredDownload._ns.default)

    def test_indexes(self):
        result = model.DeferredDownload.list_indexes()
        self.assertEqual([[('unit_id', 1), ('unit_type_id', 1)], [(u'_id', 1)]], result)

    def test_meta_collection(self):
        """
        Assert that the collection name is correct.
        """
        self.assertEquals(model.DeferredDownload._meta['collection'], 'deferred_download')


class TestUser(unittest.TestCase):
    """
    Tests for the User model.
    """

    def test_model_superclass(self):
        """
        Ensure that the model inherrits from Mongoengine Document.
        """
        sample_model = model.CeleryBeatLock()
        self.assertTrue(isinstance(sample_model, Document))

    def test_no_cache_query_set(self):
        """Ensure the QuerySet class is the non-caching variety."""
        self.assertTrue(issubclass(model.User.objects.__class__,
                                   QuerySetNoCache))

    def test_attributes(self):
        self.assertTrue(isinstance(model.User.login, StringField))
        self.assertTrue(model.User.login.required)

        self.assertTrue(isinstance(model.User.name, StringField))
        self.assertFalse(model.User.name.required)

        self.assertTrue(isinstance(model.User.password, StringField))
        self.assertFalse(model.User.password.required)

        self.assertTrue(isinstance(model.User.roles, ListField))

    def test_meta_collection(self):
        """
        Assert that the collection name is correct.
        """
        self.assertEquals(model.User._meta['collection'], 'users')

    def test_meta_allow_inheritance(self):
        """
        Ensure that inheritance is not allowed.
        """
        self.assertEquals(model.User._meta['allow_inheritance'], False)

    def test_meta_allow_indexes(self):
        """
        Test that the indexes are set correctly.
        """
        indexes = model.User._meta['indexes']
        self.assertDictEqual(indexes[1], {'fields': ['-login', '-name'], 'unique': True})
        self.assertEqual(indexes[0], '-roles')

    def test_queryset(self):
        """
        Test that the model can search with criteria.
        """
        self.assertEqual(model.User._meta['queryset_class'], CriteriaQuerySet)
        self.assertTrue(issubclass(model.Worker.objects.__class__, QuerySetNoCache))


class TestUserAuth(unittest.TestCase):
    """
    Test password and superuser methods of the User model.
    """

    def setUp(self):
        """
        Create a base User.
        """
        self.user = model.User(login='test', password='some password')

    def test_password_integrated(self):
        """
        Test the password setting and checking end to end.
        """
        self.user.set_password('mock_password')
        self.assertTrue(self.user.check_password('mock_password'))
        self.user.set_password('new_password')
        self.assertFalse(self.user.check_password('mock_password'))

    def test_set_password_integrated(self):
        """
        Test setting password end to end.
        """
        password = "some password"
        self.user.set_password(password)
        self.assertNotEqual(self.user.password, password)

    @patch('pulp.server.db.model.User._hash_password')
    def test_set_password(self, mock_hash):
        """
        Test setting a password.
        """
        password = "some password"
        self.user.set_password(password)
        self.assertEqual(self.user.password, mock_hash.return_value)

    @patch('pulp.server.db.model.User._hash_password')
    def test_set_password_not_string(self, mock_hash):
        """
        Test setting a password.
        """
        password = 1
        self.assertRaises(exceptions.InvalidValue, self.user.set_password, password)

    @patch('pulp.server.db.model.User._pbkdf_sha256')
    @patch('pulp.server.db.model.User._random_bytes')
    def test_hash_password(self, mock_rand, mock_sha):
        """
        Test hashing a password.
        """
        password = "some password"
        mock_rand.return_value.encode.return_value.strip.return_value = 'mock_salt'
        mock_sha.return_value.encode.return_value.strip.return_value = 'mock_hash'
        salted = self.user._hash_password(password)
        self.assertEqual(salted, 'mock_salt,mock_hash')

    @patch('pulp.server.db.model.random')
    def test_rand_bytes(self, mock_rand):
        """
        Test building a salt.
        """
        mock_rand.randrange.return_value = 52  # Guaranteed random number xkcd.com/221/
        self.assertEqual(self.user._random_bytes(4), '4444')

    @patch('pulp.server.db.model.digestmod')
    @patch('pulp.server.db.model.HMAC')
    def test_pbkdf_sha256(self, mock_hmac, mock_digest):
        """
        Test use of HMAC library to do the hashing under the hood.
        """
        hashed = self.user._pbkdf_sha256('password', 'salt', 1)
        self.assertTrue(hashed is mock_hmac.return_value.digest.return_value)
        mock_hmac.assert_called_once_with('password', 'salt', mock_digest)

    def test_is_superuser(self):
        """
        Test determining if the user is a super user.
        """
        self.user.roles = ['one role']
        self.assertFalse(self.user.is_superuser())
        self.user.roles = ['one role', model.SUPER_USER_ROLE]
        self.assertTrue(self.user.is_superuser())


class SystemUser(unittest.TestCase):
    """
    Tests for the system user (no user is logged in)
    """

    def test_init(self):
        """
        Make sure the SystemUser has the correct attributes.
        """
        sys_user = model.SystemUser()
        self.assertEqual(sys_user.login, model.SYSTEM_LOGIN)
        self.assertEqual(sys_user.password, None)
        self.assertEqual(sys_user.name, model.SYSTEM_LOGIN)
        self.assertEqual(sys_user.roles, [])
        self.assertEqual(sys_user._id, model.SYSTEM_ID)
        self.assertEqual(sys_user.id, model.SYSTEM_ID)

    def test_singleton(self):
        """
        Since it is a singleton, all instances should be the same.
        """
        sys_u_1 = model.SystemUser()
        sys_u_2 = model.SystemUser()
        self.assertTrue(sys_u_1 is sys_u_2)
