from copy import deepcopy
from unittest import TestCase

from mock import Mock, patch

from pulp.server.db.migrate.models import MigrationModule

LAST_UPDATED = 'last_updated'
MIGRATION = 'pulp.server.db.migrations.0028_distributor_last_updated_fix'


class TestMigration(TestCase):
    """
    Test the migration.
    """

    @patch('.'.join((MIGRATION, 'dateutils.now_utc_datetime_with_tzinfo')))
    @patch('.'.join((MIGRATION, 'get_collection')))
    def test_migrate(self, m_get_collection, now_utc_datetime):
        """
        Test last_updated field is set.
        """
        collection = Mock()
        found = [
            {LAST_UPDATED: '2016-05-03T18:19:01Z'},
            {LAST_UPDATED: None},
            {},
        ]
        collection.find.return_value = deepcopy(found)
        m_get_collection.return_value = collection

        # test
        module = MigrationModule(MIGRATION)._module
        module.migrate()

        # validation
        m_get_collection.assert_called_once_with('repo_distributors')
        collection.find.assert_called_once_with()
        self.assertEqual(now_utc_datetime.call_count, 2)
        self.assertTrue(dist.get(LAST_UPDATED) for dist in collection.save.call_args_list)
        self.assertEqual(len(collection.save.call_args_list), 2)
