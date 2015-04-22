import errno
import os
import unittest

import mock

from pulp.server.db.connection import PulpCollection
from pulp.server.db.model.criteria import Criteria
from pulp.server.managers.content.query import ContentQueryManager
from test_cud import PulpContentTests, TYPE_1_DEF, TYPE_1_UNITS, TYPE_2_DEF, TYPE_2_UNITS


class PulpContentQueryTests(PulpContentTests):

    def setUp(self):
        super(PulpContentQueryTests, self).setUp()
        self.type_1_ids = []
        self.type_2_ids = []
        for unit in TYPE_1_UNITS:
            unit_id = self.cud_manager.add_content_unit(TYPE_1_DEF.id, None, unit)
            self.type_1_ids.append(unit_id)
        for unit in TYPE_2_UNITS:
            unit_id = self.cud_manager.add_content_unit(TYPE_2_DEF.id, None, unit)
            self.type_2_ids.append(unit_id)

    def test_get_content_unit_collection(self):
        manager = ContentQueryManager()
        collection = manager.get_content_unit_collection('deb')
        self.assertTrue(isinstance(collection, PulpCollection))
        self.assertEqual(collection.name, 'units_deb')

    @mock.patch.object(ContentQueryManager, 'get_content_unit_collection')
    def test_find_by_criteria(self, mock_get_collection):
        criteria = Criteria(limit=20)
        units = self.query_manager.find_by_criteria('deb', criteria)

        # make sure it tried to get the correct collection
        mock_get_collection.assert_called_once_with('deb')

        # make sure the query call itself was correct
        mock_query = mock_get_collection.return_value.query
        self.assertEqual(mock_query.call_count, 1)
        self.assertEqual(mock_query.call_args[0][0], criteria)
        self.assertEqual(mock_query.return_value, units)

    def test_list(self):
        units = self.query_manager.list_content_units(TYPE_1_DEF.id)
        self.assertEqual(len(TYPE_1_UNITS), len(units))
        units = self.query_manager.list_content_units(TYPE_2_DEF.id)
        self.assertEqual(len(TYPE_2_UNITS), len(units))

    def test_get_by_id(self):
        unit = self.query_manager.get_content_unit_by_id(TYPE_1_DEF.id, self.type_1_ids[0])
        self.assertEqual(unit['key-1'], TYPE_1_UNITS[0]['key-1'])

    def test_get_by_ids(self):
        units = self.query_manager.get_multiple_units_by_ids(TYPE_2_DEF.id, self.type_2_ids)
        self.assertEqual(len(units), len(self.type_2_ids))

    def test_key_dict(self):
        unit_ids, unit_keys = self.query_manager.get_content_unit_keys(TYPE_2_DEF.id,
                                                                       [self.type_2_ids[0]])
        self.assertEqual(len(unit_keys), 1)
        unit_id = unit_ids[0]
        unit_dict = unit_keys[0]
        unit_model = TYPE_2_UNITS[0]
        self.assertEqual(unit_id, self.type_2_ids[0])
        self.assertEqual(unit_dict['key-2a'], unit_model['key-2a'])
        self.assertEqual(unit_dict['key-2b'], unit_model['key-2b'])

    def test_get_by_key_dict(self):
        key_dict = self.query_manager.get_content_unit_keys(
            TYPE_2_DEF.id, [self.type_2_ids[0]])[1][0]
        unit = self.query_manager.get_content_unit_by_keys_dict(TYPE_2_DEF.id, key_dict)
        self.assertEqual(unit['_id'], self.type_2_ids[0])

    def test_multi_key_dicts(self):
        ids, key_dicts = self.query_manager.get_content_unit_keys(TYPE_2_DEF.id, self.type_2_ids)
        units = list(self.query_manager.get_multiple_units_by_keys_dicts(TYPE_2_DEF.id, key_dicts))
        self.assertEqual(len(units), len(self.type_2_ids))

    def __test_keys_dicts_query(self):
        # XXX this test proves my multi-dict query wrong, need to fix it
        new_unit = {'key-2a': 'B', 'key-2b': 'B'}
        self.cud_manager.add_content_unit(TYPE_2_DEF.id, None, new_unit)
        keys_dicts = TYPE_2_UNITS[1:3]
        units = self.query_manager.get_multiple_units_by_keys_dicts(TYPE_2_DEF.id, keys_dicts)
        self.assertEqual(len(units), 2)

    @mock.patch('pulp.server.managers.content.upload.os.makedirs')
    @mock.patch.object(ContentQueryManager, 'get_root_content_dir')
    def test_request_content_unit_file_path_exists(self, mock_root_dir, mock_makedirs):
        mock_root_dir.return_value = '/var/lib/pulp/content/rpm/'
        mock_makedirs.side_effect = OSError(errno.EEXIST, os.strerror(errno.EEXIST))
        ContentQueryManager().request_content_unit_file_path('rpm', '/name/blah')
        mock_makedirs.assert_called_once_with('/var/lib/pulp/content/rpm/name')

    @mock.patch('pulp.server.managers.content.upload.os.makedirs')
    @mock.patch.object(ContentQueryManager, 'get_root_content_dir')
    def test_request_content_unit_file_path_random_os_error(self, mock_root_dir, mock_makedirs):
        mock_root_dir.return_value = '/var/lib/pulp/content/rpm/'
        mock_makedirs.side_effect = OSError(errno.EACCES, os.strerror(errno.EACCES))
        self.assertRaises(OSError, ContentQueryManager().request_content_unit_file_path, 'rpm',
                          '/name/blah')
        mock_makedirs.assert_called_once_with('/var/lib/pulp/content/rpm/name')

    @mock.patch('pulp.server.managers.content.upload.os.makedirs')
    @mock.patch.object(ContentQueryManager, 'get_root_content_dir')
    def test_request_content_unit_file_path_no_error(self, mock_root_dir, mock_makedirs):
        mock_root_dir.return_value = '/var/lib/pulp/content/rpm/'
        mock_makedirs.return_value = '/var/lib/pulp/content/rpm/name'
        ContentQueryManager().request_content_unit_file_path('rpm', '/name/blah')
        mock_makedirs.assert_called_once_with('/var/lib/pulp/content/rpm/name')


