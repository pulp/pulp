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

import unittest

import mock
from qpid.messaging import Connection
from qpid.messaging.exceptions import ConnectionError, MessagingError

from pulp.common.json_compat import json
from pulp.server.config import config
from pulp.server.event import data
from pulp.server.managers.event.remote import TopicPublishManager

class TestTopicPublishManager(unittest.TestCase):
    def setUp(self):
        self.manager = TopicPublishManager()

    def tearDown(self):
        TopicPublishManager._logged_disabled = False
        if TopicPublishManager._connection:
            TopicPublishManager._connection.close()
            TopicPublishManager._connection = None

    def test_connect(self):
        connection = self.manager.connection()
        self.assertTrue(isinstance(connection, Connection))
        self.assertTrue(connection.opened)

    def test_connection_multiple_calls(self):
        # multiple requests should return the same connection object, even
        # across instances
        connection1 = self.manager.connection()
        connection2 = TopicPublishManager().connection()

        self.assertEqual(connection1, connection2)

    @mock.patch.object(Connection, 'open', side_effect=ConnectionError)
    @mock.patch.object(TopicPublishManager.logger, 'exception')
    def test_connect_fails(self, mock_error, mock_open):
        connection = self.manager.connection()
        self.assertTrue(connection is None)
        self.assertEqual(mock_error.call_count, 1)

    @mock.patch.object(TopicPublishManager.logger, 'debug')
    @mock.patch('pulp.server.config.config.get', return_value='')
    def test_no_address_configured(self, mock_config_get, mock_debug):
        connection = self.manager.connection()
        self.assertTrue(connection is None)
        self.assertEqual(mock_config_get.call_count, 1)
        self.assertEqual(mock_debug.call_count, 1)

    @mock.patch.object(TopicPublishManager.logger, 'debug')
    @mock.patch('pulp.server.config.config.get', return_value='')
    def test_no_address_configured_single_log(self, mock_config_get, mock_debug):
        # make sure the error is only logged once
        self.manager.connection()
        self.manager.connection()
        self.assertEqual(mock_debug.call_count, 1)

    @mock.patch.object(TopicPublishManager, 'connection', return_value=None)
    def test_publish_no_connection(self, mock_connection):
        # make sure this just fails silently.
        self.manager.publish(mock.MagicMock())

    @mock.patch.object(TopicPublishManager, 'connection')
    def test_publish(self, mock_connection):
        mock_event = mock.MagicMock()
        mock_event.data.return_value = {}
        mock_event.event_type = data.TYPE_REPO_PUBLISH_FINISHED
        self.manager.publish(mock_event)

        expected_topic = 'pulp.server.' + data.TYPE_REPO_PUBLISH_FINISHED
        expected_destination = '%s/%s' % (
            config.get('messaging', 'topic_exchange'), expected_topic)

        sender = mock_connection.return_value.session.return_value.sender
        self.assertEqual(sender.call_count, 1)
        self.assertTrue(sender.call_args[0][0].startswith(expected_destination))
        sender.return_value.send.assert_called_once_with(
            json.dumps(mock_event.data.return_value))

    @mock.patch('qpid.messaging.Connection.session', side_effect=MessagingError)
    @mock.patch.object(TopicPublishManager.logger, 'exception')
    def test_publish_failed(self, mock_error, mock_session):
        # make sure this just logs the error
        mock_event = mock.MagicMock()
        mock_event.data.return_value = {}
        mock_event.event_type = data.TYPE_REPO_PUBLISH_FINISHED
        self.manager.publish(mock_event)

        self.assertEqual(mock_error.call_count, 1)

    @mock.patch.object(TopicPublishManager, 'connection')
    def test_publish_specify_exchange(self, mock_connection):
        mock_event = mock.MagicMock()
        mock_event.data.return_value = {}
        mock_event.event_type = data.TYPE_REPO_PUBLISH_FINISHED
        self.manager.publish(mock_event, 'pulp')

        expected_topic = 'pulp.server.' + data.TYPE_REPO_PUBLISH_FINISHED
        expected_destination = '%s/%s' % ('pulp', expected_topic)
        sender = mock_connection.return_value.session.return_value.sender
        self.assertEqual(sender.call_count, 1)
        self.assertTrue(sender.call_args[0][0].startswith(expected_destination))

