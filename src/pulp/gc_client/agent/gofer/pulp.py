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
from gofer.decorators import *
from gofer.agent.plugin import Plugin
from gofer.messaging import Topic
from gofer.messaging.producer import Producer
from gofer.pmon import PathMonitor
from pulp.gc_client.agent.lib.dispatcher import Dispatcher
from pulp.gc_client.agent.bindings import PulpBindings
from pulp.common.bundle import Bundle as BundleImpl
from logging import getLogger

log = getLogger(__name__)
plugin = Plugin.find(__name__)
dispatcher = Dispatcher()
cfg = plugin.cfg()

#
# Utils
#

def secret():
    """
    Get the shared secret used for auth of RMI requests.
    @return: The sha256 for the certificate
    @rtype: str
    """
    bundle = Bundle()
    content = bundle.read()
    crt = bundle.split(content)[1]
    if content:
        hash = sha256()
        hash.update(crt)
        return hash.hexdigest()
    else:
        return None


class Bundle(BundleImpl):
    """
    Consumer certificate (bundle)
    """

    def __init__(self):
        BundleImpl.__init__(self, cfg.messaging.clientcert)

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

    @action(seconds=cfg.heartbeat.seconds)
    def heartbeat(self):
        return self.send()

    @remote
    def send(self):
        topic = Topic('heartbeat')
        delay = int(cfg.heartbeat.seconds)
        bundle = Bundle()
        myid = bundle.cn()
        if myid:
            p = self.producer()
            body = dict(uuid=myid, next=delay)
            p.send(topic, ttl=delay, heartbeat=body)
        return myid


class RegistrationMonitor:

    pmon = PathMonitor()

    @classmethod
    @action(days=0x8E94)
    def init(cls):
        """
        Start path monitor to track changes in the
        pulp identity certificate.
        """
        path = '/etc/pki/pulp/consumer/cert.pem'
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
        bundle = Bundle()
        myid = bundle.cn()
        plugin.setuuid(myid)

#
# API
#

class Consumer:
    """
    Consumer Management.
    """

    @remote(secret=secret)
    def unregistered(self):
        bundle = Bundle()
        bundle.delete()
        report = dispatcher.clean()
        return report.dict()

    @remote(secret=secret)
    def bind(self, repoid):
        bindings = PulpBindings()
        bundle = Bundle()
        myid = bundle.cn()
        http = bindings.bind.find_by_id(myid, repoid)
        if http.response_code == 200:
            report = dispatcher.bind(http.response_body)
            return report.dict()
        else:
            raise Exception('rebind failed, http:%d', http.response_code)

    @remote(secret=secret)
    @action(days=0x8E94)
    def rebind(self):
        bindings = PulpBindings()
        bundle = Bundle()
        myid = bundle.cn()
        http = bindings.bind.find_by_id(myid)
        if http.response_code == 200:
            report = dispatcher.rebind(http.response_body)
            return report.dict()
        else:
            raise Exception('rebind failed, http:%d', http.response_code)

    @remote(secret=secret)
    def unbind(self, repoid):
        report = dispatcher.unbind(repoid)
        return report.dict()


class Content:
    """
    Content Management.
    """

    @remote(secret=secret)
    def install(self, units, options):
        report = dispatcher.install(units, options)
        return report.dict()

    @remote(secret=secret)
    def update(self, units, options):
        report = dispatcher.update(units, options)
        return report.dict()

    @remote(secret=secret)
    def uninstall(self, units, options):
        report = dispatcher.uninstall(units, options)
        return report.dict()


class Profile:
    """
    Profile Management
    """

    @remote(secret=secret)
    @action(minutes=cfg.profile.minutes)
    def send(self):
        report = dispatcher.profile()
        # TODO: send profiles
        log.info('profile: %s' % report)
        return report.dict()
