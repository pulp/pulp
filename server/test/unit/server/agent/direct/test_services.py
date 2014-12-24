from unittest import TestCase

from mock import patch, Mock
from gofer.messaging.model import Document
from gofer.rmi.async import Accepted, Rejected, Started, Succeeded, Failed, Progress

from pulp.common import constants
from pulp.server.agent.direct.services import Services, ReplyHandler
from pulp.server.config import config as pulp_conf


class TestServices(TestCase):

    @patch('pulp.server.agent.direct.services.Broker')
    def test_init(self, mock_broker):
        Services.init()
        url = pulp_conf.get('messaging', 'url')
        transport = pulp_conf.get('messaging', 'transport')
        ca_cert = pulp_conf.get('messaging', 'cacert')
        client_cert = pulp_conf.get('messaging', 'clientcert')
        mock_broker.assert_called_with(url, transport=transport)
        broker = mock_broker()
        self.assertEqual(broker.cacert, ca_cert)
        self.assertEqual(broker.clientcert, client_cert)

    @patch('pulp.server.agent.direct.services.ReplyHandler')
    def test_start(self, mock_reply_handler):
        Services.start()
        mock_reply_handler.start.assert_called()


class TestReplyHandler(TestCase):

    @patch('pulp.server.agent.direct.services.Queue', Mock())
    @patch('pulp.server.agent.direct.services.ReplyConsumer', Mock())
    def reply_handler(self):
        return ReplyHandler('', '')

    @patch('pulp.server.agent.direct.services.Authenticator')
    @patch('pulp.server.agent.direct.services.Queue')
    @patch('pulp.server.agent.direct.services.ReplyConsumer')
    def test_construction(self, mock_consumer, mock_queue, mock_auth):
        url = 'http://broker'
        transport = pulp_conf.get('messaging', 'transport')
        handler = ReplyHandler(url, transport)
        mock_queue.assert_called_with(Services.REPLY_QUEUE, transport=transport)
        mock_consumer.assert_called_with(
            mock_queue(), url=url, transport=transport, authenticator=mock_auth())
        self.assertEqual(handler.consumer, mock_consumer())

    def test_start(self):
        handler = self.reply_handler()
        handler.start()
        handler.consumer.start.assert_called_with(handler)

    @patch('pulp.common.dateutils.format_iso8601_datetime')
    @patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_agent_succeeded(self, mock_task_objects, mock_date):
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
        mock_return_tasks = Mock()
        mock_task_objects.return_value = mock_return_tasks
        test_date = '2014-12-16T20:03:10Z'
        mock_date.return_value = test_date
        result = dict(retval=dispatch_report)
        document = Document(routing=['A', 'B'], result=result, any=call_context)
        reply = Succeeded(document)
        handler = self.reply_handler()
        handler.succeeded(reply)

        # validate task updated
        mock_task_objects.assert_called_with(task_id=task_id)
        mock_return_tasks.update_one.assert_called_with(set__finish_time=test_date,
                                                        set__state=constants.CALL_FINISHED_STATE,
                                                        set__result=dispatch_report)

    @patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_accepted(self, mock_task_objects):
        task_id = 'task_1'
        call_context = {
            'task_id': task_id
        }
        mock_returned_tasks = Mock()
        mock_task_objects.return_value = mock_returned_tasks
        document = Document(routing=['A', 'B'], any=call_context)
        reply = Accepted(document)
        handler = self.reply_handler()
        handler.accepted(reply)

        # validate task updated
        mock_task_objects.assert_called_once_with(task_id=task_id,
                                                  state=constants.CALL_WAITING_STATE)
        mock_returned_tasks.update_one.assert_called_once_with(
            set__state=constants.CALL_ACCEPTED_STATE)

    @patch('pulp.common.dateutils.format_iso8601_datetime')
    @patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_rejected(self, mock_task_objects, mock_date):
        task_id = 'task_1'
        call_context = {
            'task_id': task_id,
        }
        mock_return_tasks = Mock()
        mock_task_objects.return_value = mock_return_tasks
        test_date = '2014-12-16T20:03:10Z'
        mock_date.return_value = test_date
        document = Document(routing=['A', 'B'], any=call_context)
        reply = Rejected(document)
        handler = self.reply_handler()
        handler.rejected(reply)

        # validate task updated
        mock_task_objects.assert_called_with(task_id=task_id)
        mock_return_tasks.update_one.assert_called_with(set__finish_time=test_date,
                                                        set__state=constants.CALL_ERROR_STATE)

    @patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_started(self, mock_task_objects):
        task_id = 'task_1'
        call_context = {
            'task_id': task_id,
        }
        mock_returned_tasks = Mock()
        mock_task_objects.return_value = mock_returned_tasks
        document = Document(routing=['A', 'B'], any=call_context)
        reply = Started(document)
        handler = self.reply_handler()
        handler.started(reply)

        # validate task updated
        mock_task_objects.assert_called_with(task_id=task_id,
                                             state__in=[constants.CALL_WAITING_STATE,
                                                        constants.CALL_ACCEPTED_STATE])
        mock_returned_tasks.update_one.assert_called_with(set__state=constants.CALL_RUNNING_STATE)

    @patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_progress_reported(self, mock_task_objects):
        task_id = 'task_1'
        call_context = {'task_id': task_id}
        progress_report = {'step': 'step-1'}
        test_task_documents = Mock()
        mock_task_objects.return_value = test_task_documents
        document = Document(routing=['A', 'B'], any=call_context, details=progress_report)
        reply = Progress(document)
        handler = self.reply_handler()
        handler.progress(reply)

        # validate task updated
        mock_task_objects.assert_called_with(task_id=task_id)
        test_task_documents.update_one.assert_called_with(set__progress_report=progress_report)

    @patch('pulp.common.dateutils.format_iso8601_datetime')
    @patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_agent_raised_exception(self, mock_task_objects, mock_date):
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
        mock_return_tasks = Mock()
        mock_task_objects.return_value = mock_return_tasks
        test_date = '2014-12-16T20:03:10Z'
        mock_date.return_value = test_date
        document = Document(routing=['A', 'B'], result=raised, any=call_context)
        reply = Failed(document)
        handler = self.reply_handler()
        handler.failed(reply)

        # validate task updated
        mock_task_objects.assert_called_with(task_id=task_id)
        mock_return_tasks.update_one.assert_called_with(set__finish_time=test_date,
                                                        set__state=constants.CALL_ERROR_STATE,
                                                        set__traceback=traceback)

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

    @patch('pulp.common.dateutils.format_iso8601_datetime')
    @patch('pulp.server.agent.direct.services.ReplyHandler._bind_succeeded')
    @patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_bind_succeeded(self, mock_task_objects, mock_bind_succeeded, mock_date):
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
        mock_return_tasks = Mock()
        mock_task_objects.return_value = mock_return_tasks
        test_date = '2014-12-16T20:03:10Z'
        mock_date.return_value = test_date
        dispatch_report = dict(succeeded=True)
        result = Document(retval=dispatch_report)
        document = Document(routing=['A', 'B'], result=result, any=call_context)
        reply = Succeeded(document)
        handler = self.reply_handler()
        handler.succeeded(reply)

        # validate task updated
        mock_task_objects.assert_called_with(task_id=task_id)
        mock_return_tasks.update_one.assert_called_with(set__finish_time=test_date,
                                                        set__state=constants.CALL_FINISHED_STATE,
                                                        set__result=dispatch_report)
        # validate bind action updated
        mock_bind_succeeded.assert_called_with(task_id, call_context)

    @patch('pulp.common.dateutils.format_iso8601_datetime')
    @patch('pulp.server.agent.direct.services.ReplyHandler._bind_failed')
    @patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_bind_succeeded_with_error_report(self, mock_task_objects, mock_bind_failed, mock_date):
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
        mock_return_tasks = Mock()
        mock_task_objects.return_value = mock_return_tasks
        test_date = '2014-12-16T20:03:10Z'
        mock_date.return_value = test_date
        dispatch_report = dict(succeeded=False)
        result = Document(retval=dispatch_report)
        document = Document(routing=['A', 'B'], result=result, any=call_context)
        reply = Succeeded(document)
        handler = self.reply_handler()
        handler.succeeded(reply)

        # validate task updated
        mock_task_objects.assert_called_with(task_id=task_id)
        mock_return_tasks.update_one.assert_called_with(set__finish_time=test_date,
                                                        set__state=constants.CALL_FINISHED_STATE,
                                                        set__result=dispatch_report)
        # validate bind action not updated
        mock_bind_failed.assert_called_with(task_id, call_context)

    @patch('pulp.common.dateutils.format_iso8601_datetime')
    @patch('pulp.server.agent.direct.services.ReplyHandler._unbind_succeeded')
    @patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_unbind_succeeded(self, mock_task_objects, mock_unbind_succeeded, mock_date):
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
        mock_return_tasks = Mock()
        mock_task_objects.return_value = mock_return_tasks
        test_date = '2014-12-16T20:03:10Z'
        mock_date.return_value = test_date
        dispatch_report = dict(succeeded=True)
        result = Document(retval=dispatch_report)
        document = Document(routing=['A', 'B'], result=result, any=call_context)
        reply = Succeeded(document)
        handler = self.reply_handler()
        handler.succeeded(reply)

        # validate task updated
        mock_task_objects.assert_called_with(task_id=task_id)
        mock_return_tasks.update_one.assert_called_with(set__finish_time=test_date,
                                                        set__state=constants.CALL_FINISHED_STATE,
                                                        set__result=dispatch_report)
        # validate bind action updated
        mock_unbind_succeeded.assert_called_with(call_context)

    @patch('pulp.common.dateutils.format_iso8601_datetime')
    @patch('pulp.server.agent.direct.services.ReplyHandler._unbind_failed')
    @patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_unbind_succeeded_with_error_report(self, mock_task_objects, mock_unbind_failed,
                                                mock_date):
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
        mock_return_tasks = Mock()
        mock_task_objects.return_value = mock_return_tasks
        test_date = '2014-12-16T20:03:10Z'
        mock_date.return_value = test_date
        dispatch_report = dict(succeeded=False)
        result = Document(retval=dispatch_report)
        document = Document(routing=['A', 'B'], result=result, any=call_context)
        reply = Succeeded(document)
        handler = self.reply_handler()
        handler.succeeded(reply)

        # validate task updated
        mock_task_objects.assert_called_with(task_id=task_id)
        mock_return_tasks.update_one.assert_called_with(set__finish_time=test_date,
                                                        set__state=constants.CALL_FINISHED_STATE,
                                                        set__result=dispatch_report)
        # validate bind action updated
        mock_unbind_failed.assert_called_with(task_id, call_context)

    @patch('pulp.common.dateutils.format_iso8601_datetime')
    @patch('pulp.server.agent.direct.services.ReplyHandler._bind_failed')
    @patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_bind_failed(self, mock_task_objects, mock_bind_failed, mock_date):
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
        mock_return_tasks = Mock()
        mock_task_objects.return_value = mock_return_tasks
        test_date = '2014-12-16T20:03:10Z'
        mock_date.return_value = test_date
        document = Document(routing=['A', 'B'], result=raised, any=call_context)
        reply = Failed(document)
        handler = self.reply_handler()
        handler.failed(reply)

        # validate task updated
        mock_task_objects.assert_called_with(task_id=task_id)
        mock_return_tasks.update_one.assert_called_with(set__finish_time=test_date,
                                                        set__state=constants.CALL_ERROR_STATE,
                                                        set__traceback=traceback)
        # validate bind action updated
        mock_bind_failed.assert_called_with(task_id, call_context)

    @patch('pulp.common.dateutils.format_iso8601_datetime')
    @patch('pulp.server.agent.direct.services.ReplyHandler._bind_failed')
    @patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_bind_rejected(self, mock_task_objects, mock_bind_failed, mock_date):
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
        mock_return_tasks = Mock()
        mock_task_objects.return_value = mock_return_tasks
        test_date = '2014-12-16T20:03:10Z'
        mock_date.return_value = test_date
        document = Document(routing=['A', 'B'], status='rejected', any=call_context)
        reply = Rejected(document)
        handler = self.reply_handler()
        handler.rejected(reply)

        # validate task updated
        mock_task_objects.assert_called_with(task_id=task_id)
        mock_return_tasks.update_one.assert_called_with(set__finish_time=test_date,
                                                        set__state=constants.CALL_ERROR_STATE)
        # validate bind action updated
        mock_bind_failed.assert_called_with(task_id, call_context)

    @patch('pulp.common.dateutils.format_iso8601_datetime')
    @patch('pulp.server.agent.direct.services.ReplyHandler._unbind_failed')
    @patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_unbind_failed(self, mock_task_objects, mock_unbind_failed, mock_date):
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
        mock_return_tasks = Mock()
        mock_task_objects.return_value = mock_return_tasks
        test_date = '2014-12-16T20:03:10Z'
        mock_date.return_value = test_date
        document = Document(routing=['A', 'B'], result=raised, any=call_context)
        reply = Failed(document)
        handler = self.reply_handler()
        handler.failed(reply)

        # validate task updated
        mock_task_objects.assert_called_with(task_id=task_id)
        mock_return_tasks.update_one.assert_called_with(set__finish_time=test_date,
                                                        set__state=constants.CALL_ERROR_STATE,
                                                        set__traceback=traceback)
        # validate bind action updated
        mock_unbind_failed.assert_called_with(task_id, call_context)

    @patch('pulp.common.dateutils.format_iso8601_datetime')
    @patch('pulp.server.agent.direct.services.ReplyHandler._unbind_failed')
    @patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_unbind_rejected(self, mock_task_objects, mock_unbind_failed, mock_date):
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
        mock_return_tasks = Mock()
        mock_task_objects.return_value = mock_return_tasks
        test_date = '2014-12-16T20:03:10Z'
        mock_date.return_value = test_date
        document = Document(routing=['A', 'B'], status='rejected', any=call_context)
        reply = Rejected(document)
        handler = self.reply_handler()
        handler.rejected(reply)

        # validate task updated
        mock_task_objects.assert_called_with(task_id=task_id)
        mock_return_tasks.update_one.assert_called_with(set__finish_time=test_date,
                                                        set__state=constants.CALL_ERROR_STATE)
        # validate bind action updated
        mock_unbind_failed.assert_called_with(task_id, call_context)
