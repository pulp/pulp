from unittest import TestCase

from mock import patch

from pulp.server.agent.auth import Authenticator
from pulp.server.agent.context import Context
from pulp.server.agent.direct.services import ReplyHandler


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
