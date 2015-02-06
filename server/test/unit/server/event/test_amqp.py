import mock

from ... import base
from pulp.server.event.amqp import handle_event


class TestAMQPNotifier(base.PulpServerTests):
    @mock.patch('pulp.server.managers.event.remote.TopicPublishManager.publish')
    def test_handle_event(self, mock_publish):
        event = mock.MagicMock()

        handle_event({}, event)

        mock_publish.assert_called_once_with(event, None)

    @mock.patch('pulp.server.managers.event.remote.TopicPublishManager.publish')
    def test_handle_event_with_exchange(self, mock_publish):
        event = mock.MagicMock()

        handle_event({'exchange': 'pulp'}, event)

        mock_publish.assert_called_once_with(event, 'pulp')
