"""
This module contains tests for pulp.server.db.migrations.0018_remove_archived_calls.
"""
import unittest

from mock import patch

from pulp.server.db.migrate.models import _import_all_the_way

migration = _import_all_the_way('pulp.server.db.migrations.0018_remove_archived_calls')


class TestMigrate(unittest.TestCase):
    """
    Test the migrate() function.
    """

    @patch.object(migration.connection, 'get_database')
    def test_migrate_no_collection_archived_calls(self, mock_get_database):
        """
        Assert that drop is not called when archived_calls is not present in the db
        """

        mock_get_database.return_value.collection_names.return_value = []
        collection = mock_get_database.return_value['archived_calls']
        migration.migrate()
        self.assertFalse(collection.drop.called)

    @patch.object(migration.connection, 'get_database')
    def test_migrate_collection_present_archived_calls(self, mock_get_database):
        """
        Assert that drop is called when archived_calls is present in the db
        """

        mock_get_database.return_value.collection_names.return_value = ['archived_calls']
        collection = mock_get_database.return_value['archived_calls']
        migration.migrate()
        self.assertTrue(collection.drop.called)
