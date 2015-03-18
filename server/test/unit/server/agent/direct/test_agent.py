#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from unittest import TestCase

from mock import patch, Mock

from pulp.server.agent.direct.pulpagent import PulpAgent, Consumer, Content, Profile


class TestAgent(TestCase):

    def test_capabilities(self):
        agent = PulpAgent()
        self.assertEqual(agent.consumer, Consumer)
        self.assertEqual(agent.content, Content)
        self.assertEqual(agent.profile, Profile)


class NotFound(Exception):
    pass


class Context(Mock):

    def __init__(self):
        super(Context, self).__init__()
        self.address = '123'
        self.secret = 'test-secret'
        self.url = 'http://broker.com'
        self.authenticator = Mock()
        self.details = {'task_id': '4567'}
        self.reply_queue = 'pulp.task'
        self.__enter__ = Mock()
        self.__exit__ = Mock()


class TestConsumerCapability(TestCase):

    @patch('pulp.server.agent.direct.pulpagent.add_connector')
    @patch('pulp.server.agent.direct.pulpagent.Queue')
    def test_delete_queue(self, queue, add_connector):
        url = 'test-url'
        name = 'test-queue'

        # test
        agent = PulpAgent()
        agent.delete_queue(url, name)

        # validation
        add_connector.assert_called_once_with()
        queue.assert_called_once_with(name, url)
        queue.return_value.purge.assert_called_once_with()
        queue.return_value.delete.assert_called_once_with()

    @patch('pulp.server.agent.direct.pulpagent.add_connector')
    @patch('pulp.server.agent.direct.pulpagent.Queue')
    @patch('pulp.server.agent.direct.pulpagent.NotFound', NotFound)
    def test_delete_queue_not_found(self, queue, add_connector):
        url = 'test-url'
        name = 'test-queue'
        queue.return_value.purge.side_effect = NotFound

        # test
        agent = PulpAgent()
        agent.delete_queue(url, name)

        # validation
        add_connector.assert_called_once_with()
        queue.assert_called_once_with(name, url)
        queue.return_value.purge.assert_called_once_with()
        self.assertFalse(queue.delete.called)

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_unregister(self, _agent):
        context = Context()

        # test
        Consumer.unregister(context)

        # validation
        context.__enter__.assert_called_once_with()
        self.assertTrue(context.__exit__.called)

        _agent.assert_called_with(
            context.url,
            context.address,
            secret=context.secret,
            authenticator=context.authenticator,
            wait=0)

        _agent.return_value.Consumer.return_value.unregister.assert_called_with()

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_bind(self, _agent):
        context = Context()
        bindings = []
        options = {}

        # test
        Consumer.bind(context, bindings, options)

        # validation
        context.__enter__.assert_called_once_with()
        self.assertTrue(context.__exit__.called)

        _agent.assert_called_with(
            context.url,
            context.address,
            reply=context.reply_queue,
            secret=context.secret,
            authenticator=context.authenticator,
            data=context.details)

        _agent.return_value.Consumer.return_value.bind.assert_called_with(bindings, options)

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_unbind(self, _agent):
        context = Context()
        bindings = []
        options = {}

        # test
        Consumer.unbind(context, bindings, options)

        # validation
        context.__enter__.assert_called_once_with()
        self.assertTrue(context.__exit__.called)

        _agent.assert_called_with(
            context.url,
            context.address,
            reply=context.reply_queue,
            secret=context.secret,
            authenticator=context.authenticator,
            data=context.details)

        _agent.return_value.Consumer.return_value.unbind.assert_called_with(bindings, options)


class TestContentCapability(TestCase):

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_install(self, _agent):
        context = Context()
        units = []
        options = {}

        # test
        Content.install(context, units, options)

        # validation
        context.__enter__.assert_called_once_with()
        self.assertTrue(context.__exit__.called)

        _agent.assert_called_with(
            context.url,
            context.address,
            reply=context.reply_queue,
            secret=context.secret,
            authenticator=context.authenticator,
            data=context.details)

        _agent.return_value.Content.return_value.install.assert_called_with(units, options)

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_update(self, _agent):
        context = Context()
        units = []
        options = {}

        # test
        Content.update(context, units, options)

        # validation
        context.__enter__.assert_called_once_with()
        self.assertTrue(context.__exit__.called)

        _agent.assert_called_with(
            context.url,
            context.address,
            reply=context.reply_queue,
            secret=context.secret,
            authenticator=context.authenticator,
            data=context.details)

        _agent.return_value.Content.return_value.update.assert_called_with(units, options)

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_uninstall(self, _agent):
        context = Context()
        units = []
        options = {}

        # test
        Content.uninstall(context, units, options)

        # validation
        context.__enter__.assert_called_once_with()
        self.assertTrue(context.__exit__.called)

        _agent.assert_called_with(
            context.url,
            context.address,
            reply=context.reply_queue,
            secret=context.secret,
            authenticator=context.authenticator,
            data=context.details)

        _agent.return_value.Content.return_value.uninstall.assert_called_with(units, options)


class TestProfileCapability(TestCase):

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_send(self, _agent):
        context = Context()

        # test
        Profile.send(context)

        # validation
        context.__enter__.assert_called_once_with()
        self.assertTrue(context.__exit__.called)

        _agent.assert_called_with(
            context.url,
            context.address,
            secret=context.secret,
            authenticator=context.authenticator)

        _agent.return_value.Profile.return_value.send.assert_called_with()


class TestAdminCapability(TestCase):

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_cancel(self, _agent):
        context = Context()
        task_id = '5678'

        # test
        agent = PulpAgent()
        agent.cancel(context, task_id)

        # validation
        context.__enter__.assert_called_once_with()
        self.assertTrue(context.__exit__.called)

        _agent.assert_called_with(
            context.url,
            context.address,
            authenticator=context.authenticator,
            wait=0)

        _agent.return_value.Admin.return_value.cancel.assert_called_with(
            criteria={'match': {'task_id': task_id}})
