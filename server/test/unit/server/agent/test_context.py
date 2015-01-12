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
from pulp.server.agent.direct.services import Services, ReplyHandler


class TestContext(TestCase):

    @patch('pulp.server.agent.context.Queue')
    @patch('pulp.server.agent.direct.services.Services.get_url')
    @patch('pulp.server.agent.context.Authenticator.load')
    def test_context(self, mock_load, get_url, queue):
        _id = 'test-db_id'
        consumer = {'_id': _id, 'id': 'test-consumer', 'certificate': 'XXX'}
        details = {'task_id': '3456'}

        # test context

        context = Context(consumer, **details)

        # validation

        route = 'pulp.agent.%s' % consumer['id']

        queue.assert_called_once_with(route)
        queue.return_value.declare.assert_called_once_with(context.url)

        self.assertEqual(context.route, route)
        self.assertEqual(context.url, get_url.return_value)
        self.assertEqual(context.secret, _id)
        self.assertEqual(context.details, details)
        self.assertEqual(context.reply_queue, ReplyHandler.REPLY_QUEUE)
        self.assertTrue(isinstance(context.authenticator, Authenticator))
        self.assertTrue(mock_load.called)