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

import smtplib
import unittest
import dummy_threading
try:
    from email.parser import Parser
except ImportError:
    # for python 2.4
    from email.Parser import Parser

import mock

# needed to create unserializable ID
from bson.objectid import ObjectId as _test_objid

from pulp.server.compat import json
from pulp.server.config import config
from pulp.server.event.data import Event
from pulp.server.event import data, mail
from pulp.server.managers import factory


class TestSendEmail(unittest.TestCase):
    @mock.patch('smtplib.SMTP')
    def test_basic(self, mock_smtp):
        # send a message
        mail._send_email('hello', 'stuff', 'someone@some.domain')
        mock_smtp.assert_called_once_with(host=config.get('email', 'host'),
            port=config.getint('email', 'port'))

        # verify
        mock_sendmail = mock_smtp.return_value.sendmail
        self.assertEqual(mock_sendmail.call_count, 1)
        self.assertEqual(mock_sendmail.call_args[0][0],
            config.get('email', 'from'))
        self.assertEqual(mock_sendmail.call_args[0][1], 'someone@some.domain')

        # verify message attributes
        message = Parser().parsestr(mock_sendmail.call_args[0][2])
        self.assertEqual(message.get_payload(), 'stuff')
        self.assertEqual(message.get('Subject', None), 'hello')
        self.assertEqual(message.get('From', None), config.get('email', 'from'))
        self.assertEqual(message.get('To', None), 'someone@some.domain')

    @mock.patch('smtplib.SMTP')
    @mock.patch('logging.Logger.error')
    def test_connect_failure(self, mock_error, mock_smtp):
        mock_smtp.side_effect = smtplib.SMTPConnectError(123, 'aww crap')
        mail._send_email('hello', 'stuff', 'someone@some.domain')
        self.assertTrue(mock_error.called)

    @mock.patch('smtplib.SMTP')
    @mock.patch('logging.Logger.error')
    def test_send_failure(self, mock_error, mock_smtp):
        mock_smtp.return_value.sendmail.side_effect = smtplib.SMTPRecipientsRefused(['someone@some.domain'])
        mail._send_email('hello', 'stuff', 'someone@some.domain')
        self.assertTrue(mock_error.called)


class TestHandleEvent(unittest.TestCase):
    def setUp(self):
        self.notifier_config = {
            'subject': 'hello',
            'addresses': ['user1@some.domain', 'user2@some.domain']
        }
        self.event = mock.MagicMock()
        self.event.payload = 'stuff'
        self.event.data.return_value = self.event.payload

    # don't actually spawn a thread
    @mock.patch('threading.Thread', new=dummy_threading.Thread)
    @mock.patch('ConfigParser.SafeConfigParser.getboolean', return_value=False)
    @mock.patch('smtplib.SMTP')
    def test_email_disabled(self, mock_smtp, mock_getbool):
        mail.handle_event(self.notifier_config, self.event)
        self.assertFalse(mock_smtp.called)

    # don't actually spawn a thread
    @mock.patch('threading.Thread', new=dummy_threading.Thread)
    @mock.patch('ConfigParser.SafeConfigParser.getboolean', return_value=True)
    @mock.patch('smtplib.SMTP')
    def test_email_enabled(self, mock_smtp, mock_getbool):
        mail.handle_event(self.notifier_config, self.event)

        #verify
        self.assertEqual(mock_smtp.call_count, 2)
        mock_sendmail = mock_smtp.return_value.sendmail
        self.assertEqual(mock_sendmail.call_args[0][0],
            config.get('email', 'from'))
        self.assertTrue(mock_sendmail.call_args[0][1] in self.notifier_config['addresses'])

        # verify message attributes
        message = Parser().parsestr(mock_sendmail.call_args[0][2])
        self.assertEqual(json.loads(message.get_payload()), self.event.payload)
        self.assertEqual(message.get('Subject', None), self.notifier_config['subject'])
        self.assertEqual(message.get('From', None), config.get('email', 'from'))
        self.assertTrue(message.get('To', None) in self.notifier_config['addresses'])

    # tests bz 1099945
    @mock.patch('threading.Thread', new=dummy_threading.Thread)
    @mock.patch('ConfigParser.SafeConfigParser.getboolean', return_value=True)
    @mock.patch('smtplib.SMTP')
    def test_email_serialize_objid(self, mock_smtp, mock_getbool):
        event_with_id = Event('test-1', {'foo': _test_objid()})
        # no TypeError = success
        mail.handle_event(self.notifier_config, event_with_id)


class TestSystem(unittest.TestCase):
    # test integration with the event system

    def setUp(self):
        self.notifier_config = {
            'subject': 'hello',
            'addresses': ['user1@some.domain', 'user2@some.domain']
        }
        self.event_doc = {
            'notifier_type_id' : mail.TYPE_ID,
            'event_types' : data.TYPE_REPO_SYNC_FINISHED,
            'notifier_config' : self.notifier_config,
        }

    # don't actually spawn a thread
    @mock.patch('threading.Thread', new=dummy_threading.Thread)
    # mock qpid, because it freaks out over dummy_threading
    @mock.patch('pulp.server.managers.event.remote.TopicPublishManager')
    # don't actually send any email
    @mock.patch('smtplib.SMTP')
    # act as if the config has email enabled
    @mock.patch('ConfigParser.SafeConfigParser.getboolean', return_value=True)
    # inject fake results from the database query
    @mock.patch('pulp.server.db.model.event.EventListener.get_collection')
    def test_fire(self, mock_get_collection, mock_getbool, mock_smtp, mock_publish):
        # verify that the event system will trigger listeners of this type
        mock_get_collection.return_value.find.return_value = [self.event_doc]
        event = data.Event(data.TYPE_REPO_SYNC_FINISHED, 'stuff')
        factory.initialize()
        factory.event_fire_manager()._do_fire(event)

        # verify that the mail event handler was called and processed something
        self.assertTrue(mock_smtp.return_value.sendmail.call_count, 2)


