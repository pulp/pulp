import unittest
import mock
import copy
from pulp.server.db.migrate.models import MigrationModule

MIGRATION = 'pulp.server.db.migrations.0013_role_schema_change'
CURRENT = [{"_id": "547e3f9ee138237a3451e419", "display_name": "test",
            "_ns": "roles", "id": "test",
            "permissions": {"/v2/random": [4, 2, 1, 3]}}]
TARGET = [{"_id": "547e3f9ee138237a3451e419", "display_name": "test",
           "_ns": "roles", "id": "test",
           "permissions": [{"resource": "/v2/random", "permission": [4, 2, 1, 3]}]}]


class TestMigration(unittest.TestCase):

    @mock.patch('pulp.server.db.migrations.0013_role_schema_change.Role')
    def test_migrate(self, mock_connection):
        """
        Test the schema change happens like it should.
        """
        role_schema = copy.deepcopy(CURRENT)
        migration = MigrationModule(MIGRATION)._module
        collection = mock_connection.get_collection.return_value
        collection.find.return_value = role_schema
        migration.migrate()
        self.assertEquals(role_schema, TARGET)

    @mock.patch('pulp.server.db.migrations.0013_role_schema_change.Role')
    def test_idempotence(self, mock_connection):
        """
        Test the idempotence of the migration
        """
        role_schema = copy.deepcopy(TARGET)
        migration = MigrationModule(MIGRATION)._module
        collection = mock_connection.get_collection.return_value
        collection.find.return_value = role_schema
        migration.migrate()
        self.assertFalse(collection.save.called)
        self.assertEquals(role_schema, TARGET)
