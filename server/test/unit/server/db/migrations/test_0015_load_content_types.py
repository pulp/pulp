"""
This module contains tests for pulp.server.db.migrations.0015_load_content_types.
"""
from cStringIO import StringIO
import unittest

from mock import inPy3k, MagicMock, patch

from pulp.common.compat import json
from pulp.server.db.migrate.models import _import_all_the_way
import pulp.plugins.types.database as types_db


# This is used for mocking
_test_type_json = '''{"types": [{
    "id" : "test_type_id",
    "display_name" : "Test Type",
    "description" : "Test Type",
    "unit_key" : ["attribute_1", "attribute_2", "attribute_3"],
    "search_indexes" : ["attribute_1", "attribute_3"]
}]}'''


# Mock 1.0.0 has a built in mock_open, and one day when we upgrade to 1.0.0 we can use that. In the
# meantime, I've included the example for mock_open as listed in the Mock 0.8 docs, slightly
# modified to allow read_data to just be a str.
# http://www.voidspace.org.uk/python/mock/0.8/examples.html?highlight=open#mocking-open
if inPy3k:
    file_spec = [
        '_CHUNK_SIZE', '__enter__', '__eq__', '__exit__',
        '__format__', '__ge__', '__gt__', '__hash__', '__iter__', '__le__',
        '__lt__', '__ne__', '__next__', '__repr__', '__str__',
        '_checkClosed', '_checkReadable', '_checkSeekable',
        '_checkWritable', 'buffer', 'close', 'closed', 'detach',
        'encoding', 'errors', 'fileno', 'flush', 'isatty',
        'line_buffering', 'mode', 'name',
        'newlines', 'peek', 'raw', 'read', 'read1', 'readable',
        'readinto', 'readline', 'readlines', 'seek', 'seekable', 'tell',
        'truncate', 'writable', 'write', 'writelines']
else:
    file_spec = file


def mock_open(mock=None, read_data=None):
    if mock is None:
        mock = MagicMock(spec=file_spec)

    handle = MagicMock(spec=file_spec)
    handle.write.return_value = None
    fake_file = StringIO(read_data)
    if read_data is None:
        if hasattr(handle, '__enter__'):
            handle.__enter__.return_value = handle
    else:
        if hasattr(handle, '__enter__'):
            handle.__enter__.return_value = fake_file
        handle.read = fake_file.read
    mock.return_value = handle
    return mock

migration = _import_all_the_way('pulp.server.db.migrations.0015_load_content_types')


class TestMigrate(unittest.TestCase):
    @patch('pulp.plugins.types.database._drop_indexes')
    @patch('__builtin__.open', mock_open(read_data=_test_type_json))
    @patch('os.listdir', return_value=['test_type.json'])
    @patch('sys.argv', ["pulp-manage-db"])
    @patch('sys.stdout', MagicMock())
    @patch('pulp.server.db.manage._start_logging')
    def test_migrate(self, start_logging_mock, listdir_mock, mock_drop_indices):
        """
        Ensure that migrate() imports types on a clean types database.
        """
        migration.migrate()
        self.assertTrue(mock_drop_indices.called)

        all_collection_names = types_db.all_type_collection_names()
        self.assertEqual(len(all_collection_names), 1)

        self.assertEqual(['units_test_type_id'], all_collection_names)

        # Let's make sure we loaded the type definitions correctly
        db_type_definitions = types_db.all_type_definitions()
        self.assertEquals(len(db_type_definitions), 1)
        test_json = json.loads(_test_type_json)
        for attribute in ['id', 'display_name', 'description', 'unit_key', 'search_indexes']:
            self.assertEquals(test_json['types'][0][attribute], db_type_definitions[0][attribute])

        # Now let's ensure that we have the correct indexes
        collection = types_db.type_units_collection('test_type_id')
        indexes = collection.index_information()
        self.assertEqual(indexes['_id_']['key'], [(u'_id', 1)])
        # Make sure we have the unique constraint on all three attributes
        self.assertEqual(indexes['attribute_1_1_attribute_2_1_attribute_3_1']['unique'], True)
        self.assertEqual(indexes['attribute_1_1_attribute_2_1_attribute_3_1']['key'],
                         [(u'attribute_1', 1), (u'attribute_2', 1), (u'attribute_3', 1)])
        # Make sure we indexed attributes 1 and 3
        self.assertEqual(indexes['attribute_1_1']['key'], [(u'attribute_1', 1)])
        self.assertEqual(indexes['attribute_3_1']['key'], [(u'attribute_3', 1)])
        # Make sure we only have the indexes that we've hand inspected here
        self.assertEqual(indexes.keys(), [u'_id_', u'attribute_1_1_attribute_2_1_attribute_3_1',
                                          u'attribute_1_1', u'attribute_3_1'])
