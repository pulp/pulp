import unittest

import mock

from pulp.server.event import http
from pulp.server.event.data import Event

MODULE_PATH = 'pulp.server.event.http.'


class TestHTTPNotifierTests(unittest.TestCase):

    @mock.patch(MODULE_PATH + 'json')
    @mock.patch(MODULE_PATH + 'json_util')
    @mock.patch(MODULE_PATH + 'threading.Thread')
    def test_handle_event(self, mock_thread, mock_jutil, mock_json):
        # Setup
        notifier_config = {'key': 'value'}
        mock_event = mock.Mock(spec=Event)
        event_data = mock_event.data.return_value

        # Test
        http.handle_event(notifier_config, mock_event)
        mock_json.dumps.assert_called_once_with(event_data, default=mock_jutil.default)
        mock_thread.assert_called_once_with(
            target=http._send_post,
            args=[notifier_config, mock_json.dumps.return_value]
        )

    @mock.patch(MODULE_PATH + 'post')
    def test_send_post_no_auth(self, mock_post):
        notifier_config = {'url': 'https://localhost/api/'}
        data = {'head': 'feet'}

        http._send_post(notifier_config, data)
        mock_post.assert_called_once_with(
            'https://localhost/api/',
            data=data,
            headers={'Content-Type': 'application/json'},
            auth=None,
        )

    @mock.patch(MODULE_PATH + 'HTTPBasicAuth')
    @mock.patch(MODULE_PATH + 'post')
    def test_send_post_auth(self, mock_post, mock_basic_auth):
        notifier_config = {
            'url': 'https://localhost/api/',
            'username': 'jcline',
            'password': 'hunter2'
        }
        data = {'head': 'feet'}

        http._send_post(notifier_config, data)
        mock_post.assert_called_once_with(
            'https://localhost/api/',
            data=data,
            headers={'Content-Type': 'application/json'},
            auth=mock_basic_auth.return_value,
        )
        mock_basic_auth.assert_called_once_with('jcline', 'hunter2')

    @mock.patch(MODULE_PATH + '_logger')
    @mock.patch(MODULE_PATH + 'HTTPBasicAuth')
    @mock.patch(MODULE_PATH + 'post')
    def test_send_post_no_url(self, mock_post, mock_basic_auth, mock_log):
        """Assert attempting to post to no url fails."""
        expected_log = 'HTTP notifier configured without a URL; cannot fire event'
        http._send_post({}, {})
        mock_log.error.assert_called_once_with(expected_log)
        self.assertEqual(0, mock_post.call_count)

    @mock.patch(MODULE_PATH + '_logger')
    @mock.patch(MODULE_PATH + 'HTTPBasicAuth')
    @mock.patch(MODULE_PATH + 'post')
    def test_send_post_bad_response(self, mock_post, mock_basic_auth, mock_log):
        """Assert non-200 posts get logged."""
        expected_log = 'Received HTTP 404 from HTTP notifier to https://localhost/api/.'
        notifier_config = {
            'url': 'https://localhost/api/',
            'username': 'jcline',
            'password': 'hunter2'
        }
        data = {'head': 'feet'}
        mock_post.return_value.status_code = 404

        http._send_post(notifier_config, data)
        mock_post.assert_called_once_with(
            'https://localhost/api/',
            data=data,
            headers={'Content-Type': 'application/json'},
            auth=mock_basic_auth.return_value,
        )
        mock_log.error.assert_called_once_with(expected_log)
