from copy import deepcopy
from unittest import TestCase

from mock import Mock, patch

from pulp.server.db.migrate.models import MigrationModule

LAST_SYNC = 'last_sync'
LAST_UPDATED = 'last_updated'
LAST_OVERRIDE_CONFIG = 'last_override_config'
MIGRATION = 'pulp.server.db.migrations.0025_importer_schema_change'


class TestMigration(TestCase):
    """
    Test the migration.
    """

    @patch('.'.join((MIGRATION, 'dateutils.now_utc_datetime_with_tzinfo')))
    @patch('.'.join((MIGRATION, 'get_collection')))
    def test_migrate(self, m_get_collection, now_utc_datetime):
        """
        Test last_updated and last_override_config fields added.
        """
        collection = Mock()
        found = [
            {LAST_SYNC: '2016-05-04T18:19:01Z', LAST_UPDATED: '2016-05-03T18:19:01Z'},
            {LAST_SYNC: '2016-05-04T18:20:01Z'},
            {},
        ]
        collection.find.return_value = deepcopy(found)
        m_get_collection.return_value = collection

        # test
        module = MigrationModule(MIGRATION)._module
        module.migrate()

        # validation
        m_get_collection.assert_called_once_with('repo_importers')
        collection.find.assert_called_once_with()
        now_utc_datetime.assert_called_once_with()
        self.assertTrue(LAST_UPDATED in dist for dist in collection.save.call_args_list)
        self.assertTrue(LAST_OVERRIDE_CONFIG in dist for dist in collection.save.call_args_list)
        self.assertEqual(
            len(collection.save.call_args_list), 2)
