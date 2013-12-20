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


from threading import RLock
from datetime import datetime as dt
from datetime import timedelta
from logging import getLogger

from pulp.common import dateutils
from pulp.server.config import config
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.managers import factory as managers
from gofer.messaging.broker import Broker
from gofer.messaging import Topic
from gofer.messaging.consumer import Consumer
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
        # heartbeat
        cls.heartbeat_listener = HeartbeatListener(url)
        cls.heartbeat_listener.start()
        log.info('AMQP heartbeat listener started')
        # asynchronous reply
        cls.reply_handler = ReplyHandler(url)
        cls.reply_handler.start(cls.watchdog)
        log.info('AMQP reply handler started')


class HeartbeatListener(Consumer):
    """
    Agent heartbeat listener.
    """

    __status = {}
    __mutex = RLock()

    @classmethod
    def status(cls, uuids=[]):
        """
        Get the agent heartbeat status.
        :param uuids: An (optional) list of uuids to query.
        :return: A tuple (status,last-heartbeat)
        """
        cls.__lock()
        try:
            now = dt.now(dateutils.utc_tz())
            if not uuids:
                uuids = cls.__status.keys()
            d = {}
            for uuid in uuids:
                last = cls.__status.get(uuid)
                if last:
                    status = ( last[1] > now )
                    heartbeat = last[0].isoformat()
                    any = last[2]
                else:
                    status = False
                    heartbeat = None
                    any = {}
                d[uuid] = (status, heartbeat, any)
            return d
        finally:
            cls.__unlock()

    @classmethod
    def __lock(cls):
        cls.__mutex.acquire()

    @classmethod
    def __unlock(cls):
        cls.__mutex.release()

    def __init__(self, url):
        topic = Topic('heartbeat')
        Consumer.__init__(self, topic, url=url)

    def dispatch(self, envelope):
        try:
            self.__update(envelope.heartbeat)
        except:
            log.error(envelope, exec_info=True)
        self.ack()

    def __update(self, body):
        self.__lock()
        try:
            log.debug(body)
            uuid = body.pop('uuid')
            next = body.pop('next')
            last = dt.now(dateutils.utc_tz())
            next = int(next*1.20)
            next = last+timedelta(seconds=next)
            self.__status[uuid] = (last, next, body)
        finally:
            self.__unlock()


class ReplyHandler(Listener):
    """
    The async RMI reply handler.
    :ivar consumer: The reply consumer.
    :type consumer: ReplyConsumer
    """

    @staticmethod
    def _update_bind_action(action_id, call_context, succeeded):
        """
        Update the bind action.
        :param action_id: The action ID (basically the task_id).
        :type action_id: str
        :param call_context: The information about the bind call that was
            passed to the agent to be round tripped back here.
        :param succeeded: The bind action status.
        :type succeeded: bool
        """
        manager = managers.consumer_bind_manager()
        consumer_id = call_context['consumer_id']
        repo_id = call_context['repo_id']
        distributor_id = call_context['distributor_id']
        if succeeded:
            manager.action_succeeded(consumer_id, repo_id, distributor_id, action_id)
        else:
            manager.action_failed(consumer_id, repo_id, distributor_id, action_id)

    def __init__(self, url):
        queue = Queue(Services.REPLY_QUEUE)
        self.consumer = ReplyConsumer(queue, url=url)

    def start(self, watchdog):
        """
        Start the reply handler (thread)
        :param watchdog: A watchdog object used to synthesize timeouts.
        :type watchdog: Watchdog
        """
        self.consumer.start(self, watchdog=watchdog)
        log.info('Task reply handler, started.')

    def started(self, status):
        """
        Notification that an RMI has started executing in the agent.
        The task status is updated in the pulp DB.
        :param status: A RMi status object.
        :type status: gofer.rmi.async.Started
        """
        call_context = status.any
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
        result = reply.retval
        call_context = reply.any
        task_id = call_context['task_id']
        TaskStatusManager.set_task_succeeded(task_id, result)
        action = call_context.get('action')
        if action in ('bind', 'unbind'):
            ReplyHandler._update_bind_action(task_id, call_context, result['succeeded'])

    def failed(self, reply):
        """
        Notification (reply) indicating an RMI failed.
        This information used to update the task status.
        :param reply: A failure reply object.
        :type reply: gofer.rmi.async.Failed
        """
        log.info('Task RMI (failed)\n%s', reply)
        traceback = reply.xstate['trace']
        call_context = reply.any
        task_id = call_context['task_id']
        TaskStatusManager.set_task_failed(task_id, traceback)
        action = call_context.get('action')
        if action in ('bind', 'unbind'):
            ReplyHandler._update_bind_action(task_id, call_context, False)

    def progress(self, reply):
        """
        Notification (reply) indicating an RMI has reported status.
        This information is relayed to the task coordinator.
        :param reply: A progress reply object.
        :type reply: gofer.rmi.async.Progress
        """
        # TODO: not supported by TaskStats yet.