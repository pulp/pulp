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

import hashlib
from unittest import TestCase

from mock import patch, Mock
from gofer.messaging import Envelope
from gofer.messaging.broker import URL, Broker
from gofer.rmi.async import Started, Succeeded, Failed

from base import PulpServerTests
from pulp.devel import mock_agent
from pulp.server.config import config as pulp_conf
from pulp.server.agent import Context
from pulp.server.agent.direct.pulpagent import PulpAgent
from pulp.server.agent.direct.services import HeartbeatListener, Services, ReplyHandler


REPO_ID = 'repo_1'
DETAILS = {}
BINDINGS = [
    {'type_id': 'yum',
     'repo_id': REPO_ID,
     'details': DETAILS}
]
CONSUMER = {
    'id': 'gc',
    'certificate': 'XXX',
}
UNIT = {
    'type_id': 'rpm',
    'unit_key': {
        'name': 'zsh',
    }
}
UNITS = [UNIT]
OPTIONS = {
    'xxx': True,
}

TASK_ID = 'TASK-123'

CONTEXT_DETAILS = {
    'task_id': TASK_ID
}

CONTEXT = Context(CONSUMER, **CONTEXT_DETAILS)


class TestContext(TestCase):

    def test_context(self):
        h = hashlib.sha256()
        h.update(CONSUMER['certificate'])
        secret = h.hexdigest()
        context = Context(CONSUMER, **CONTEXT_DETAILS)
        self.assertEqual(context.uuid, CONSUMER['id'])
        self.assertEqual(context.url, pulp_conf.get('messaging', 'url'))
        self.assertEqual(context.secret, secret)
        self.assertEqual(context.details, CONTEXT_DETAILS)
        self.assertEqual(context.reply_queue, Services.REPLY_QUEUE)
        self.assertEqual(context.watchdog, Services.watchdog)


class TestAgent(PulpServerTests):
    
    def setUp(self):
        PulpServerTests.setUp(self)
        mock_agent.install()
        mock_agent.reset()

    def test_unregistered(self):
        # Test
        agent = PulpAgent()
        agent.consumer.unregistered(CONTEXT)
        # Verify
        mock_agent.Consumer.unregistered.assert_called_once_with()
        
    def test_bind(self):
        # Test
        agent = PulpAgent()
        result = agent.consumer.bind(CONTEXT, BINDINGS, OPTIONS)
        # Verify
        mock_agent.Consumer.bind.assert_called_once_with(BINDINGS, OPTIONS)
        
    def test_unbind(self):
        # Test
        agent = PulpAgent()
        result = agent.consumer.unbind(CONTEXT, BINDINGS, OPTIONS)
        # Verify
        mock_agent.Consumer.unbind.assert_called_once_with(BINDINGS, OPTIONS)
        
    def test_install_content(self):
        # Test
        agent = PulpAgent()
        result = agent.content.install(CONTEXT, UNITS, OPTIONS)
        # Verify
        mock_agent.Content.install.assert_called_once_with(UNITS, OPTIONS)
        
    def test_update_content(self):
        # Test
        agent = PulpAgent()
        result = agent.content.update(CONTEXT, UNITS, OPTIONS)
        # Verify
        mock_agent.Content.update.assert_called_once_with(UNITS, OPTIONS)
        
    def test_uninstall_content(self):
        # Test
        agent = PulpAgent()
        result = agent.content.uninstall(CONTEXT, UNITS, OPTIONS)
        # Verify
        mock_agent.Content.uninstall.assert_called_once_with(UNITS, OPTIONS)

    def test_profile_send(self):
        # Test
        agent = PulpAgent()
        print agent.profile.send(CONTEXT)
        # Verify
        mock_agent.Profile.send.assert_called_once_with()

    def test_status(self):
        # Setup
        listener = HeartbeatListener('queue')
        envelope = Envelope(heartbeat=dict(uuid='A', next=10))
        listener.dispatch(envelope)
        # Test
        result = PulpAgent.status(['A','B'])
        # Verify
        self.assertEqual(len(result), 2)
        # A
        alive, next_heartbeat, details = result['A']
        self.assertTrue(alive)
        self.assertTrue(isinstance(next_heartbeat, basestring))
        self.assertTrue(isinstance(details, dict))
        # B
        alive, last_heartbeat, details = result['B']
        self.assertFalse(alive)
        self.assertTrue(last_heartbeat is None)
        self.assertTrue(isinstance(details, dict))

    def test_cancel(self):
        # Test
        task_id = '123'
        agent = PulpAgent()
        agent.cancel(CONTEXT, task_id)
        # Verify
        criteria = {'match': {'task_id': task_id}}
        mock_agent.Admin.cancel.assert_called_once_with(criteria=criteria)


