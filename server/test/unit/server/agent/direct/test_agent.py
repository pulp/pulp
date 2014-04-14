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


class TestConsumerCapability(TestCase):

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_unregistered(self, mock_gofer_agent):
        context = Mock()
        context.agent_id = '123'
        context.secret = 'test-secret'
        context.url = 'http://broker.com'
        context.transport = 'qpid'
        context.authenticator = Mock()

        mock_agent = Mock()
        mock_gofer_agent.return_value = mock_agent
        mock_consumer = Mock()
        mock_agent.Consumer = Mock(return_value=mock_consumer)

        # test capability

        Consumer.unregistered(context)

        # validation

        mock_gofer_agent.assert_called_with(
            context.agent_id,
            url=context.url,
            secret=context.secret,
            authenticator=context.authenticator,
            transport=context.transport,
            async=True)

        mock_consumer.unregistered.assert_called_with()

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_bind(self, mock_gofer_agent):
        context = Mock()
        context.agent_id = '123'
        context.secret = 'test-secret'
        context.url = 'http://broker.com'
        context.transport = 'qpid'
        context.authenticator = Mock()
        context.details = {'task_id': '4567'}
        context.reply_queue = 'pulp.task'

        mock_agent = Mock()
        mock_gofer_agent.return_value = mock_agent
        mock_consumer = Mock()
        mock_agent.Consumer = Mock(return_value=mock_consumer)

        bindings = []
        options = {}

        Consumer.bind(context, bindings, options)

        mock_gofer_agent.assert_called_with(
            context.agent_id,
            ctag=context.reply_queue,
            url=context.url,
            transport=context.transport,
            secret=context.secret,
            authenticator=context.authenticator,
            any=context.details)

        mock_consumer.bind.assert_called_with(bindings, options)

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_unbind(self, mock_gofer_agent):
        context = Mock()
        context.agent_id = '123'
        context.secret = 'test-secret'
        context.url = 'http://broker.com'
        context.transport = 'qpid'
        context.authenticator = Mock()
        context.details = {'task_id': '4567'}
        context.reply_queue = 'pulp.task'

        mock_agent = Mock()
        mock_gofer_agent.return_value = mock_agent
        mock_consumer = Mock()
        mock_agent.Consumer = Mock(return_value=mock_consumer)

        bindings = []
        options = {}

        Consumer.unbind(context, bindings, options)

        mock_gofer_agent.assert_called_with(
            context.agent_id,
            ctag=context.reply_queue,
            url=context.url,
            transport=context.transport,
            secret=context.secret,
            authenticator=context.authenticator,
            any=context.details)

        mock_consumer.unbind.assert_called_with(bindings, options)


class TestContentCapability(TestCase):

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_install(self, mock_gofer_agent):
        context = Mock()
        context.agent_id = '123'
        context.secret = 'test-secret'
        context.url = 'http://broker.com'
        context.transport = 'qpid'
        context.authenticator = Mock()
        context.details = {'task_id': '4567'}
        context.reply_queue = 'pulp.task'

        mock_agent = Mock()
        mock_gofer_agent.return_value = mock_agent
        mock_content = Mock()
        mock_agent.Content = Mock(return_value=mock_content)

        units = []
        options = {}

        Content.install(context, units, options)

        mock_gofer_agent.assert_called_with(
            context.agent_id,
            ctag=context.reply_queue,
            url=context.url,
            transport=context.transport,
            secret=context.secret,
            authenticator=context.authenticator,
            any=context.details)

        mock_content.install.assert_called_with(units, options)

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_update(self, mock_gofer_agent):
        context = Mock()
        context.agent_id = '123'
        context.secret = 'test-secret'
        context.url = 'http://broker.com'
        context.transport = 'qpid'
        context.authenticator = Mock()
        context.details = {'task_id': '4567'}
        context.reply_queue = 'pulp.task'

        mock_agent = Mock()
        mock_gofer_agent.return_value = mock_agent
        mock_content = Mock()
        mock_agent.Content = Mock(return_value=mock_content)

        units = []
        options = {}

        Content.update(context, units, options)

        mock_gofer_agent.assert_called_with(
            context.agent_id,
            ctag=context.reply_queue,
            url=context.url,
            transport=context.transport,
            secret=context.secret,
            authenticator=context.authenticator,
            any=context.details)

        mock_content.update.assert_called_with(units, options)

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_uninstall(self, mock_gofer_agent):
        context = Mock()
        context.agent_id = '123'
        context.secret = 'test-secret'
        context.url = 'http://broker.com'
        context.transport = 'qpid'
        context.authenticator = Mock()
        context.details = {'task_id': '4567'}
        context.reply_queue = 'pulp.task'

        mock_agent = Mock()
        mock_gofer_agent.return_value = mock_agent
        mock_content = Mock()
        mock_agent.Content = Mock(return_value=mock_content)

        units = []
        options = {}

        Content.uninstall(context, units, options)

        mock_gofer_agent.assert_called_with(
            context.agent_id,
            ctag=context.reply_queue,
            url=context.url,
            transport=context.transport,
            secret=context.secret,
            authenticator=context.authenticator,
            any=context.details)

        mock_content.uninstall.assert_called_with(units, options)


class TestProfileCapability(TestCase):

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_send(self, mock_gofer_agent):
        context = Mock()
        context.agent_id = '123'
        context.secret = 'test-secret'
        context.url = 'http://broker.com'
        context.transport = 'qpid'
        context.authenticator = Mock()

        mock_agent = Mock()
        mock_gofer_agent.return_value = mock_agent
        mock_profile = Mock()
        mock_agent.Profile = Mock(return_value=mock_profile)

        Profile.send(context)

        mock_gofer_agent.assert_called_with(
            context.agent_id,
            url=context.url,
            transport=context.transport,
            secret=context.secret,
            authenticator=context.authenticator)

        mock_profile.send.assert_called_with()


class TestAdminCapability(TestCase):

    @patch('pulp.server.agent.direct.pulpagent.Agent')
    def test_send(self, mock_gofer_agent):
        context = Mock()
        context.agent_id = '123'
        context.url = 'http://broker.com'
        context.transport = 'qpid'
        context.authenticator = Mock()

        task_id = '5678'
        criteria = {'match': {'task_id': task_id}}

        mock_agent = Mock()
        mock_gofer_agent.return_value = mock_agent
        mock_admin = Mock()
        mock_agent.Admin = Mock(return_value=mock_admin)

        agent = PulpAgent()
        agent.cancel(context, task_id)

        mock_gofer_agent.assert_called_with(
            context.agent_id,
            url=context.url,
            transport=context.transport,
            authenticator=context.authenticator,
            async=True)

        mock_admin.cancel.assert_called_with(criteria=criteria)
