#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

"""
Pulp (gofer) plugin.
Contains recurring actions and remote classes.
"""

import os
from hashlib import sha256
from pulp.client.consumer.credentials import Consumer as ConsumerBundle
from pulp.client.agent.dispatcher import Dispatcher
from gofer.agent.plugin import Plugin
from gofer.messaging import Topic
from gofer.messaging.producer import Producer
from gofer.pmon import PathMonitor
from gofer.decorators import *

from logging import getLogger

log = getLogger(__name__)
plugin = Plugin.find(__name__)
cfg = plugin.cfg()

HEARTBEAT = cfg.heartbeat.seconds


def secret():
    """
    Get the shared secret used for auth of RMI requests.
    @return: The sha256 for the certificate
    @rtype: str
    """
    bundle = ConsumerBundle()
    content = bundle.read()
    crt = bundle.split(content)[1]
    if content:
        hash = sha256()
        hash.update(crt)
        return hash.hexdigest()
    else:
        return None

#
# Actions
#

class Heartbeat:
    """
    Provide agent heartbeat.
    """

    __producer = None

    @classmethod
    def producer(cls):
        if not cls.__producer:
            broker = plugin.getbroker()
            url = str(broker.url)
            cls.__producer = Producer(url=url)
        return cls.__producer

    #@action(seconds=HEARTBEAT)
    def heartbeat(self):
        return self.send()

    @remote
    def send(self):
        topic = Topic('heartbeat')
        delay = int(HEARTBEAT)
        bundle = ConsumerBundle()
        myid = bundle.getid()
        if myid:
            p = self.producer()
            body = dict(uuid=myid, next=delay)
            p.send(topic, ttl=delay, heartbeat=body)
        return myid


class RegistrationMonitor:

    pmon = PathMonitor()

    @classmethod
    #@action(days=0x8E94)
    def init(cls):
        """
        Start path monitor to track changes in the
        pulp identity certificate.
        """
        bundle = ConsumerBundle()
        path = bundle.crtpath()
        cls.pmon.add(path, cls.changed)
        cls.pmon.start()

    @classmethod
    def changed(cls, path):
        """
        A change in the pulp certificate has been detected.
        When deleted: disconnect from qpid.
        When added/updated: reconnect to qpid.
        @param path: The changed file (ignored).
        @type path: str
        """
        log.info('changed: %s', path)
        bundle = ConsumerBundle()
        plugin.setuuid(bundle.getid())

#
# API
#

class ConsumerXXX: # Temporary v1 compat.
    """
    Consumer Management.
    """

    @remote(secret=secret)
    def unregistered(self):
        pass

    @remote(secret=secret)
    def bind(self, repo_id):
        pass

    @remote(secret=secret)
    @action(days=0x8E94)
    def rebind(self):
        pass

    @remote(secret=secret)
    def unbind(self, repo_id):
        pass


class Content:
    """
    Content Management.
    """

    @remote(secret=secret)
    def install(self, units, options):
        dispatcher = Dispatcher()
        report = dispatcher.install(units, options)
        return report.dict()

    @remote(secret=secret)
    def update(self, units, options):
        dispatcher = Dispatcher()
        report = dispatcher.update(units, options)
        return report.dict()

    @remote(secret=secret)
    def uninstall(self, units, options):
        dispatcher = Dispatcher()
        report = dispatcher.uninstall(units, options)
        return report.dict()

class Profile:

    @remote(secret=secret)
    def send(self):
        pass
