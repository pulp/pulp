"""
This module contains tests for pulp.server.db.migrations.0021_remove_extra_importer_fields.py
"""
import unittest

import mock

from pulp.server.db.migrate.models import _import_all_the_way

migration = _import_all_the_way('pulp.server.db.migrations.0021_remove_extra_importer_fields')


class TestMigrate(unittest.TestCase):
    """
    Test the migrate() function.
    """
    @classmethod
    def setUpClass(cls):
        """
        Run the migration
        """
        with mock.patch.object(migration.connection, 'get_database') as mock_db:
            cls.collection = mock_db.return_value['archived_calls']
            migration.migrate()

    def test_index_removed(self):
        """
        Assert that the old index is removed.
        """
        self.collection.drop_index.assert_called_once_with("repo_id_-1_id_-1")

    def test_fields_removed(self):
        """
        Assert that the old fields are removed.
        """
        self.collection.update.assert_has_calls([
            mock.call({}, {"$unset": {"id": True}}, multi=True),
            mock.call({}, {"$unset": {"scheduled_syncs": ""}}, multi=True)
        ])
