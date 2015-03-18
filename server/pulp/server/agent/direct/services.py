from gettext import gettext as _
from logging import getLogger

from gofer.messaging import Queue
from gofer.rmi.async import ReplyConsumer, Listener

from pulp.server.agent.auth import Authenticator
from pulp.server.agent.connector import get_url, add_connector
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.managers import factory as managers


log = getLogger(__name__)


class Services(object):
    """
    Agent services.
    :cvar reply_handler: Asynchronous RMI reply listener.
    :type reply_handler: ReplyHandler
    """

    reply_handler = None

    @staticmethod
    def init():
        add_connector()

    @staticmethod
    def start():
        """
        Start the agent services.
        """
        url = get_url()
        Services.reply_handler = ReplyHandler(url)
        Services.reply_handler.start()
        log.info(_('AMQP reply handler started'))


class ReplyHandler(Listener):
    """
    The async RMI reply handler.
    :cvar REPLY_QUEUE: The agent RMI reply queue.
    :type REPLY_QUEUE: str
    :ivar consumer: The reply consumer.
    :type consumer: ReplyConsumer
    """

    REPLY_QUEUE = 'pulp.task'


    @staticmethod
    def _bind_succeeded(action_id, call_context):
        """
        Bind succeeded.
        Update the bind action.
        :param action_id: The action ID (basically the task_id).
        :type action_id: str
        :param call_context: The information about the bind call that was
            passed to the agent to be round tripped back here.
        :type call_context: dict
        """
        manager = managers.consumer_bind_manager()
        consumer_id = call_context['consumer_id']
        repo_id = call_context['repo_id']
        distributor_id = call_context['distributor_id']
        manager.action_succeeded(consumer_id, repo_id, distributor_id, action_id)

    @staticmethod
    def _unbind_succeeded(call_context):
        """
        Update the bind action.
        :param call_context: The information about the bind call that was
            passed to the agent to be round tripped back here.
        :type call_context: dict
        """
        manager = managers.consumer_bind_manager()
        consumer_id = call_context['consumer_id']
        repo_id = call_context['repo_id']
        distributor_id = call_context['distributor_id']
        manager.delete(consumer_id, repo_id, distributor_id, force=True)

    @staticmethod
    def _bind_failed(action_id, call_context):
        """
        The bind failed.
        Update the bind action.
        :param action_id: The action ID (basically the task_id).
        :type action_id: str
        :param call_context: The information about the bind call that was
            passed to the agent to be round tripped back here.
        :type call_context: dict
        """
        manager = managers.consumer_bind_manager()
        consumer_id = call_context['consumer_id']
        repo_id = call_context['repo_id']
        distributor_id = call_context['distributor_id']
        manager.action_failed(consumer_id, repo_id, distributor_id, action_id)

    # added for clarity
    _unbind_failed = _bind_failed

    def __init__(self, url):
        """
        :param url: The broker URL.
        :type url: str
        """
        queue = Queue(ReplyHandler.REPLY_QUEUE)
        queue.durable = True
        queue.declare(url)
        self.consumer = ReplyConsumer(queue, url=url, authenticator=Authenticator())

    # --- agent replies ------------------------------------------------------

    def start(self):
        """
        Start the reply handler (thread)
        """
        self.consumer.start(self)
        log.info(_('Task reply handler, started.'))

    def accepted(self, reply):
        """
        Notification that an RMI has started executing in the agent.
        The task status is updated in the pulp DB.
        :param reply: A status reply object.
        :type reply: gofer.rmi.async.Accepted
        """
        log.debug(_('Task RMI (accepted): %(r)s'), {'r': reply})
        call_context = dict(reply.data)
        task_id = call_context['task_id']
        TaskStatusManager.set_task_accepted(task_id)

    def started(self, reply):
        """
        Notification that an RMI has started executing in the agent.
        The task status is updated in the pulp DB.
        :param reply: A status reply object.
        :type reply: gofer.rmi.async.Started
        """
        log.debug(_('Task RMI (started): %(r)s'), {'r': reply})
        call_context = dict(reply.data)
        task_id = call_context['task_id']
        TaskStatusManager.set_task_started(task_id, timestamp=reply.timestamp)

    def rejected(self, reply):
        """
        Notification (reply) indicating an RMI request has been rejected.
        This information used to update the task status.
        :param reply: A rejected reply object.
        :type reply: gofer.rmi.async.Rejected
        """
        log.warn(_('Task RMI (rejected): %(r)s'), {'r': reply})

        call_context = dict(reply.data)
        action = call_context.get('action')
        task_id = call_context['task_id']

        TaskStatusManager.set_task_failed(task_id, timestamp=reply.timestamp)

        if action == 'bind':
            ReplyHandler._bind_failed(task_id, call_context)
            return
        if action == 'unbind':
            ReplyHandler._unbind_failed(task_id, call_context)
            return

    def succeeded(self, reply):
        """
        Notification (reply) indicating an RMI succeeded.
        This information is relayed to the task coordinator.
        :param reply: A successful reply object.
        :type reply: gofer.rmi.async.Succeeded
        """
        log.info(_('Task RMI (succeeded): %(r)s'), {'r': reply})

        call_context = dict(reply.data)
        action = call_context.get('action')
        task_id = call_context['task_id']
        result = dict(reply.retval)

        TaskStatusManager.set_task_succeeded(task_id, result=result, timestamp=reply.timestamp)

        if action == 'bind':
            if result['succeeded']:
                ReplyHandler._bind_succeeded(task_id, call_context)
            else:
                ReplyHandler._bind_failed(task_id, call_context)
            return
        if action == 'unbind':
            if result['succeeded']:
                ReplyHandler._unbind_succeeded(call_context)
            else:
                ReplyHandler._unbind_failed(task_id, call_context)
            return

    def failed(self, reply):
        """
        Notification (reply) indicating an RMI failed.
        This information used to update the task status.
        :param reply: A failure reply object.
        :type reply: gofer.rmi.async.Failed
        """
        log.info(_('Task RMI (failed): %(r)s'), {'r': reply})

        call_context = dict(reply.data)
        action = call_context.get('action')
        task_id = call_context['task_id']
        traceback = reply.xstate['trace']

        TaskStatusManager.set_task_failed(task_id, traceback=traceback, timestamp=reply.timestamp)

        if action == 'bind':
            ReplyHandler._bind_failed(task_id, call_context)
            return
        if action == 'unbind':
            ReplyHandler._unbind_failed(task_id, call_context)
            return

    def progress(self, reply):
        """
        Notification (reply) indicating an RMI has reported status.
        This information is relayed to the task coordinator.
        :param reply: A progress reply object.
        :type reply: gofer.rmi.async.Progress
        """
        call_context = dict(reply.data)
        task_id = call_context['task_id']
        delta = {'progress_report': reply.details}
        TaskStatusManager.update_task_status(task_id, delta)
