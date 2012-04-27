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
from pulp.common import dateutils
from pulp.server.config import config
from pulp.server.dispatch import factory
from gofer.messaging.broker import Broker
from gofer.messaging import Topic
from gofer.messaging.consumer import Consumer
from gofer.messaging import Queue
from gofer.rmi.async import ReplyConsumer, Listener
from gofer.rmi.async import WatchDog
from logging import getLogger


log = getLogger(__name__)


class Services:
    """
    Agent services.
    @cvar CTAG: The RMI correlation.
    @type CTAG: str
    @cvar watchdog: Asynchronous RMI watchdog.
    @type watchdog: L{WatchDog}
    @cvar reply_handler: Asynchornous RMI reply listener.
    @type reply_handler: L{ReplyHandler}
    @cvar heartbeat_listener: Agent heartbeat listener.
    @type heartbeat_listener: L{HeartbeatListener}
    """

    watchdog = None
    reply_handler = None
    heartbeat_listener = None

    CTAG = 'pulp.task'

    @classmethod
    def start(cls):
        url = config.get('messaging', 'url')
        log.info('Using URL: %s', url)
        # broker configuration
        broker = Broker(url)
        broker.cacert = config.get('messaging', 'cacert')
        broker.clientcert = config.get('messaging', 'clientcert')
        log.info('AMQP broker configured')
        # watchdog
        cls.watchdog = WatchDog(url=url)
        cls.watchdog.journal('/var/lib/pulp/journal/watchdog')
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
        @param uuids: An (optional) list of uuids to query.
        @return: A tuple (status,last-heartbeat)
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
    @ivar consumer: The reply consumer.
    @type consumer: L{ReplyConsumer}
    """

    def __init__(self, url):
        queue = Queue(Services.CTAG)
        self.consumer = ReplyConsumer(queue, url=url)

    def start(self, watchdog):
        self.consumer.start(self, watchdog=watchdog)
        log.info('Task reply handler, started.')

    def succeeded(self, reply):
        log.info('Task RMI (succeeded)\n%s', reply)
        taskid = reply.any
        result = reply.retval
        coordinator = factory.coordinator()
        coordinator.complete_call_success(taskid, result)

    def failed(self, reply):
        log.info('Task RMI (failed)\n%s', reply)
        taskid = reply.any
        exception = reply.exval
        traceback = reply.xstate['trace']
        coordinator = factory.coordinator()
        coordinator.complete_call_failure(taskid, exception, traceback)

    def status(self, reply):
        pass
