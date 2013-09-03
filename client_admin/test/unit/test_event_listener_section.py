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
from okaara.cli import CommandUsage

from pulp.client.admin import event
from pulp.client.extensions.extensions import PulpCliOption


class TestEventSection(unittest.TestCase):
    def test_subsection(self):
        context = mock.MagicMock()
        section = event.EventSection(context)
        subsection = section.subsections.get('listener')

        self.assertTrue(isinstance(subsection, event.ListenerSection))
        self.assertEqual(context, subsection.context)


class TestGenericSection(unittest.TestCase):
    CREATE_ARGS = {
        'config' : {'a' : 'foo'},
        'event_types' : ['repo-sync-started'],
        'notifier_type' : 'email'
    }

    def setUp(self):
        self.section = event.GenericSection(mock.MagicMock(), 'section' ,'stuff')

    def test_create(self):
        self.section._create(**self.CREATE_ARGS)
        self.section.context.server.event_listener.create.assert_called_once_with(
            'email',
            {'a': 'foo'},
            ['repo-sync-started']
        )

        self.assertEqual(self.section.context.prompt.render_success_message.call_count, 1)

    def test_create_error(self):
        self.section.context.server.event_listener.create.side_effect = TypeError

        self.assertRaises(CommandUsage, self.section._create, **self.CREATE_ARGS)

    def test_empty_update(self):
        self.section._update('listener1', {})

        self.assertEqual(self.section.context.prompt.render_failure_message.call_count, 1)
        self.assertEqual(self.section.context.server.event_listener.update.call_count, 0)

    def test_update(self):
        self.section._update('foo', {'notifier_config': {'a':'bar'}})

        self.assertEqual(self.section.context.prompt.render_success_message.call_count, 1)
        self.section.context.server.event_listener.update.assert_called_once_with(
            'foo', notifier_config={'a': 'bar'})

    def test_update_event_type(self):
        self.section._update('foo', {'event_types' : ['blah']})

        self.assertEqual(self.section.context.prompt.render_success_message.call_count, 1)
        self.section.context.server.event_listener.update.assert_called_once_with(
            'foo', event_types=['blah'])

    def test_copy_flip_required(self):
        opt = PulpCliOption('--x', 'description', required=True)
        ret = self.section._copy_flip_required(opt)

        self.assertTrue(ret.required is False)
        self.assertEqual(opt.name, ret.name)
        self.assertEqual(opt.description, ret.description)
        self.assertTrue(id(opt) != id(ret))


class TestListenerSection(unittest.TestCase):
    def setUp(self):
        self.section = event.ListenerSection(mock.MagicMock())

    def test_list(self):
        self.section.context.server.event_listener.list.return_value = [{}]
        self.section.list()

        self.section.context.prompt.render_document.assert_called_once_with({})

    def test_delete(self):
        args = {'listener-id' : 'foo'}
        self.section.delete(**args)

        self.assertEqual(self.section.context.prompt.render_success_message.call_count, 1)
        self.section.context.server.event_listener.delete.assert_called_once_with(
            'foo')


class TestAMQPSection(unittest.TestCase):
    def setUp(self):
        self.section = event.AMQPSection(mock.MagicMock())

    def test_create(self):
        kwargs = {
            'event-type' : 'repo-sync-finished',
            'exchange' : 'pulp',
        }
        self.section.create(**kwargs)

        self.section.context.server.event_listener.create.assert_called_once_with(
            'amqp',
            {
                'exchange': 'pulp',
            },
            'repo-sync-finished'
        )

    def test_update_exchange(self):
        kwargs = {
            'listener-id' : 'listener1',
            'exchange' : 'pulp',
            'event-type' : None
        }

        self.section.update(**kwargs)
        self.section.context.server.event_listener.update.assert_called_once_with(
            'listener1', notifier_config={'exchange': 'pulp'})

    def test_update_exchange_empty(self):
        kwargs = {
            'listener-id' : 'listener1',
            'exchange' : '',
            'event-type' : None
        }

        self.section.update(**kwargs)
        self.section.context.server.event_listener.update.assert_called_once_with(
            'listener1', notifier_config={'exchange': ''})


