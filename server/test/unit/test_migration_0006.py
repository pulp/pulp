# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from base import PulpServerTests

from pulp.server.db.migrate.models import MigrationModule
from pulp.server.db.model.consumer import Bind

ID = 'id'
CONSUMER_ID = 'consumer_id'
REPO_ID = 'repo_id'
DISTRIBUTOR_ID = 'distributor_id'
BINDING_CONFIG = 'binding_config'
NOTIFY_AGENT = 'notify_agent'
MAX_BINDINGS = 10

MIGRATION = 'pulp.server.db.migrations.0006_binding_config'


class TestMigration_0006(PulpServerTests):

    def setUp(self):
        self.clean()
        super(TestMigration_0006, self).setUp()
        collection = Bind.get_collection()
        collection.remove()

    def tearDown(self):
        super(TestMigration_0006, self).tearDown()
        collection = Bind.get_collection()
        collection.remove()

    def test_migration(self):
        # setup
        collection = Bind.get_collection()
        for n in range(0, MAX_BINDINGS):
            if n % 2 == 0:
                conf = {ID: n}
            else:
                conf = None
            binding = {
                ID: n,
                CONSUMER_ID: n,
                REPO_ID: n,
                DISTRIBUTOR_ID: n,
                BINDING_CONFIG: conf,
                NOTIFY_AGENT: True,
            }
            collection.save(binding, safe=True)
        # migrate
        module = MigrationModule(MIGRATION)._module
        module.migrate()
        # verify
        bindings = list(collection.find({}))
        self.assertEqual(len(bindings), MAX_BINDINGS)
        for binding in bindings:
            conf = binding[BINDING_CONFIG]
            bind_id = binding[ID]
            if bind_id % 2 == 0:
                # untouched
                self.assertEqual(conf, {ID: bind_id})
            else:
                # fixed
                self.assertEqual(conf, {})