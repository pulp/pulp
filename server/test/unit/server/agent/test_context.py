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

from unittest import TestCase

from mock import patch

from pulp.server.agent.auth import Authenticator
from pulp.server.agent.context import Context
from pulp.server.agent.direct.services import ReplyHandler


class TestContext(TestCase):

    @patch('pulp.server.agent.context.get_url')
    @patch('pulp.server.agent.context.Authenticator.load')
    def test_context(self, load, get_url):
        _id = 'test-db_id'
        consumer = {'_id': _id, 'id': 'test-consumer'}
        details = {'task_id': '3456'}

        # test context

        context = Context(consumer, **details)

        # validation
        load.assert_called_once_with()

        self.assertEqual(context.address, 'pulp.agent.%s' % consumer['id'])
        self.assertEqual(context.url, get_url.return_value)
        self.assertEqual(context.secret, _id)
        self.assertEqual(context.details, details)
        self.assertEqual(context.reply_queue, ReplyHandler.REPLY_QUEUE)
        self.assertTrue(isinstance(context.authenticator, Authenticator))

    @patch('pulp.server.agent.context.get_url')
    @patch('pulp.server.agent.context.Authenticator.load')
    @patch('pulp.server.agent.context.add_connector')
    @patch('pulp.server.agent.context.Queue')
    def test_enter_exit(self, queue, add_connector, load, get_url):
        _id = 'test-db_id'
        consumer = {'_id': _id, 'id': 'test-consumer'}
        details = {'task_id': '3456'}

        get_url.return_value = 'amqp://host'
        load.return_value = None

        # test context
        with Context(consumer, **details) as connector:
            pass

        # validation
        add_connector.assert_called_once_with()
        queue.assert_called_once_with(connector.address, connector.url)
        queue.return_value.declare.assert_called_once_with()
