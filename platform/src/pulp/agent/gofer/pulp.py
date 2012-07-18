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

from hashlib import sha256
from gofer.decorators import *
from gofer.agent.plugin import Plugin
from gofer.messaging import Topic
from gofer.messaging.producer import Producer
from gofer.pmon import PathMonitor
from pulp.common.bundle import Bundle as BundleImpl
from pulp.agent.lib.dispatcher import Dispatcher
from pulp.bindings.server import PulpConnection
from pulp.bindings.bindings import Bindings
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
        BundleImpl.__init__(self, cfg.rest.clientcert)
        

class PulpBindings(Bindings):
    """
    Pulp (REST) API.
    """
    
    def __init__(self):
        host = cfg.rest.host
        port = int(cfg.rest.port)
        cert = cfg.rest.clientcert
        connection = PulpConnection(host, port, cert_filename=cert)
        Bindings.__init__(self, connection)

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
        """
        Get the cached producer.
        @return: A producer.
        @rtype: L{Producer}
        """
        if not cls.__producer:
            broker = plugin.getbroker()
            url = str(broker.url)
            cls.__producer = Producer(url=url)
        return cls.__producer

    @remote
    @action(seconds=cfg.heartbeat.seconds)
    def send(self):
        """
        Send the heartbeat.
        The delay defines when the next heartbeat
        should be expected.
        """
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
    """
    Monitor the registration (consumer) certificate for changes.
    When a change is detected, the bus attachement is changed
    as appropriate.  When removed, we set our UUID to None which
    will cause us to detach.  When changed, our UUID is changed
    which causes a detach/attach to be sure we are attached with
    the correct UUID.
    @cvar pmon: A path monitor object.
    @type pmon: L{PathMonitor}
    """

    pmon = PathMonitor()

    @classmethod
    @action(days=0x8E94)
    def init(cls):
        """
        Start path monitor to track changes in the
        pulp identity certificate.
        """
        path = cfg.rest.clientcert
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


class Synchronization:
    """
    Misc actions used to synchronize with the server.
    """

    @action(days=0x8E94)
    def rebind(self):
        """
        (Re)bind on agent statup.
        """
        if self.registered():
            consumer = Consumer()
            consumer.rebind()
        else:
            log.info('not registered, rebind skipped')
            
    @action(minutes=cfg.profile.minutes)
    def profile(self):
        """
        Report the unit profile(s).
        """
        if self.registered():
            profile = Profile()
            profile.send()
        else:
            log.info('not registered, profile report skipped')
            
    def registered(self):
        """
        Get registration status.
        """
        bundle = Bundle()
        myid = bundle.cn()
        return (myid is not None)

#
# API
#

class Consumer:
    """
    Consumer Management.
    """

    @remote(secret=secret)
    def unregistered(self):
        """
        Notification that the consumer had been unregistered.
        The action is to clean up registration and bind artifacts.
        The consumer bundle is deleted.  Then, all handlers
        are requested to perform a clean().
        """
        bundle = Bundle()
        bundle.delete()
        report = dispatcher.clean()
        return report.dict()

    @remote(secret=secret)
    def bind(self, repoid):
        """
        Bind to the specified repository ID.
        Delegated to content handlers.
        @param repoid: A repository ID.
        @type repoid: str
        @return: A dispatch report.
        @rtype: DispatchReport
        """
        bindings = PulpBindings()
        bundle = Bundle()
        myid = bundle.cn()
        http = bindings.bind.find_by_id(myid, repoid)
        if http.response_code == 200:
            report = dispatcher.bind(http.response_body)
            return report.dict()
        else:
            raise Exception('bind failed, http:%d', http.response_code)

    @remote(secret=secret)
    def rebind(self):
        """
        (Re)bind to all repositories.
        Runs at plugin initialization and delegated to content handlers.
        @return: A dispatch report.
        @rtype: DispatchReport
        """
        bindings = PulpBindings()
        bundle = Bundle()
        myid = bundle.cn()
        bindings = PulpBindings()
        http = bindings.bind.find_by_id(myid)
        if http.response_code == 200:
            report = dispatcher.rebind(http.response_body)
            return report.dict()
        else:
            raise Exception('rebind failed, http:%d', http.response_code)

    @remote(secret=secret)
    def unbind(self, repoid):
        """
        Unbind to the specified repository ID.
        Delegated to content handlers.
        @param repoid: A repository ID.
        @type repoid: str
        @return: A dispatch report.
        @rtype: DispatchReport
        """
        report = dispatcher.unbind(repoid)
        return report.dict()


class Content:
    """
    Content Management.
    """

    @remote(secret=secret)
    def install(self, units, options):
        """
        Install the specified content units using the specified options.
        Delegated to content handlers.
        @param units: A list of content units to be installed.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Install options; based on unit type.
        @type options: dict
        @return: A dispatch report.
        @rtype: DispatchReport
        """
        report = dispatcher.install(units, options)
        return report.dict()

    @remote(secret=secret)
    def update(self, units, options):
        """
        Update the specified content units using the specified options.
        Delegated to content handlers.
        @param units: A list of content units to be updated.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Update options; based on unit type.
        @type options: dict
        @return: A dispatch report.
        @rtype: DispatchReport
        """
        report = dispatcher.update(units, options)
        return report.dict()

    @remote(secret=secret)
    def uninstall(self, units, options):
        """
        Uninstall the specified content units using the specified options.
        Delegated to content handlers.
        @param units: A list of content units to be uninstalled.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Uninstall options; based on unit type.
        @type options: dict
        @return: A dispatch report.
        @rtype: DispatchReport
        """
        report = dispatcher.uninstall(units, options)
        return report.dict()


class Profile:
    """
    Profile Management
    """

    @remote(secret=secret)
    def send(self):
        """
        Send the content profile(s) to the server.
        Delegated to the handlers.
        @return: A dispatch report.
        @rtype: DispatchReport
        """
        bundle = Bundle()
        myid = bundle.cn()
        bindings = PulpBindings()
        report = dispatcher.profile()
        log.info('profile: %s' % report)
        for typeid, report in report.details.items():
            if not report['status']:
                continue
            details = report['details']
            http = bindings.profile.send(myid, typeid, details)
            log.info('profile (%s), reported: %d', typeid, http.response_code)
        return report
