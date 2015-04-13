"""
This module contains tests for pulp.server.db.migrations.0015_load_content_types.
"""
import unittest
from mock import Mock, call, patch

from pulp.server.db.migrate.models import _import_all_the_way

migration = _import_all_the_way('pulp.server.db.migrations.'
                                '0016_remove_repo_content_unit_owner_type_and_id')


class TestMigrate(unittest.TestCase):

    @patch.object(migration.connection, 'get_database')
    def test_migrate_no_collection_in_db(self, mock_get_database):
        """
        Test doing nothing, no actual tests since if it tries to do any work it will raise
        """
        mock_get_database.return_value.collection_names.return_value = []
        migration.migrate()

    @patch.object(migration.connection, 'get_database')
    @patch.object(migration, 'remove_duplicates')
    def test_migrate_removes_duplicates(self, mock_remove_duplicates, mock_get_database):
        """
        Test that the migration calls the remove_duplicates method & drops the
        owner_type and owner_id fields from the repo_content_units collection
        """
        mock_get_database.return_value.collection_names.return_value = ['repo_content_units']
        collection = mock_get_database.return_value['repo_content_units']
        migration.migrate()

        mock_remove_duplicates.assert_called_once_with(collection)
        collection.update.assert_called_once_with(
            {}, {'$unset': {'owner_type': "", 'owner_id': ''}}, multi=True)

    @patch.object(migration.connection, 'get_database')
    @patch.object(migration, 'remove_duplicates')
    def test_migrate_removes_index(self, mock_remove_duplicates, mock_get_database):
        """
        Test that the migration removes the index if it has been created
        """
        mock_get_database.return_value.collection_names.return_value = ['repo_content_units']
        collection = mock_get_database.return_value['repo_content_units']
        collection.index_information.return_value = \
            ["repo_id_-1_unit_type_id_-1_unit_id_-1_owner_type_-1_owner_id_-1"]

        migration.migrate()

        collection.drop_index.assert_called_once_with(
            "repo_id_-1_unit_type_id_-1_unit_id_-1_owner_type_-1_owner_id_-1")

    @patch.object(migration.connection, 'get_database')
    @patch.object(migration, 'remove_duplicates')
    def test_migrate_no_index(self, mock_remove_duplicates, mock_get_database):
        """
        Test that the migration does not drop the index if it does not exist
        """
        mock_get_database.return_value.collection_names.return_value = ['repo_content_units']
        collection = mock_get_database.return_value['repo_content_units']
        migration.migrate()
        self.assertFalse(collection.drop_index.called)

    def test_remove_duplicates_no_units(self):
        """
        Test removing duplicates of there are no units
        """
        mock_collection = Mock()
        mock_collection.find.return_value = []

        migration.remove_duplicates(mock_collection)

        self.assertFalse(mock_collection.remove.called)

    def test_remove_duplicates_no_duplicate(self):
        """
        Test removing duplicates of there are no duplicate units
        """
        mock_collection = Mock()
        mock_collection.find.return_value = [
            {'_id': 1, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'baz'},
            {'_id': 2, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'qux'},
            {'_id': 3, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'foo'}
        ]

        migration.remove_duplicates(mock_collection)

        self.assertFalse(mock_collection.remove.called)

    def test_remove_duplicates_one_duplicate(self):
        """
        Test removing duplicates of there is a single duplicated unit
        """
        mock_collection = Mock()
        mock_collection.find.return_value = [
            {'_id': 1, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'baz'},
            {'_id': 2, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'baz'},
            {'_id': 3, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'foo'}
        ]

        migration.remove_duplicates(mock_collection)
        mock_collection.remove.assert_called_once_with({'_id': {'$in': [1]}})

    def test_remove_duplicates_one_duplicate_many(self):
        """
        Test removing duplicates of there is a single duplicated unit with many duplicates
        """
        mock_collection = Mock()
        mock_collection.find.return_value = [
            {'_id': 1, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'baz'},
            {'_id': 2, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'baz'},
            {'_id': 4, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'baz'},
            {'_id': 3, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'foo'}
        ]

        migration.remove_duplicates(mock_collection)
        mock_collection.remove.assert_called_once_with({'_id': {'$in': [1, 2]}})

    def test_remove_duplicates_multiple_duplicates(self):
        """
        Test removing duplicates of there are multiple duplicated units
        """
        mock_collection = Mock()
        mock_collection.find.return_value = [
            {'_id': 1, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'baz'},
            {'_id': 2, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'baz'},
            {'_id': 4, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'foo'},
            {'_id': 3, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'foo'}
        ]

        migration.remove_duplicates(mock_collection)
        mock_collection.remove.assert_called_once_with({'_id': {'$in': [1, 4]}})

    def test_remove_duplicates_creates_and_removes_indexes(self):
        mock_collection = Mock()
        mock_collection.find.return_value = []
        migration.remove_duplicates(mock_collection)
        mock_collection.ensure_index.assert_called_once_with([('repo_id', -1),
                                                              ('unit_type_id', -1),
                                                              ('unit_id', -1),
                                                              ('updated', -1)])
        mock_collection.drop_index.assert_called_once_with(
            'repo_id_-1_unit_type_id_-1_unit_id_-1_updated_-1')

    def test_remove_duplicates_batch_remove(self):
        """
        Test removing > 100 duplicates batches the removes in to groups of 100
        """
        mock_collection = Mock()
        unit_list = []
        for i in range(110):
            unit_list.extend([
                {'_id': i, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'baz%s' % i},
                {'_id': '%s-a' % i, 'repo_id': 'foo', 'unit_type_id': 'bar', 'unit_id': 'baz%s' % i}
            ])

        mock_collection.find.return_value = unit_list

        migration.remove_duplicates(mock_collection)
        calls = [call({'_id': {'$in': list(range(101))}}),
                 call({'_id': {'$in': list(range(101, 110))}})]
        mock_collection.remove.assert_has_calls(calls)
