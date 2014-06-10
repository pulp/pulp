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

from mock import patch, Mock, call

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
        fake_broker.addQueue.assert_called__once_with('pulp.agent.dog', durable=True)


class TestMigrateReplyQueue(TestCase):

    def setUp(self):
        self.patcher = patch(MIGRATION + '._del_queue_catch_queue_in_use_exception')
        self.mock_del_queue_catch_queue_in_use_exc = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_migrate_reply_queue_checks_deleted_and_recreates_reply_queue(self):
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
        fake_broker.getQueue.assert_called_once_with(Services.REPLY_QUEUE)
        expected_call = call(fake_broker, Services.REPLY_QUEUE)
        self.mock_del_queue_catch_queue_in_use_exc.assert_has_calls(expected_call)
        fake_broker.addQueue.assert_called_once_with(Services.REPLY_QUEUE, durable=True)

    def test_migrate_reply_queue_arguments_is_exclusive_deletes_and_add_reply_queue(self):
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
        expected_call = call(fake_broker, Services.REPLY_QUEUE)
        self.mock_del_queue_catch_queue_in_use_exc.assert_has_calls(expected_call)
        fake_broker.addQueue.assert_called_with(Services.REPLY_QUEUE, durable=True)

    def test_migrate_reply_queue_not_exclusive_does_not_delete_or_add_reply_queue(self):
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
        self.assertTrue(not self.mock_del_queue_catch_queue_in_use_exc.called)
        self.assertTrue(not fake_broker.addQueue.called)

    def test_migrate_reply_queue_not_found_does_not_delete_or_add_reply_queue(self):
        fake_broker = Mock()
        fake_broker.getQueue.return_value = None

        # test
        migration = MigrationModule(MIGRATION)._module
        migration._migrate_reply_queue(fake_broker)

        # validation
        fake_broker.getQueue.assert_called_with(Services.REPLY_QUEUE)
        self.assertTrue(not self.mock_del_queue_catch_queue_in_use_exc.called)
        self.assertTrue(not fake_broker.addQueue.called)


class TestDelAgentQueues(TestCase):

    def setUp(self):
        self.patch_a = patch('pulp.server.db.model.consumer.Consumer.get_collection')
        self.mock_get_collection = self.patch_a.start()

        self.patch_b = patch(MIGRATION + '._del_queue_catch_queue_in_use_exception')
        self.mock_del_queue_catch_queue_in_use_exc = self.patch_b.start()

        self.fake_collection = Mock()
        self.fake_collection.find = Mock(return_value=[{'id': 'dog'}, {'id': 'cat'}])
        self.mock_get_collection.return_value = self.fake_collection
        self.fake_broker = Mock()

    def tearDown(self):
        self.patch_a.stop()
        self.patch_b.stop()

    def test_del_agent_queues_skips_existing_queues(self):
        self.fake_broker.getQueue.side_effect = [None, None]

        # test
        migration = MigrationModule(MIGRATION)._module
        migration._del_agent_queues(self.fake_broker)

        self.fake_broker.getQueue.assert_has_calls([call('dog'), call('cat')])
        self.assertTrue(not self.mock_del_queue_catch_queue_in_use_exc.called)

    def test_del_agent_queues_deletes_all_existing_queues(self):
        self.fake_broker.getQueue.side_effect = [Mock(), Mock()]

        # test
        migration = MigrationModule(MIGRATION)._module
        migration._del_agent_queues(self.fake_broker)

        expected_calls = [call(self.fake_broker, 'dog'), call(self.fake_broker, 'cat')]
        self.mock_del_queue_catch_queue_in_use_exc.assert_has_calls(expected_calls)


class TestDelQueueCatchQueueInUseException(TestCase):

    def test__del_queue_catch_no_queue_in_use_exception_calls_add_queue(self):
        fake_broker = Mock()
        mock_name = Mock()
        migration = MigrationModule(MIGRATION)._module
        migration._del_queue_catch_queue_in_use_exception(fake_broker, mock_name)
        fake_broker.delQueue.assert_called_once_with(mock_name)

    def test__del_queue_catch_no_queue_in_use_exception_catches_cannot_delete_queue(self):
        fake_broker = Mock()
        mock_name = Mock()
        exc_to_raise = Exception("Cannot delete queue celery; queue in use")
        fake_broker.delQueue.side_effect = exc_to_raise

        migration = MigrationModule(MIGRATION)._module
        try:
            migration._del_queue_catch_queue_in_use_exception(fake_broker, mock_name)
            self.fail('An exception should have been raised, and was not.')
        except Exception as error:
            string_a = 'Consumers are still bound to the queue'
            string_b = 'All consumers must be unregistered, upgraded, or off before you can continue'
            if string_a not in error.message or string_b not in error.message:
                self.fail("Migration 0009 does not handle a 'queue in use' exception")

    def test__del_queue_catch_no_queue_in_use_exception_calls_passed_through_other_exceptions(self):
        fake_broker = Mock()
        mock_name = Mock()
        fake_broker.delQueue.side_effect = IOError()
        migration = MigrationModule(MIGRATION)._module
        self.assertRaises(IOError, migration._del_queue_catch_queue_in_use_exception, fake_broker, mock_name)
