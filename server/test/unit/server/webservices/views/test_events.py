import json
import unittest

import mock

from base import (assert_auth_CREATE, assert_auth_DELETE, assert_auth_READ, assert_auth_UPDATE)
from pulp.server.webservices.views.events import (EventResourceView, EventView)


class TestEventView(unittest.TestCase):
    """
    Test events view.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.events.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.events.factory')
    def test_get_events(self, mock_factory, mock_resp):
        """
        Test events retrieval.
        """
        events = [{'notifier_type_id': 'http', 'id': '12345'}]
        mock_factory.event_listener_manager.return_value.list.return_value = events

        request = mock.MagicMock()
        event_listeners = EventView()
        response = event_listeners.get(request)

        expected_cont = [{'id': '12345', '_href': '/v2/events/12345/', 'notifier_type_id': 'http'}]
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.events.generate_redirect_response')
    @mock.patch('pulp.server.webservices.views.events.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.events.factory')
    def test_create_event(self, mock_factory, mock_resp, mock_redirect):
        """
        Test event creation.
        """
        resp = {'notifier_type_id': 'http', 'id': '12345', "event_types": ["foo", "bar"]}
        mock_factory.event_listener_manager.return_value.create.return_value = resp

        request = mock.MagicMock()
        request.body = json.dumps({'notifier_type_id': 'http', "event_types": ["foo", "bar"]})
        event_listeners = EventView()
        response = event_listeners.post(request)

        expected_cont = {'id': '12345', '_href': '/v2/events/12345/', 'notifier_type_id': 'http',
                         'event_types': ['foo', 'bar']}
        mock_resp.assert_called_once_with(expected_cont)
        mock_redirect.assert_called_once_with(mock_resp.return_value, expected_cont['_href'])
        self.assertTrue(response is mock_redirect.return_value)


class TestEventResourceView(unittest.TestCase):
    """
    Test event resource view.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.events.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.events.factory')
    def test_get_single_event(self, mock_factory, mock_resp):
        """
        Test single event retrieval.
        """
        event = {'notifier_type_id': 'http', 'id': '12345'}
        mock_factory.event_listener_manager.return_value.get.return_value = event

        request = mock.MagicMock()
        event_listeners = EventResourceView()
        response = event_listeners.get(request, '12345')

        expected_cont = {'id': '12345', '_href': '/v2/events/12345/', 'notifier_type_id': 'http'}
        mock_resp.assert_called_once_with(expected_cont)
        mock_factory.event_listener_manager.return_value.get.assert_called_once_with('12345')
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.events.generate_json_response')
    @mock.patch('pulp.server.webservices.views.events.factory')
    def test_delete_single_event(self, mock_factory, mock_resp):
        """
        Test event deletion.
        """
        mock_factory.event_listener_manager.return_value.delete.return_value = None

        request = mock.MagicMock()
        event_listeners = EventResourceView()
        response = event_listeners.delete(request, '12345')

        mock_factory.event_listener_manager.return_value.delete.assert_called_once_with('12345')
        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.events.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.events.factory')
    def test_update_event(self, mock_factory, mock_resp):
        """
        Test event update
        """
        resp = {'notifier_type_id': 'http', 'id': '12345', 'event_types': ['some']}
        mock_factory.event_listener_manager.return_value.update.return_value = resp

        request = mock.MagicMock()
        request.body = json.dumps({'event_types': ['some']})
        event_listeners = EventResourceView()
        response = event_listeners.put(request, '12345')

        expected_cont = {'id': '12345', '_href': '/v2/events/12345/', 'notifier_type_id': 'http',
                         'event_types': ['some']}

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)
