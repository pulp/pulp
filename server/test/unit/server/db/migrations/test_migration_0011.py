import unittest
import mock
from pulp.server.db.migrate.models import MigrationModule

MIGRATION = 'pulp.server.db.migrations.0011_permissions_schema_change'


class TestMigration(unittest.TestCase):

    @mock.patch('pulp.server.db.migrations.0011_permissions_schema_change.Permission')
    def test_migrate(self, mock_connection):
        """
        Test the schema change happens like it should.
        """
        permissions_schema = [{"resource": "/", "id": "5356d55b37382030f4a80b5e",
                               "users": {"admin": [0, 1, 2, 3, 4]}}]
        new_schema = [{"resource": "/", "id": "5356d55b37382030f4a80b5e",
                      "users": [{"username": "admin", "permissions": [0, 1, 2, 3, 4]}]}]
        migration = MigrationModule(MIGRATION)._module
        collection = mock_connection.get_collection.return_value
        collection.find.return_value = permissions_schema
        migration.migrate()
        self.assertEquals(permissions_schema, new_schema)

    @mock.patch('pulp.server.db.migrations.0011_permissions_schema_change.Permission')
    def test_idempotence(self, mock_connection):
        """
        Test the idempotence of the migration
        """
        permissions_schema = [{"resource": "/", "id": "5356d55b37382030f4a80b5e",
                               "users": {"admin": [0, 1, 2, 3, 4]}}]
        new_schema = [{"resource": "/", "id": "5356d55b37382030f4a80b5e",
                      "users": [{"username": "admin", "permissions": [0, 1, 2, 3, 4]}]}]
        migration = MigrationModule(MIGRATION)._module
        collection = mock_connection.get_collection.return_value
        collection.find.return_value = permissions_schema
        migration.migrate()
        self.assertEquals(permissions_schema, new_schema)
        migration.migrate()
        self.assertEquals(permissions_schema, new_schema)
