# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import httplib
import mock
import time
import unittest
from pulp.server.compat import json

from pulp.server.event import rest_api
from pulp.server.event.data import Event

class RestApiNotifierTests(unittest.TestCase):

    @mock.patch('pulp.server.event.rest_api._create_connection')
    def test_handle_event(self, mock_create):
        # Setup
        notifier_config = {
            'url' : 'https://localhost/api/',
            'username' : 'admin',
            'password' : 'admin',
        }

        event = Event('type-1', {'k1' : 'v1'})

        mock_connection = mock.Mock()
        mock_response = mock.Mock()

        mock_response.status = httplib.OK

        mock_connection.getresponse.return_value = mock_response
        mock_create.return_value = mock_connection

        # Test
        rest_api.handle_event(notifier_config, event)
        time.sleep(.5) # handle works in a thread so give it a bit to finish

        # Verify
        self.assertEqual(1, mock_create.call_count)
        self.assertEqual(1, mock_connection.request.call_count)

        request_args = mock_connection.request.call_args[0]
        self.assertEqual('POST', request_args[0])
        self.assertEqual('/api/', request_args[1])

        expected_body = {'event_type' : event.event_type,
                         'payload' : event.payload}

        request_kwargs = mock_connection.request.call_args[1]
        parsed_body = json.loads(request_kwargs['body'])
        self.assertEqual(parsed_body, expected_body)

        headers = request_kwargs['headers']
        self.assertTrue('Authorization' in headers)

    @mock.patch('pulp.server.event.rest_api._create_connection')
    def test_handle_event_with_error(self, mock_create):
        # Setup
        notifier_config = {'url' : 'https://localhost/api/'}

        event = Event('type-1', {'k1' : 'v1'})

        mock_connection = mock.Mock()
        mock_response = mock.Mock()

        mock_response.status = httplib.NOT_FOUND

        mock_connection.getresponse.return_value = mock_response
        mock_create.return_value = mock_connection

        # Test
        rest_api.handle_event(notifier_config, event) # should not error
        time.sleep(.5)

        # Verify
        self.assertEqual(1, mock_create.call_count)
        self.assertEqual(1, mock_connection.request.call_count)

    @mock.patch('pulp.server.event.rest_api._create_connection')
    def test_handle_event_missing_url(self, mock_create):
        # Test
        rest_api.handle_event({}, Event('type-1', {})) # should not error

        # Verify
        self.assertEqual(0, mock_create.call_count)

    @mock.patch('pulp.server.event.rest_api._create_connection')
    def test_handle_event_unparsable_url(self, mock_create):
        # Test
        rest_api.handle_event({'url' : '!@#$%'}, Event('type-1', {})) # should not error

        # Verify
        self.assertEqual(0, mock_create.call_count)

    def test_create_configuration(self):
        # Test HTTPS
        conn = rest_api._create_connection('https', 'foo')
        self.assertTrue(isinstance(conn, httplib.HTTPSConnection))

        # Test HTTP
        conn = rest_api._create_connection('http', 'foo')
        self.assertTrue(isinstance(conn, httplib.HTTPConnection))