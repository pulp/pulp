# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from logging import getLogger

from pulp.server.config import config
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.managers import factory as managers
from gofer.messaging.broker import Broker
from gofer.messaging import Queue
from gofer.rmi.async import ReplyConsumer, Listener
from gofer.rmi.async import WatchDog, Journal


log = getLogger(__name__)


class Services:
    """
    Agent services.
    :cvar REPLY_QUEUE: The agent RMI reply queue.
    :type REPLY_QUEUE: str
    :cvar watchdog: Asynchronous RMI watchdog.
    :type watchdog: WatchDog
    :cvar reply_handler: Asynchronous RMI reply listener.
    :type reply_handler: ReplyHandler
    :cvar heartbeat_listener: Agent heartbeat listener.
    :type heartbeat_listener: HeartbeatListener
    """

    watchdog = None
    reply_handler = None
    heartbeat_listener = None

    REPLY_QUEUE = 'pulp.task'

    @staticmethod
    def init():
        url = config.get('messaging', 'url')
        broker = Broker(url)
        broker.cacert = config.get('messaging', 'cacert')
        broker.clientcert = config.get('messaging', 'clientcert')
        log.info('AMQP broker configured: %s', broker)

    @classmethod
    def start(cls):
        url = config.get('messaging', 'url')
        # watchdog
        journal = Journal('/var/lib/pulp/journal/watchdog')
        cls.watchdog = WatchDog(url=url, journal=journal)
        cls.watchdog.start()
        log.info('AMQP watchdog started')
        # asynchronous reply
        cls.reply_handler = ReplyHandler(url)
        cls.reply_handler.start(cls.watchdog)
        log.info('AMQP reply handler started')


class ReplyHandler(Listener):
    """
    The async RMI reply handler.
    :ivar consumer: The reply consumer.
    :type consumer: ReplyConsumer
    """

    # --- action post-processing ---------------------------------------------

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
        queue = Queue(Services.REPLY_QUEUE)
        self.consumer = ReplyConsumer(queue, url=url)

    # --- agent replies ------------------------------------------------------

    def start(self, watchdog):
        """
        Start the reply handler (thread)
        :param watchdog: A watchdog object used to synthesize timeouts.
        :type watchdog: Watchdog
        """
        self.consumer.start(self, watchdog=watchdog)
        log.info('Task reply handler, started.')

    def started(self, reply):
        """
        Notification that an RMI has started executing in the agent.
        The task status is updated in the pulp DB.
        :param reply: A status reply object.
        :type reply: gofer.rmi.async.Started
        """
        call_context = reply.any
        task_id = call_context['task_id']
        TaskStatusManager.set_task_started(task_id)

    def succeeded(self, reply):
        """
        Notification (reply) indicating an RMI succeeded.
        This information is relayed to the task coordinator.
        :param reply: A successful reply object.
        :type reply: gofer.rmi.async.Succeeded
        """
        log.info('Task RMI (succeeded)\n%s', reply)

        call_context = dict(reply.any)
        action = call_context.get('action')
        task_id = call_context['task_id']
        result = dict(reply.retval)

        TaskStatusManager.set_task_succeeded(task_id, result)

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
        log.info('Task RMI (failed)\n%s', reply)

        call_context = dict(reply.any)
        action = call_context.get('action')
        task_id = call_context['task_id']
        traceback = reply.xstate['trace']

        TaskStatusManager.set_task_failed(task_id, traceback)

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
        call_context = dict(reply.any)
        task_id = call_context['task_id']
        delta = {'progress_report': reply.details}
        TaskStatusManager.update_task_status(task_id, delta)
