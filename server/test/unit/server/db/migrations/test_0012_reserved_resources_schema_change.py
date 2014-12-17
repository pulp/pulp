"""
This module contains unit tests for pulp.server.db.migrations.0012_reserved_resources_schema_change.
"""
import unittest

from mock import call, patch

from pulp.server.db.migrate.models import _import_all_the_way


migration = _import_all_the_way('pulp.server.db.migrations.0012_reserved_resources_schema_change')


class TestMigrate(unittest.TestCase):
    """
    Test the migrate() function.
    """
    @patch('pulp.server.db.migrations.0012_reserved_resources_schema_change._migrate_task_status',
           side_effect=migration._migrate_task_status)
    @patch('pulp.server.db.migrations.0012_reserved_resources_schema_change.'
           '_migrate_reserved_resources', side_effect=migration._migrate_reserved_resources)
    @patch(
        'pulp.server.db.migrations.0012_reserved_resources_schema_change.connection.get_collection',
        autospec=True)
    def test_calls_correct_functions(self, get_collection, _migrate_reserved_resources,
                                     _migrate_task_status):
        """
        Assert that migrate() calls the correct other functions that do the real work.
        """
        migration.migrate()

        _migrate_task_status.assert_called_once_with()
        _migrate_reserved_resources.assert_called_once_with()
        get_collection.assert_any_call('task_status')
        get_collection.assert_any_call('reserved_resources')

    @patch('pulp.server.db.migrations.0012_reserved_resources_schema_change._migrate_task_status',
           side_effect=migration._migrate_task_status)
    @patch('pulp.server.db.migrations.0012_reserved_resources_schema_change.'
           '_migrate_reserved_resources', side_effect=migration._migrate_reserved_resources)
    @patch(
        'pulp.server.db.migrations.0012_reserved_resources_schema_change.connection.get_collection',
        autospec=True)
    def test_migrate_task_status(self, get_collection, _migrate_reserved_resources,
                                 _migrate_task_status):
        """
        Assert that the correct query is run for migrating task_status collection.
        """
        migration._migrate_task_status()
        get_collection.assert_has_calls(call().update({'state': {'$in': ('waiting', 'accepted',
                                                                         'running', 'suspended')}},
                                                      {'$set': {'state': 'canceled'}}, multi=True))

    @patch('pulp.server.db.migrations.0012_reserved_resources_schema_change._migrate_task_status',
           side_effect=migration._migrate_task_status)
    @patch('pulp.server.db.migrations.0012_reserved_resources_schema_change.'
           '_migrate_reserved_resources', side_effect=migration._migrate_reserved_resources)
    @patch(
        'pulp.server.db.migrations.0012_reserved_resources_schema_change.connection.get_collection',
        autospec=True)
    def test_migrate_reserved_resources(self, get_collection, _migrate_reserved_resources,
                                        _migrate_task_status):
        """
        Assert that the correct query is run for migrating reserved_resources collection.
        """
        migration._migrate_reserved_resources()
        get_collection.assert_has_calls(call().remove({}))