class TestReplyHandler(TestCase):

    @patch('gofer.rmi.async.ReplyConsumer.start')
    def test_start(self, mock_start):
        url = 'http://broker'
        handler = ReplyHandler(url)
        watchdog = Mock()
        handler.start(watchdog)
        mock_start.start_called_with(watchdog)


    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_succeeded')
    def test_agent_succeeded(self, task_succeeded):
        dispatch_report = Envelope(succeeded=True)
        task_id = 'task_1'
        consumer_id = 'consumer_1'
        repo_id = 'repo_1'
        dist_id = 'dist_1'
        call_context = {
            'task_id': task_id,
            'consumer_id': consumer_id,
            'repo_id': repo_id,
            'distributor_id': dist_id
        }
        result = Envelope(retval=dispatch_report)
        envelope = Envelope(routing=['A', 'B'], result=result, any=call_context)
        reply = Succeeded(envelope)
        handler = ReplyHandler('')
        handler.succeeded(reply)

        # validate task updated
        task_succeeded.assert_called_with(task_id, dispatch_report)

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_started')
    def test_started(self, task_started):
        dispatch_report = Envelope(succeeded=True)
        task_id = 'task_1'
        consumer_id = 'consumer_1'
        repo_id = 'repo_1'
        dist_id = 'dist_1'
        call_context = {
            'task_id': task_id,
            'consumer_id': consumer_id,
            'repo_id': repo_id,
            'distributor_id': dist_id
        }
        result = Envelope(retval=dispatch_report)
        envelope = Envelope(routing=['A', 'B'], result=result, any=call_context)
        reply = Started(envelope)
        handler = ReplyHandler('')
        handler.started(reply)

        # validate task updated
        task_started.assert_called_with(task_id)

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_failed')
    def test_agent_raised_exception(self, task_failed):
        task_id = 'task_1'
        consumer_id = 'consumer_1'
        repo_id = 'repo_1'
        dist_id = 'dist_1'
        call_context = {
            'task_id': task_id,
            'consumer_id': consumer_id,
            'repo_id': repo_id,
            'distributor_id': dist_id
        }
        raised = Envelope(
            exval='Boom',
            xmodule='foo.py',
            xclass=ValueError,
            xstate={'trace': 'stack-trace'},
            xargs=[]
        )
        envelope = Envelope(routing=['A', 'B'], result=raised, any=call_context)
        reply = Failed(envelope)
        handler = ReplyHandler('')
        handler.failed(reply)

        # validate task updated
        task_failed.assert_called_with(task_id, 'stack-trace')

    @patch('pulp.server.managers.factory.consumer_bind_manager')
    def test_update_bind_action(self, get_manager):
        bind_manager = Mock()
        get_manager.return_value = bind_manager
        task_id = 'task_1'
        consumer_id = 'consumer_1'
        repo_id = 'repo_1'
        dist_id = 'dist_1'
        call_context = {
            'action': 'bind',
            'task_id': task_id,
            'consumer_id': consumer_id,
            'repo_id': repo_id,
            'distributor_id': dist_id
        }
        # handler report: succeeded
        ReplyHandler._update_bind_action(task_id, call_context, True)
        bind_manager.action_succeeded.assert_called_with(consumer_id, repo_id, dist_id, task_id)
        # handler report: failed
        ReplyHandler._update_bind_action(task_id, call_context, False)
        bind_manager.action_failed.assert_called_with(consumer_id, repo_id, dist_id, task_id)

    @patch('pulp.server.agent.direct.services.ReplyHandler._update_bind_action')
    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_succeeded')
    def test_bind_succeeded(self, task_succeeded, update_action):
        task_id = 'task_1'
        consumer_id = 'consumer_1'
        repo_id = 'repo_1'
        dist_id = 'dist_1'
        call_context = {
            'action': 'bind',
            'task_id': task_id,
            'consumer_id': consumer_id,
            'repo_id': repo_id,
            'distributor_id': dist_id
        }
        dispatch_report = Envelope(succeeded=True)
        result = Envelope(retval=dispatch_report)
        envelope = Envelope(routing=['A', 'B'], result=result, any=call_context)
        reply = Succeeded(envelope)
        handler = ReplyHandler('')
        handler.succeeded(reply)

        # validate task updated
        task_succeeded.assert_called_with(task_id, dispatch_report)
        # validate bind action updated
        update_action.called_with(task_id, call_context, True)

    @patch('pulp.server.agent.direct.services.ReplyHandler._update_bind_action')
    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_succeeded')
    def test_unbind_succeeded(self, task_succeeded, update_action):
        task_id = 'task_1'
        consumer_id = 'consumer_1'
        repo_id = 'repo_1'
        dist_id = 'dist_1'
        call_context = {
            'action': 'unbind',
            'task_id': task_id,
            'consumer_id': consumer_id,
            'repo_id': repo_id,
            'distributor_id': dist_id
        }
        dispatch_report = Envelope(succeeded=True)
        result = Envelope(retval=dispatch_report)
        envelope = Envelope(routing=['A', 'B'], result=result, any=call_context)
        reply = Succeeded(envelope)
        handler = ReplyHandler('')
        handler.succeeded(reply)

        # validate task updated
        task_succeeded.assert_called_with(task_id, dispatch_report)
        # validate bind action updated
        update_action.called_with(task_id, call_context, True)

    @patch('pulp.server.agent.direct.services.ReplyHandler._update_bind_action')
    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_failed')
    def test_bind_failed(self, task_failed, update_action):
        task_id = 'task_1'
        consumer_id = 'consumer_1'
        repo_id = 'repo_1'
        dist_id = 'dist_1'
        call_context = {
            'action': 'bind',
            'task_id': task_id,
            'consumer_id': consumer_id,
            'repo_id': repo_id,
            'distributor_id': dist_id
        }
        raised = Envelope(
            exval='Boom',
            xmodule='foo.py',
            xclass=ValueError,
            xstate={'trace': 'stack-trace'},
            xargs=[]
        )
        envelope = Envelope(routing=['A', 'B'], result=raised, any=call_context)
        reply = Failed(envelope)
        handler = ReplyHandler('')
        handler.failed(reply)

        # validate task updated
        task_failed.assert_called_with(task_id, 'stack-trace')
        # validate bind action updated
        update_action.called_with(task_id, call_context, False)

    @patch('pulp.server.agent.direct.services.ReplyHandler._update_bind_action')
    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_failed')
    def test_unbind_failed(self, task_failed, update_action):
        task_id = 'task_1'
        consumer_id = 'consumer_1'
        repo_id = 'repo_1'
        dist_id = 'dist_1'
        call_context = {
            'action': 'unbind',
            'task_id': task_id,
            'consumer_id': consumer_id,
            'repo_id': repo_id,
            'distributor_id': dist_id
        }
        raised = Envelope(
            exval='Boom',
            xmodule='foo.py',
            xclass=ValueError,
            xstate={'trace': 'stack-trace'},
            xargs=[]
        )
        envelope = Envelope(routing=['A', 'B'], result=raised, any=call_context)
        reply = Failed(envelope)
        handler = ReplyHandler('')
        handler.failed(reply)

        # validate task updated
        task_failed.assert_called_with(task_id, 'stack-trace')
        # validate bind action updated
        update_action.called_with(task_id, call_context, False)


class TestServices(TestCase):

    def test_init(self):
        Services.init()
        url = pulp_conf.get('messaging', 'url')
        ca_cert = pulp_conf.get('messaging', 'cacert')
        client_cert = pulp_conf.get('messaging', 'clientcert')
        broker = Broker(url)
        self.assertEqual(broker.url, URL(url))
        self.assertEqual(broker.cacert, ca_cert)
        self.assertEqual(broker.clientcert, client_cert)

    @patch('pulp.server.agent.direct.services.ReplyHandler')
    @patch('pulp.server.agent.direct.services.HeartbeatListener')
    @patch('gofer.rmi.async.WatchDog')
    def test_start(self, watchdog, heartbeat_listener, reply_handler):
        Services.start()
        watchdog.assert_called()
        heartbeat_listener.assert_called()
        reply_handler.assert_called()