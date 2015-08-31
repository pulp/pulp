"""
This module contains tests for pulp.server.db.migrations.0020_drop_celery_taskmeta.py
"""
import unittest

from mock import patch

from pulp.server.db.migrate.models import _import_all_the_way

migration = _import_all_the_way('pulp.server.db.migrations.0020_drop_celery_taskmeta')


class TestMigrate(unittest.TestCase):
    """
    Test the migrate() function.
    """

    @patch.object(migration.connection, 'get_database')
    def test_celery_taskmeta_collection_dropped(self, mock_get_database):
        mock_get_database.return_value.collection_names.return_value = []
        collection = mock_get_database.return_value['celery_taskmeta']
        migration.migrate()
        collection.drop.assert_called_once()
