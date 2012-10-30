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
from logging import getLogger

from gofer.decorators import *
from gofer.agent.plugin import Plugin
from gofer.messaging import Topic
from gofer.messaging.producer import Producer
from gofer.pmon import PathMonitor
from gofer.agent.rmi import Context

from pulp.common.bundle import Bundle as BundleImpl
from pulp.common.config import Config
from pulp.agent.lib.dispatcher import Dispatcher
from pulp.agent.lib.conduit import Conduit as HandlerConduit
from pulp.bindings.server import PulpConnection
from pulp.bindings.bindings import Bindings


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


class Conduit(HandlerConduit):
    """
    Provides integration between the gofer progress reporting
    and agent handler frameworks.
    """

    def get_consumer_config(self):
        """
        Get the consumer configuration.
        @return: The consumer configuration object.
        @rtype: L{pulp.common.config.Config}
        """
        paths = ['/etc/pulp/consumer/consumer.conf']
        overrides = os.path.expanduser('~/.pulp/consumer.conf')
        if os.path.exists(overrides):
            paths.append(overrides)
        cfg = Config(*paths)
        return cfg

    def update_progress(self, report):
        """
        Send the updated progress report.
        @param report: A handler progress report.
        @type report: object
        """
        context = Context.current()
        context.progress.details = report
        context.progress.report()

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
        conduit = Conduit()
        report = dispatcher.clean(conduit)
        return report.dict()

    @remote(secret=secret)
    def bind(self, definitions, options):
        """
        Bind to the specified repository ID.
        Delegated to content handlers.
        @param definitions: A list of bind definitions.
        Each definition is:
            {type_id:<str>, repository:<repository>, details:<dict>}
              The <repository> is a pulp repository object.
              The content of <details> is at the discretion of the distributor.
        @type definitions: list
        @param options: Bind options.
        @type options: dict
        @return: A dispatch report.
        @rtype: DispatchReport
        """
        conduit = Conduit()
        report = dispatcher.bind(conduit, definitions, options)
        return report.dict()

    @remote(secret=secret)
    def unbind(self, repo_id, options):
        """
        Unbind to the specified repository ID.
        Delegated to content handlers.
        @param repo_id: A repository ID.
        @type repo_id: str
        @param options: Unbind options.
        @type options: dict
        @return: A dispatch report.
        @rtype: DispatchReport
        """
        conduit = Conduit()
        report = dispatcher.unbind(conduit, repo_id, options)
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
        conduit = Conduit()
        report = dispatcher.install(conduit, units, options)
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
        conduit = Conduit()
        report = dispatcher.update(conduit, units, options)
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
        conduit = Conduit()
        report = dispatcher.uninstall(conduit, units, options)
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
        conduit = Conduit()
        bindings = PulpBindings()
        report = dispatcher.profile(conduit)
        log.info('profile: %s' % report)
        for typeid, profile_report in report.details.items():
            if not profile_report['status']:
                continue
            details = profile_report['details']
            http = bindings.profile.send(myid, typeid, details)
            log.debug('profile (%s), reported: %d', typeid, http.response_code)
        return report.dict()
