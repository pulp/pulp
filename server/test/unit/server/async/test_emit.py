"""
This module contains tests for the pulp.server.async.emit module.
"""
import unittest

import mock
from pulp.server.async.emit import send


class TestEmit(unittest.TestCase):

    @mock.patch('pulp.server.async.emit.config')
    def test_send_disabled(self, mock_config):
        """
        Ensure we bail out immediately if 'event_notifications_enabled' is False
        """
        doc = mock.Mock()
        # NB: 'event_notifications_enabled' is the only config param found via
        # getboolean() in emit.py
        mock_config.getboolean.return_value = False

        send(doc)

        assert not doc.to_json.called

    @mock.patch('pulp.server.async.emit._logger')
    @mock.patch('pulp.server.async.emit.config')
    def test_send_unserializable(self, mock_config, mock_logger):
        """
        Ensure we bail out if doc is not serializable
        """
        doc = mock.Mock()
        doc.to_json.side_effect = TypeError("boom!")
        mock_config.getboolean.return_value = True

        send(doc)

        mock_logger.warn.assert_called_once_with('unable to convert document to JSON; '
                                                 'event message not sent')

    @mock.patch('pulp.server.async.emit.config')
    @mock.patch('pulp.server.async.emit.Connection')
    @mock.patch('pulp.server.async.emit.Producer')
    def test_send_other_exception(self, mock_producer, mock_conn, mock_config):
        """
        Raise an exception if we get an Exception when sending a message
        """
        doc = mock.Mock()
        doc.to_json.return_value = '{"a": "B"}'
        mock_config.getboolean.return_value = True
        mock_config.get.return_value = "amqp://some.amqp.url/"
        mock_producer.side_effect = Exception("boom!")

        self.assertRaises(Exception, send, doc)

    @mock.patch('pulp.server.async.emit.config')
    @mock.patch('pulp.server.async.emit.Producer')
    @mock.patch('pulp.server.async.emit.Connection')
    @mock.patch('pulp.server.async.emit.Exchange')
    def test_send(self, mock_exchange, mock_conn, mock_producer, mock_config):
        """
        Test a successful send
        """
        doc = mock.Mock()
        doc.to_json.return_value = '{"a": "B"}'
        mock_config.getboolean.return_value = True
        mock_config.get.return_value = "amqp://some.amqp.url/"

        mock_exchange_instance = mock.Mock()
        mock_exchange.return_value = mock_exchange_instance

        mock_producer_instance = mock.Mock()
        mock_producer.return_value = mock_producer_instance

        send(doc)

        mock_producer_instance.maybe_declare.assert_called_once_with(mock_exchange_instance)
        mock_producer_instance.publish.assert_called_once_with('{"a": "B"}', routing_key=None,
                                                               exchange=mock_exchange_instance)
