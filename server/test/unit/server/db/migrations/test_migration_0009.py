# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from unittest import TestCase

from mock import patch, Mock

from pulp.server.db.migrate.models import MigrationModule


PATH = 'pulp.server.db.migrations.0009_qpid_queues'
migration = MigrationModule(PATH)._module


class TestMigration(TestCase):

    @patch('pulp.server.db.model.consumer.Consumer.get_collection')
    def test_migration(self, fake_get):
        fake_collection = Mock()
        fake_collection.find = Mock(return_value=[{'id': 'jeff'}])
        fake_get.return_value = fake_collection

        # test
        migration.migrate()