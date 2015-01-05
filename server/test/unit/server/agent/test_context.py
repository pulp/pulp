from unittest import TestCase

from mock import patch

from pulp.server.agent.auth import Authenticator
from pulp.server.agent.context import Context
from pulp.server.agent.direct.services import Services


pulp_conf = {
    'messaging': {
        'url': 'http://broker'
    }
}


class TestContext(TestCase):

    @patch('pulp.server.agent.context.pulp_conf', pulp_conf)
    @patch('pulp.server.agent.context.Authenticator.load')
    def test_context(self, mock_load):
        _id = 'test-db_id'
        consumer = {'_id': _id, 'id': 'test-consumer', 'certificate': 'XXX'}
        details = {'task_id': '3456'}

        # test context

        context = Context(consumer, **details)

        # validation

        agent_id = 'pulp.agent.%s' % consumer['id']

        self.assertEqual(context.agent_id, agent_id)
        self.assertEqual(context.url, pulp_conf.get('messaging', 'url'))
        self.assertEqual(context.secret, _id)
        self.assertEqual(context.details, details)
        self.assertEqual(context.reply_queue, Services.REPLY_QUEUE)
        self.assertTrue(isinstance(context.authenticator, Authenticator))
        self.assertTrue(mock_load.called)
