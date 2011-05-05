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
from gofer import proxy
from gofer.messaging import Topic
from gofer.messaging.consumer import Consumer
from pulp.common import dateutils
from pulp.server.config import config
from logging import getLogger


log = getLogger(__name__)


def Agent(uuid, **options):
    """
    Factory method for getting a pulp agent object.
    @param uuid: The agent UUID.
    @type uuid: str
    @return: A proxy object for the remote agent.
    """
    return proxy.agent(uuid, **options)

def status(uuids=[]):
    """
    Get the agent heartbeat status.
    @param uuids: An (optional) list of uuids to query.
    @return: A tuple (status,last-heartbeat)
    """
    return HeartbeatListener.status(uuids)


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
            log.debug(body)
            uuid = body.pop('uuid')
            next = body.pop('next')
            last = dt.now(dateutils.utc_tz())
            next = int(next*1.20)
            next = last+timedelta(seconds=next)
            self.__status[uuid] = (last, next, body)
        finally:
            self.__unlock()
