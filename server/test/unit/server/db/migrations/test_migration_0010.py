import unittest

import mock

from pulp.server.db.migrate.models import MigrationModule

MIGRATION = 'pulp.server.db.migrations.0010_utc_timestamps'


class TestMigration(unittest.TestCase):

    @mock.patch('pulp.server.db.migrations.0010_utc_timestamps.connection')
    def test_time_to_utc_on_collection(self, mock_connection):
        migration = MigrationModule(MIGRATION)._module
        collection = mock_connection.get_collection.return_value
        unit = {'bar': '2014-07-09T11:09:07-04:00'}
        utc_value = '2014-07-09T15:09:07Z'
        collection.find.return_value = [unit]

        migration.update_time_to_utc_on_collection('foo', 'bar')

        mock_connection.get_collection.assert_called_once_with('foo')
        self.assertEquals(unit['bar'], utc_value)
        collection.save.assert_called_once_with(unit, safe=True)

    @mock.patch('pulp.server.db.migrations.0010_utc_timestamps.connection')
    def test_time_to_utc_on_collection_skips_utc(self, mock_connection):
        migration = MigrationModule(MIGRATION)._module
        collection = mock_connection.get_collection.return_value
        unit = {'bar': '2014-07-09T11:09:07Z'}
        collection.find.return_value = [unit]

        migration.update_time_to_utc_on_collection('foo', 'bar')
        mock_connection.get_collection.assert_called_once_with('foo')
        self.assertFalse(collection.save.called)

    @mock.patch('pulp.server.db.migrations.0010_utc_timestamps.update_time_to_utc_on_collection')
    @mock.patch('pulp.server.db.migrations.0010_utc_timestamps.connection')
    def test_migrate(self, mock_connection, mock_update):
        """
        Verify that only known & valid collections are updated
        """
        migration = MigrationModule(MIGRATION)._module
        collection_list = ['repo_distributors']

        mock_connection.get_database.return_value.collection_names.return_value = collection_list

        migration.migrate()

        mock_update.assert_called_once_with('repo_distributors', 'last_publish')

