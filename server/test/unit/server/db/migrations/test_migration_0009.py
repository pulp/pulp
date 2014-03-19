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
from ConfigParser import ConfigParser
from StringIO import StringIO

from mock import patch, Mock

from pulp.server.agent.direct.services import Services
from pulp.server.db.migrate.models import MigrationModule


MIGRATION = 'pulp.server.db.migrations.0009_qpid_queues'

TEST_CONF = """
[messaging]
transport: qpid
url: tcp://myhost:1234
clientcert: TEST-CERTIFICATE
"""

PULP_CONF = ConfigParser()
PULP_CONF.readfp(StringIO(TEST_CONF))


class TestMigration(TestCase):

    @patch(MIGRATION + '.BrokerAgent')
    @patch(MIGRATION + '.Connection')
    @patch(MIGRATION + '._migrate_reply_queue')
    @patch(MIGRATION + '._migrate_agent_queues')
    @patch(MIGRATION + '.pulp_conf', PULP_CONF)
    def test_migrate(self,
                     fake_migrate_agent_queues,
                     fake_migrate_reply_queue,
                     fake_connection,
                     fake_broker):

        # test
        migration = MigrationModule(MIGRATION)._module
        migration.migrate()

        # validation
        fake_connection.assert_called_with(
            host='myhost',
            port=1234,
            transport='tcp',
            reconnect=False,
            ssl_certfile='TEST-CERTIFICATE',
            ssl_skip_hostname_check=True)

        fake_connection().attach.assert_called_with()
        fake_broker.assert_called_with(fake_connection())
        fake_migrate_reply_queue.assert_called_with(fake_broker())
        fake_migrate_agent_queues.assert_called_with(fake_broker())
        fake_connection().detach.assert_called_with()

    @patch(MIGRATION + '.BrokerAgent')
    @patch(MIGRATION + '.Connection')
    @patch(MIGRATION + '._migrate_reply_queue')
    @patch(MIGRATION + '._migrate_agent_queues')
    @patch(MIGRATION + '.pulp_conf')
    def test_migrate_not_qpid(self,
                     fake_conf,
                     fake_migrate_agent_queues,
                     fake_migrate_reply_queue,
                     fake_connection,
                     fake_broker):

        fake_conf.get.return_value = 'not-qpid'

        # test
        migration = MigrationModule(MIGRATION)._module
        migration.migrate()

        # validation
        self.assertFalse(fake_connection.called)
        self.assertFalse(fake_broker.called)
        self.assertFalse(fake_migrate_reply_queue.called)
        self.assertFalse(fake_migrate_agent_queues.called)

    def test_migrate_reply_queue(self):
        fake_queue = Mock()
        fake_queue.values = {
            'exclusive': True,
            'arguments': {}
        }
        fake_broker = Mock()
        fake_broker.getQueue.return_value = fake_queue

        # test
        migration = MigrationModule(MIGRATION)._module
        migration._migrate_reply_queue(fake_broker)

        # validation
        fake_broker.getQueue.assert_called_with(Services.REPLY_QUEUE)
        fake_broker.delQueue.assert_called_with(Services.REPLY_QUEUE)
        fake_broker.addQueue.assert_called_with(Services.REPLY_QUEUE, durable=True)

    def test_migrate_reply_queue_excl_argument(self):
        fake_queue = Mock()
        fake_queue.values = {
            'exclusive': False,
            'arguments': {'exclusive': True}
        }
        fake_broker = Mock()
        fake_broker.getQueue.return_value = fake_queue

        # test
        migration = MigrationModule(MIGRATION)._module
        migration._migrate_reply_queue(fake_broker)

        # validation
        fake_broker.getQueue.assert_called_with(Services.REPLY_QUEUE)
        fake_broker.delQueue.assert_called_with(Services.REPLY_QUEUE)
        fake_broker.addQueue.assert_called_with(Services.REPLY_QUEUE, durable=True)

    def test_migrate_reply_queue_not_exclusive(self):
        fake_queue = Mock()
        fake_queue.values = {
            'exclusive': False,
            'arguments': {}
        }
        fake_broker = Mock()
        fake_broker.getQueue.return_value = fake_queue

        # test
        migration = MigrationModule(MIGRATION)._module
        migration._migrate_reply_queue(fake_broker)

        # validation
        fake_broker.getQueue.assert_called_with(Services.REPLY_QUEUE)
        self.assertFalse(fake_broker.called)
        self.assertFalse(fake_broker.called)

    def test_migrate_reply_queue_not_found(self):
        fake_queue = Mock()
        fake_broker = Mock()
        fake_broker.getQueue.return_value = None

        # test
        migration = MigrationModule(MIGRATION)._module
        migration._migrate_reply_queue(fake_broker)

        # validation
        fake_broker.getQueue.assert_called_with(Services.REPLY_QUEUE)
        self.assertFalse(fake_broker.called)
        self.assertFalse(fake_broker.called)

    @patch(MIGRATION + '._del_agent_queues')
    @patch(MIGRATION + '._add_agent_queues')
    def test_migrate_agent_queues(self, fake_add_agent_queues, fake_del_agent_queues):
        fake_broker = Mock()

        # test
        migration = MigrationModule(MIGRATION)._module
        migration._migrate_agent_queues(fake_broker)

        # validation
        fake_add_agent_queues.assert_called_with(fake_broker)
        fake_del_agent_queues.assert_called_with(fake_broker)


    @patch('pulp.server.db.model.consumer.Consumer.get_collection')
    def test_add_agent_queues(self, fake_get):
        fake_collection = Mock()
        fake_collection.find = Mock(return_value=[{'id': 'dog'}, {'id': 'cat'}])
        fake_get.return_value = fake_collection
        fake_broker = Mock()
        fake_broker.getQueue.side_effect = [None, None]

        # test
        migration = MigrationModule(MIGRATION)._module
        migration._add_agent_queues(fake_broker)

        fake_broker.getQueue.assert_any('pulp.agent.dog')
        fake_broker.getQueue.assert_any('pulp.agent.cat')
        fake_broker.addQueue.assert_any('pulp.agent.dog')
        fake_broker.addQueue.assert_any('pulp.agent.cat')

    @patch('pulp.server.db.model.consumer.Consumer.get_collection')
    def test_add_agent_queues_cat_only(self, fake_get):
        fake_collection = Mock()
        fake_collection.find = Mock(return_value=[{'id': 'dog'}, {'id': 'cat'}])
        fake_get.return_value = fake_collection
        fake_broker = Mock()
        fake_broker.getQueue.side_effect = [None, Mock()]

        # test
        migration = MigrationModule(MIGRATION)._module
        migration._add_agent_queues(fake_broker)

        fake_broker.getQueue.assert_any('pulp.agent.dog')
        fake_broker.getQueue.assert_any('pulp.agent.cat')
        fake_broker.addQueue.assert_calle_with('pulp.agent.cat')

    @patch('pulp.server.db.model.consumer.Consumer.get_collection')
    def test_del_agent_queues(self, fake_get):
        fake_collection = Mock()
        fake_collection.find = Mock(return_value=[{'id': 'dog'}, {'id': 'cat'}])
        fake_get.return_value = fake_collection
        fake_broker = Mock()
        fake_broker.getQueue.side_effect = [None, None]

        # test
        migration = MigrationModule(MIGRATION)._module
        migration._del_agent_queues(fake_broker)

        fake_broker.getQueue.assert_any('pulp.agent.dog')
        fake_broker.getQueue.assert_any('pulp.agent.cat')
        fake_broker.delQueue.assert_any('pulp.agent.dog')
        fake_broker.delQueue.assert_any('pulp.agent.cat')

    @patch('pulp.server.db.model.consumer.Consumer.get_collection')
    def test_del_agent_queues_cat_only(self, fake_get):
        fake_collection = Mock()
        fake_collection.find = Mock(return_value=[{'id': 'dog'}, {'id': 'cat'}])
        fake_get.return_value = fake_collection
        fake_broker = Mock()
        fake_broker.getQueue.side_effect = [None, Mock()]

        # test
        migration = MigrationModule(MIGRATION)._module
        migration._del_agent_queues(fake_broker)

        fake_broker.getQueue.assert_any('dog')
        fake_broker.getQueue.assert_any('cat')
        fake_broker.delQueue.assert_calle_with('cat')