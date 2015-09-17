from copy import deepcopy
from datetime import datetime
from unittest import TestCase

from mock import patch, Mock, call

from pulp.server.db.migrate.models import MigrationModule

LAST_PUBLISH = 'last_publish'
MIGRATION = 'pulp.server.db.migrations.0017_distributor_last_published'


class TestMigration(TestCase):
    """
    Test the migration.
    """

    @patch('.'.join((MIGRATION, 'parse_iso8601_datetime')))
    @patch('.'.join((MIGRATION, 'RepoDistributor')))
    def test_migrate(self, distributor, parse_iso8601_datetime):
        collection = Mock()
        found = [
            {LAST_PUBLISH: '2015-04-28T18:19:01Z'},
            {LAST_PUBLISH: datetime.now()},
            {LAST_PUBLISH: '2015-04-28T18:20:01Z'},
            {LAST_PUBLISH: datetime.now()},
        ]
        parsed = [1, 2]
        collection.find.return_value = deepcopy(found)
        distributor.get_collection.return_value = collection
        parse_iso8601_datetime.side_effect = parsed

        # test
        module = MigrationModule(MIGRATION)._module
        module.migrate()

        # validation
        distributor.get_collection.assert_called_once_with()
        collection.find.assert_called_once_with()
        self.assertEqual(
            parse_iso8601_datetime.call_args_list,
            [
                call(found[0][LAST_PUBLISH]),
                call(found[2][LAST_PUBLISH]),
            ])
        self.assertEqual(
            collection.save.call_args_list,
            [
                call({LAST_PUBLISH: parsed[0]}),
                call({LAST_PUBLISH: parsed[1]})
            ])
