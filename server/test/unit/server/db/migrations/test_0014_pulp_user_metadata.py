"""
This module contains tests for pulp.server.db.migrations.0014_pulp_user_metadata.
"""
import unittest

import mock

from pulp.server import constants
from pulp.server.db.migrate.models import _import_all_the_way


migration = _import_all_the_way('pulp.server.db.migrations.0014_pulp_user_metadata')


class TestMigrate(unittest.TestCase):
    """
    Test the migrate() function.
    """
    @mock.patch('pulp.server.db.migrations.0014_pulp_user_metadata.database.type_units_collection')
    @mock.patch('pulp.server.db.migrations.0014_pulp_user_metadata.factory.plugin_manager')
    def test_migrate(self, plugin_manager, type_units_collection):
        """
        Ensure that migrate() runs the correct queries on the correct collections.
        """
        types = [{'id': 'type_a'}, {'id': 'type_2'}]

        class MockPluginManager(object):
            def types(self):
                return types

        plugin_manager.return_value = MockPluginManager()

        type_collections = {'type_a': mock.MagicMock(), 'type_2': mock.MagicMock()}

        def mock_type_units_collection(type_id):
            return type_collections[type_id]

        type_units_collection.side_effect = mock_type_units_collection

        # Now we are ready to run the migration!
        migration.migrate()

        # We should have seen one call to update on each of our mocked type collections. This query
        # will set pulp_user_metadata on any objects that don't already have it to {}.
        type_collections['type_a'].update.assert_called_once_with(
            {constants.PULP_USER_METADATA_FIELDNAME: {'$exists': False}},
            {'$set': {constants.PULP_USER_METADATA_FIELDNAME: {}}}, multi=True)
        type_collections['type_2'].update.assert_called_once_with(
            {constants.PULP_USER_METADATA_FIELDNAME: {'$exists': False}},
            {'$set': {constants.PULP_USER_METADATA_FIELDNAME: {}}}, multi=True)
