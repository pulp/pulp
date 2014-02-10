# Copyright (c) 2013 Red Hat, Inc.
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
from gofer.messaging import Envelope
from gofer.messaging.broker import URL, Broker
from gofer.rmi.async import Started, Succeeded, Failed, Progress

from pulp.server.config import config as pulp_conf
from pulp.server.agent.direct.services import Services, ReplyHandler


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

    @patch('pulp.server.agent.direct.services.Journal')
    @patch('pulp.server.agent.direct.services.ReplyHandler')
    @patch('gofer.rmi.async.WatchDog')
    def test_start(self, mock_watchdog, mock_reply_handler, mock_journal):
        Services.start()
        mock_watchdog.start.assert_called()
        mock_reply_handler.start.assert_called()


class TestReplyHandler(TestCase):

    @patch('gofer.rmi.async.ReplyConsumer.start')
    def test_start(self, mock_start):
        url = 'http://broker'
        handler = ReplyHandler(url)
        watchdog = Mock()
        handler.start(watchdog)
        mock_start.assert_called_with(handler, watchdog=watchdog)


    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_succeeded')
    def test_agent_succeeded(self, mock_task_succeeded):
        dispatch_report = dict(succeeded=True)
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
        result = dict(retval=dispatch_report)
        envelope = Envelope(routing=['A', 'B'], result=result, any=call_context)
        reply = Succeeded(envelope)
        handler = ReplyHandler('')
        handler.succeeded(reply)

        # validate task updated
        mock_task_succeeded.assert_called_with(task_id, dispatch_report)

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_started')
    def test_started(self, mock_task_started):
        dispatch_report = dict(succeeded=True)
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
        envelope = Envelope(routing=['A', 'B'], any=call_context)
        reply = Started(envelope)
        handler = ReplyHandler('')
        handler.started(reply)

        # validate task updated
        mock_task_started.assert_called_with(task_id)

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    def test_progress_reported(self, mock_update_task_status):
        task_id = 'task_1'
        call_context = {'task_id': task_id}
        progress_report = {'step': 'step-1'}
        envelope = Envelope(routing=['A', 'B'], any=call_context, details=progress_report)
        reply = Progress(envelope)
        handler = ReplyHandler('')
        handler.progress(reply)

        # validate task updated
        delta = {'progress_report': progress_report}
        mock_update_task_status.assert_called_with(task_id, delta)

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_failed')
    def test_agent_raised_exception(self, mock_task_failed):
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
        raised = dict(
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
        mock_task_failed.assert_called_with(task_id, 'stack-trace')

    @patch('pulp.server.managers.factory.consumer_bind_manager')
    def test__bind_succeeded(self, mock_get_manager):
        bind_manager = Mock()
        mock_get_manager.return_value = bind_manager
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
        ReplyHandler._bind_succeeded(task_id, call_context)
        bind_manager.action_succeeded.assert_called_with(consumer_id, repo_id, dist_id, task_id)

    @patch('pulp.server.managers.factory.consumer_bind_manager')
    def test__bind_failed(self, mock_get_manager):
        bind_manager = Mock()
        mock_get_manager.return_value = bind_manager
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
        # handler report: failed
        ReplyHandler._bind_failed(task_id, call_context)
        bind_manager.action_failed.assert_called_with(consumer_id, repo_id, dist_id, task_id)

    @patch('pulp.server.managers.factory.consumer_bind_manager')
    def test__unbind_succeeded(self, mock_get_manager):
        bind_manager = Mock()
        mock_get_manager.return_value = bind_manager
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
        # handler report: succeeded
        ReplyHandler._unbind_succeeded(call_context)
        bind_manager.delete.assert_called_with(consumer_id, repo_id, dist_id, force=True)

    @patch('pulp.server.managers.factory.consumer_bind_manager')
    def test__unbind_failed(self, mock_get_manager):
        bind_manager = Mock()
        mock_get_manager.return_value = bind_manager
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
        # handler report: failed
        ReplyHandler._unbind_failed(task_id, call_context)
        bind_manager.action_failed.assert_called_with(consumer_id, repo_id, dist_id, task_id)

    @patch('pulp.server.agent.direct.services.ReplyHandler._bind_succeeded')
    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_succeeded')
    def test_bind_succeeded(self, mock_task_succeeded, mock_bind_succeeded):
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
        dispatch_report = dict(succeeded=True)
        result = Envelope(retval=dispatch_report)
        envelope = Envelope(routing=['A', 'B'], result=result, any=call_context)
        reply = Succeeded(envelope)
        handler = ReplyHandler('')
        handler.succeeded(reply)

        # validate task updated
        mock_task_succeeded.assert_called_with(task_id, dispatch_report)
        # validate bind action updated
        mock_bind_succeeded.assert_called_with(task_id, call_context)

    @patch('pulp.server.agent.direct.services.ReplyHandler._bind_failed')
    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_succeeded')
    def test_bind_succeeded_with_error_report(self, mock_task_succeeded, mock_bind_failed):
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
        dispatch_report = dict(succeeded=False)
        result = Envelope(retval=dispatch_report)
        envelope = Envelope(routing=['A', 'B'], result=result, any=call_context)
        reply = Succeeded(envelope)
        handler = ReplyHandler('')
        handler.succeeded(reply)

        # validate task updated
        mock_task_succeeded.assert_called_with(task_id, dispatch_report)
        # validate bind action not updated
        mock_bind_failed.assert_called_with(task_id, call_context)

    @patch('pulp.server.agent.direct.services.ReplyHandler._unbind_succeeded')
    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_succeeded')
    def test_unbind_succeeded(self, mock_task_succeeded, mock_unbind_succeeded):
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
        dispatch_report = dict(succeeded=True)
        result = Envelope(retval=dispatch_report)
        envelope = Envelope(routing=['A', 'B'], result=result, any=call_context)
        reply = Succeeded(envelope)
        handler = ReplyHandler('')
        handler.succeeded(reply)

        # validate task updated
        mock_task_succeeded.assert_called_with(task_id, dispatch_report)
        # validate bind action updated
        mock_unbind_succeeded.assert_called_with(call_context)

    @patch('pulp.server.agent.direct.services.ReplyHandler._unbind_failed')
    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_succeeded')
    def test_unbind_succeeded_with_error_report(self, mock_task_succeeded, mock_unbind_failed):
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
        dispatch_report = dict(succeeded=False)
        result = Envelope(retval=dispatch_report)
        envelope = Envelope(routing=['A', 'B'], result=result, any=call_context)
        reply = Succeeded(envelope)
        handler = ReplyHandler('')
        handler.succeeded(reply)

        # validate task updated
        mock_task_succeeded.assert_called_with(task_id, dispatch_report)
        # validate bind action updated
        mock_unbind_failed.assert_called_with(task_id, call_context)

    @patch('pulp.server.agent.direct.services.ReplyHandler._bind_failed')
    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_failed')
    def test_bind_failed(self, mock_task_failed, mock_bind_failed):
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
        raised = dict(
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
        mock_task_failed.assert_called_with(task_id, 'stack-trace')
        # validate bind action updated
        mock_bind_failed.assert_called_with(task_id, call_context)

    @patch('pulp.server.agent.direct.services.ReplyHandler._unbind_failed')
    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_failed')
    def test_unbind_failed(self, mock_task_failed, mock_unbind_failed):
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
        raised = dict(
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
        mock_task_failed.assert_called_with(task_id, 'stack-trace')
        # validate bind action updated
        mock_unbind_failed.assert_called_with(task_id, call_context)