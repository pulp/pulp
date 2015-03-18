from unittest import TestCase

from mock import patch, Mock
from gofer.messaging.model import Document
from gofer.rmi.async import Accepted, Rejected, Started, Succeeded, Failed, Progress

from pulp.server.agent.direct.services import Services, ReplyHandler


messaging = {
    'url': 'atlantis',
    'cacert': '/path/ca',
    'clientcert': '/path/cert',
    'transport': 'monkey'
}

conf = {
    'messaging': messaging
}


class Config(object):

    @staticmethod
    def get(section, _property):
        return conf[section][_property]


class TestServices(TestCase):

    @patch('pulp.server.agent.direct.services.add_connector')
    def test_init(self, add_connector):
        Services.init()
        add_connector.assert_called_once_with()

    @patch('pulp.server.agent.direct.services.get_url')
    @patch('pulp.server.agent.direct.services.ReplyHandler')
    def test_start(self, reply_handler, get_url):
        Services.start()
        reply_handler.assert_called_once_with(get_url.return_value)
        reply_handler.return_value.start.assert_called_once_with()


class TestReplyHandler(TestCase):

    @patch('pulp.server.agent.direct.services.Queue', Mock())
    @patch('pulp.server.agent.direct.services.ReplyConsumer', Mock())
    def reply_handler(self):
        return ReplyHandler('')

    @patch('pulp.server.agent.direct.services.Authenticator')
    @patch('pulp.server.agent.direct.services.Queue')
    @patch('pulp.server.agent.direct.services.ReplyConsumer')
    def test_construction(self, mock_consumer, mock_queue, mock_auth):
        url = 'http://broker'
        handler = ReplyHandler(url)
        mock_queue.assert_called_with(ReplyHandler.REPLY_QUEUE)
        mock_queue.return_value.declare.assert_called_with(url)
        self.assertTrue(mock_queue.return_value.durable)
        mock_consumer.assert_called_with(
            mock_queue(), url=url, authenticator=mock_auth())
        self.assertEqual(handler.consumer, mock_consumer())

    def test_start(self):
        handler = self.reply_handler()
        handler.start()
        handler.consumer.start.assert_called_with(handler)

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
        document = Document(routing=['A', 'B'], result=result, data=call_context)
        reply = Succeeded(document)
        handler = self.reply_handler()
        handler.succeeded(reply)

        # validate task updated
        mock_task_succeeded.assert_called_with(
            task_id, result=dispatch_report, timestamp=reply.timestamp)

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_accepted')
    def test_accepted(self, mock_task_accepted):
        task_id = 'task_1'
        call_context = {
            'task_id': task_id
        }
        document = Document(routing=['A', 'B'], data=call_context)
        reply = Accepted(document)
        handler = self.reply_handler()
        handler.accepted(reply)

        # validate task updated
        mock_task_accepted.assert_called_with(task_id)

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_failed')
    def test_rejected(self, mock_task_failed):
        task_id = 'task_1'
        call_context = {
            'task_id': task_id,
        }
        document = Document(routing=['A', 'B'], data=call_context)
        reply = Rejected(document)
        handler = self.reply_handler()
        handler.rejected(reply)

        # validate task updated
        mock_task_failed.assert_called_with(task_id, timestamp=reply.timestamp)

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_started')
    def test_started(self, mock_task_started):
        task_id = 'task_1'
        call_context = {
            'task_id': task_id,
        }
        document = Document(routing=['A', 'B'], data=call_context)
        reply = Started(document)
        handler = self.reply_handler()
        handler.started(reply)

        # validate task updated
        mock_task_started.assert_called_with(task_id, timestamp=reply.timestamp)

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    def test_progress_reported(self, mock_update_task_status):
        task_id = 'task_1'
        call_context = {'task_id': task_id}
        progress_report = {'step': 'step-1'}
        document = Document(routing=['A', 'B'], data=call_context, details=progress_report)
        reply = Progress(document)
        handler = self.reply_handler()
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
        traceback = 'stack-trace'
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
            xstate={'trace': traceback},
            xargs=[]
        )
        document = Document(routing=['A', 'B'], result=raised, data=call_context)
        reply = Failed(document)
        handler = self.reply_handler()
        handler.failed(reply)

        # validate task updated
        mock_task_failed.assert_called_with(task_id, traceback=traceback, timestamp=reply.timestamp)

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
        result = Document(retval=dispatch_report)
        document = Document(routing=['A', 'B'], result=result, data=call_context)
        reply = Succeeded(document)
        handler = self.reply_handler()
        handler.succeeded(reply)

        # validate task updated
        mock_task_succeeded.assert_called_with(
            task_id, result=dispatch_report, timestamp=reply.timestamp)
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
        result = Document(retval=dispatch_report)
        document = Document(routing=['A', 'B'], result=result, data=call_context)
        reply = Succeeded(document)
        handler = self.reply_handler()
        handler.succeeded(reply)

        # validate task updated
        mock_task_succeeded.assert_called_with(
            task_id, result=dispatch_report, timestamp=reply.timestamp)
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
        result = Document(retval=dispatch_report)
        document = Document(routing=['A', 'B'], result=result, data=call_context)
        reply = Succeeded(document)
        handler = self.reply_handler()
        handler.succeeded(reply)

        # validate task updated
        mock_task_succeeded.assert_called_with(
            task_id, result=dispatch_report, timestamp=reply.timestamp)
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
        result = Document(retval=dispatch_report)
        document = Document(routing=['A', 'B'], result=result, data=call_context)
        reply = Succeeded(document)
        handler = self.reply_handler()
        handler.succeeded(reply)

        # validate task updated
        mock_task_succeeded.assert_called_with(
            task_id, result=dispatch_report, timestamp=reply.timestamp)
        # validate bind action updated
        mock_unbind_failed.assert_called_with(task_id, call_context)

    @patch('pulp.server.agent.direct.services.ReplyHandler._bind_failed')
    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_failed')
    def test_bind_failed(self, mock_task_failed, mock_bind_failed):
        task_id = 'task_1'
        consumer_id = 'consumer_1'
        repo_id = 'repo_1'
        dist_id = 'dist_1'
        traceback = 'stack-trace'
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
            xstate={'trace': traceback},
            xargs=[]
        )
        document = Document(routing=['A', 'B'], result=raised, data=call_context)
        reply = Failed(document)
        handler = self.reply_handler()
        handler.failed(reply)

        # validate task updated
        mock_task_failed.assert_called_with(task_id, traceback=traceback, timestamp=reply.timestamp)
        # validate bind action updated
        mock_bind_failed.assert_called_with(task_id, call_context)

    @patch('pulp.server.agent.direct.services.ReplyHandler._bind_failed')
    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_failed')
    def test_bind_rejected(self, mock_task_failed, mock_bind_failed):
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
        document = Document(routing=['A', 'B'], status='rejected', data=call_context)
        reply = Rejected(document)
        handler = self.reply_handler()
        handler.rejected(reply)

        # validate task updated
        mock_task_failed.assert_called_with(task_id, timestamp=reply.timestamp)
        # validate bind action updated
        mock_bind_failed.assert_called_with(task_id, call_context)

    @patch('pulp.server.agent.direct.services.ReplyHandler._unbind_failed')
    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_failed')
    def test_unbind_failed(self, mock_task_failed, mock_unbind_failed):
        task_id = 'task_1'
        consumer_id = 'consumer_1'
        repo_id = 'repo_1'
        dist_id = 'dist_1'
        traceback = 'stack-trace'
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
            xstate={'trace': traceback},
            xargs=[]
        )
        document = Document(routing=['A', 'B'], result=raised, data=call_context)
        reply = Failed(document)
        handler = self.reply_handler()
        handler.failed(reply)

        # validate task updated
        mock_task_failed.assert_called_with(task_id, traceback=traceback, timestamp=reply.timestamp)
        # validate bind action updated
        mock_unbind_failed.assert_called_with(task_id, call_context)

    @patch('pulp.server.agent.direct.services.ReplyHandler._unbind_failed')
    @patch('pulp.server.async.task_status_manager.TaskStatusManager.set_task_failed')
    def test_unbind_rejected(self, mock_task_failed, mock_unbind_failed):
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
        document = Document(routing=['A', 'B'], status='rejected', data=call_context)
        reply = Rejected(document)
        handler = self.reply_handler()
        handler.rejected(reply)

        # validate task updated
        mock_task_failed.assert_called_with(task_id, timestamp=reply.timestamp)
        # validate bind action updated
        mock_unbind_failed.assert_called_with(task_id, call_context)