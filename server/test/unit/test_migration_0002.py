# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


import mock

import base
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
            'notifier_type_id' : 'rest-api',
            'event_types' : ['*'],
            'notifier_config' : {},
        }, safe=True))
        event_listener_factory = managers.factory.event_listener_manager()

        module = MigrationModule('pulp.server.db.migrations.0002_rename_http_notifier')._module
        module.migrate()

        event_listener = event_listener_factory.get(event_listener_id)
        self.assertEqual(event_listener['notifier_type_id'], 'http')

        # cleanup
        collection.remove()

