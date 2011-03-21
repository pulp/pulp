#! /usr/bin/env python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

"""
Contains (proxy) classes that represent the pulp agent.
The proxy classes must match the names of classes that are exposed
on the agent.
"""

from threading import RLock
from datetime import datetime as dt
from datetime import timedelta
from gofer.proxy import Agent as Base
from gofer.messaging import Topic
from gofer.messaging.consumer import Consumer
from gofer.messaging.producer import Producer
from pulp.server.config import config
from logging import getLogger


log = getLogger(__name__)


def retrieve_agent(uuid, **options):
    '''
    Factory method for getting Agent instances. This method can be monkey patched
    in unit tests to return a mock agent suitable for testing.

    @param uuid: uuid of the consumer
    @type  uuid: string

    @param options: options to the underlying message bus
    @type  options: dict
    '''
    return Agent(uuid, **options)

def retrieve_repo_proxy(uuid, **options):
    '''
    Utility factory method for retrieving the repo proxy to a consumer.

    @param uuid: uuid of the consumer
    @type  uuid: string

    @param options: options to the underlying message bus
    @type  options: dict
    '''
    agent = retrieve_agent(uuid, **options)
    return agent.Repo()


class Agent(Base):
    """
    A server-side proxy for the pulp agent.
    """

    @classmethod
    def status(self, uuids=[]):
        return HeartbeatListener.status(uuids)

    def __init__(self, uuid, **options):
        """
        @param uuid: The consumer uuid.
        @type uuid: str|list
        @param options: Messaging L{gofer.messaging.Options}
        """
        url = config.get('messaging', 'url')
        producer = Producer(url=url)
        Base.__init__(self, uuid, producer, **options)


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
            now = dt.utcnow()
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

    def __init__(self):
        topic = Topic('heartbeat')
        Consumer.__init__(self, topic)

    def dispatch(self, envelope):
        try:
            self.__update(envelope.heartbeat)
        except:
            log.error(envelope, exec_info=True)
        self.ack()

    def __update(self, body):
        self.__lock()
        try:
            uuid = body.pop('uuid')
            next = body.pop('next')
            last = dt.utcnow()
            next = int(next*1.20)
            next = last+timedelta(seconds=next)
            self.__status[uuid] = (last, next, body)
        finally:
            self.__unlock()
