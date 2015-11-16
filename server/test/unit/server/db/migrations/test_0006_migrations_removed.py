from pulp.common.compat import unittest

from pulp.server.db.migrate.models import _import_all_the_way, MigrationRemovedError

migration = _import_all_the_way('pulp.server.db.migrations.0006_migrations_removed')


class TestMigrate(unittest.TestCase):
    def test_raises_exception(self):
        with self.assertRaises(MigrationRemovedError) as assertion:
            migration.migrate()
        self.assertEqual(assertion.exception.migration_version, '0006')
        self.assertEqual(assertion.exception.component_version, '2.8.0')
        self.assertEqual(assertion.exception.min_component_version, '2.4.0')
        self.assertEqual(assertion.exception.component, 'pulp')