@mock.patch('pulp.plugins.types.database.type_units_unit_key', return_value=['a'])
@mock.patch('pulp.plugins.types.database.type_units_collection')
class TestGetContentUnitIDs(unittest.TestCase):
    def setUp(self):
        super(TestGetContentUnitIDs, self).setUp()
        self.manager = ContentQueryManager()

    def test_returns_generator(self, mock_type_collection, mock_type_unit_key):
        mock_type_collection.return_value.find.return_value = []

        ret = self.manager.get_content_unit_ids('fake_type', [])

        self.assertTrue(inspect.isgenerator(ret))

    def test_returns_ids(self, mock_type_collection, mock_type_unit_key):
        mock_type_collection.return_value.find.return_value = [{'_id': 'abc'}, {'_id': 'def'}]

        ret = self.manager.get_content_unit_ids('fake_type', [{'a': 'foo'}, {'a': 'bar'}])

        self.assertEqual(list(ret), ['abc', 'def'])

    def test_calls_find(self, mock_type_collection, mock_type_unit_key):
        mock_find = mock_type_collection.return_value.find
        mock_find.return_value = [{'_id': 'abc'}, {'_id': 'def'}]

        ret = self.manager.get_content_unit_ids('fake_type', [{'a': 'foo'}, {'a': 'bar'}])

        # evaluate the generator so the code actually runs
        list(ret)
        expected_spec = {'$or': ({'a': 'foo'}, {'a': 'bar'})}
        mock_find.assert_called_once_with(expected_spec, fields=['_id'])
