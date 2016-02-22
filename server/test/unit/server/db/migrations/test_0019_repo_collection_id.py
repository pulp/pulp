"""
This module contains tests for pulp.server.db.migrations.0019_repo_collection_id.py
"""
import unittest

from mock import patch

from pulp.server.db.migrate.models import _import_all_the_way

migration = _import_all_the_way('pulp.server.db.migrations.0019_repo_collection_id')


class TestMigrate(unittest.TestCase):
    """
    Test the migrate() function.
    """

    @patch.object(migration.connection, 'get_database')
    def test_repos_collection_id_renamed(self, mock_get_database):
        mock_get_database.return_value.collection_names.return_value = []
        collection = mock_get_database.return_value['archived_calls']
        migration.migrate()
        collection.update.assert_called_once_with({}, {"$rename": {"id": "repo_id"}}, multi=True)
        collection.drop_index.assert_called_once_with("id_-1")
