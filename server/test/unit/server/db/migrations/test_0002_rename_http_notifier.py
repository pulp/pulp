import mock

from .... import base
from pulp.server.db.migrate.models import MigrationModule
from pulp.server import managers
from pulp.server.db.model.event import EventListener


class TestMigration0002(base.PulpServerTests):
    @mock.patch('pulp.server.db.model.event.EventListener.get_collection')
    def test_update_called(self, mock_get_collection):
        module = MigrationModule('pulp.server.db.migrations.0002_rename_http_notifier')._module
        module.migrate()

        # make sure the correct mongo query is being passed down
        mock_get_collection.return_value.update.assert_called_once_with(
            {'notifier_type_id': 'rest-api'}, {'$set': {'notifier_type_id': 'http'}}
        )

    def test_database_integration(self):
        # make sure the migration works on a live document in mongo
        collection = EventListener.get_collection()
        event_listener_id = str(collection.insert({
            'notifier_type_id': 'rest-api',
            'event_types': ['*'],
            'notifier_config': {},
        }))
        event_listener_factory = managers.factory.event_listener_manager()

        module = MigrationModule('pulp.server.db.migrations.0002_rename_http_notifier')._module
        module.migrate()

        event_listener = event_listener_factory.get(event_listener_id)
        self.assertEqual(event_listener['notifier_type_id'], 'http')

        # cleanup
        collection.remove()
