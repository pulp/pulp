from unittest import TestCase

from mock import Mock, patch

from pulp.server.db.migrate.models import MigrationModule

LAST_UPDATED = 'last_updated'
LAST_OVERRIDE_CONFIG = 'last_override_config'
MIGRATION = 'pulp.server.db.migrations.0026_revert_0025'


class TestMigration(TestCase):
    """
    Test the migration.
    """

    @patch('.'.join((MIGRATION, 'get_collection')))
    def test_migrate(self, m_get_collection):
        """
        Test last_updated and last_override_config fields added.
        """
        collection = Mock()
        m_get_collection.return_value = collection

        # test
        module = MigrationModule(MIGRATION)._module
        module.migrate()

        # validation
        m_get_collection.assert_called_once_with('repo_importers')
        # can't do much more than see that update was called
        # for each key to be removed (2 total calls)
        self.assertEqual(
            len(collection.update.call_args_list), 2)
