# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.server.db.model.consumer import Bind

import base
from pulp.server.db.migrate.models import MigrationModule


class BindAdditionMigrationTests(base.PulpServerTests):

    def clean(self):
        super(BindAdditionMigrationTests, self).clean()

        Bind.get_collection().remove()

    def test_upgrade(self):
        # Setup
        coll = Bind.get_collection()

        for counter in range(0, 3):
            bind_dict = {
                'consumer_id' : 'consumer_%s' % counter,
                'repo_id' : 'repo_%s' % counter,
                'distributor_id' : 'distributor_%s' % counter,
            }

            coll.insert(bind_dict, safe=True)

        # Test
        module = MigrationModule('pulp.server.db.migrations.0003_bind_additions')._module
        module.migrate()

        # Verify
        bindings = coll.find()
        for b in bindings:
            self.assertTrue('notify_agent' in b)
            self.assertEqual(b['notify_agent'], True)
            self.assertTrue('binding_config' in b)
            self.assertEqual(b['binding_config'], None)

    def test_upgrade_idempotency(self):
        """
        Simplest way to check the migration can run twice is simply to run it twice. The
        primary goal is to make sure an exception isn't raised.
        """

        # Setup
        coll = Bind.get_collection()

        for counter in range(0, 3):
            bind_dict = {
                'consumer_id' : 'consumer_%s' % counter,
                'repo_id' : 'repo_%s' % counter,
                'distributor_id' : 'distributor_%s' % counter,
            }

            coll.insert(bind_dict, safe=True)

        # Test
        module = MigrationModule('pulp.server.db.migrations.0003_bind_additions')._module
        module.migrate()
        module.migrate()

        # Verify
        bindings = coll.find()
        for b in bindings:
            self.assertTrue('notify_agent' in b)
            self.assertEqual(b['notify_agent'], True)
            self.assertTrue('binding_config' in b)
            self.assertEqual(b['binding_config'], None)