class TestEmailSection(unittest.TestCase):
    def setUp(self):
        self.section = event.EmailSection(mock.MagicMock())

    def test_create(self):
        kwargs = {
            'event-type' : 'repo-sync-finished',
            'subject' : 'hi',
            'addresses' : ['info@some.domain', 'info@other.domain']
        }
        self.section.create(**kwargs)

        self.section.context.server.event_listener.create.assert_called_once_with(
            'email',
            {
                'subject': 'hi',
                'addresses' : ['info@some.domain', 'info@other.domain']
            },
            'repo-sync-finished'
        )

    def test_update_subject(self):
        kwargs = {
            'listener-id' : 'listener1',
            'subject' : 'hi',
            'addresses' : None,
            'event-type' : None
        }

        self.section.update(**kwargs)
        self.section.context.server.event_listener.update.assert_called_once_with(
            'listener1', notifier_config={'subject': 'hi'})

    def test_update_addresses(self):
        kwargs = {
            'listener-id' : 'listener1',
            'subject' : None,
            'addresses' : ['info@some.domain'],
            'event-type' : None
        }

        self.section.update(**kwargs)
        self.section.context.server.event_listener.update.assert_called_once_with(
            'listener1', notifier_config={'addresses': ['info@some.domain']})

    def test_update_event_types(self):
        kwargs = {
            'listener-id' : 'listener1',
            'subject' : None,
            'addresses' : None,
            'event-type' : ['repo-sync-finished']
        }

        self.section.update(**kwargs)
        self.section.context.server.event_listener.update.assert_called_once_with(
            'listener1', event_types=['repo-sync-finished'])


class TestRESTAPISection(unittest.TestCase):
    def setUp(self):
        self.section = event.RestApiSection(mock.MagicMock())

    def test_create_basic(self):
        kwargs = {
            'event-type' : 'repo-sync-finished',
            'url' : 'http://redhat.com',
        }
        self.section.create(**kwargs)

        self.section.context.server.event_listener.create.assert_called_once_with(
            'http',
            {'url': 'http://redhat.com'},
            'repo-sync-finished'
        )

    def test_create_with_username_password(self):
        kwargs = {
            'event-type' : 'repo-sync-finished',
            'url' : 'http://redhat.com',
            'username' : 'me',
            'password' : 'letmein'
            }
        self.section.create(**kwargs)

        self.section.context.server.event_listener.create.assert_called_once_with(
            'http',
            {
                'url': 'http://redhat.com',
                'username' : 'me',
                'password' : 'letmein'
            },
            'repo-sync-finished'
        )

    def test_update_url(self):
        kwargs = {
            'listener-id' : 'listener1',
            'url' : 'http://redhat.com',
            'username' : None,
            'password' : None,
            'event-type' : None,
        }

        self.section.update(**kwargs)
        self.section.context.server.event_listener.update.assert_called_once_with(
            'listener1', notifier_config={'url': 'http://redhat.com'})

    def test_update_username(self):
        kwargs = {
            'listener-id' : 'listener1',
            'url' : None,
            'username' : 'me',
            'password' : None,
            'event-type' : None,
        }

        self.section.update(**kwargs)
        self.section.context.server.event_listener.update.assert_called_once_with(
            'listener1', notifier_config={'username' : 'me'})

    def test_update_password(self):
        kwargs = {
            'listener-id' : 'listener1',
            'url' : None,
            'username' : None,
            'password' : 'letmein',
            'event-type' : None,
        }

        self.section.update(**kwargs)
        self.section.context.server.event_listener.update.assert_called_once_with(
            'listener1', notifier_config={'password' : 'letmein'})

    def test_update_event_types(self):
        kwargs = {
            'listener-id' : 'listener1',
            'url' : None,
            'username' : None,
            'password' : None,
            'event-type' : ['repo-sync-finished'],
        }

        self.section.update(**kwargs)
        self.section.context.server.event_listener.update.assert_called_once_with(
            'listener1', event_types=['repo-sync-finished'])
