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
import errno

from hashlib import sha256
from logging import getLogger

from M2Crypto.X509 import X509Error

from gofer.decorators import *
from gofer.agent.plugin import Plugin
from gofer.pmon import PathMonitor
from gofer.agent.rmi import Context

from pulp.common.bundle import Bundle
from pulp.agent.lib.dispatcher import Dispatcher
from pulp.agent.lib.conduit import Conduit as HandlerConduit
from pulp.bindings.server import PulpConnection
from pulp.bindings.bindings import Bindings
from pulp.client.consumer.config import read_config

log = getLogger(__name__)

# pulp consumer configuration
# the graph (cfg) is provided for syntactic convenience

pulp_conf = read_config()
cfg = pulp_conf.graph()


# --- utils ------------------------------------------------------------------


def secret():
    """
    Get the shared secret used for auth of RMI requests.
    :return: The sha256 for the certificate
    :rtype: str
    """
    try:
        bundle = ConsumerX509Bundle()
        content = bundle.read()
        certificate = bundle.split(content)[1]
        h = sha256()
        h.update(certificate)
        return h.hexdigest()
    except IOError, e:
        if e.errno != errno.ENOENT:
            raise
    except Exception:
        log.exception('generate shared secret failed')


class ConsumerX509Bundle(Bundle):
    """
    Consumer certificate (bundle)
    """

    def __init__(self):
        path = os.path.join(cfg.filesystem.id_cert_dir, cfg.filesystem.id_cert_filename)
        Bundle.__init__(self, path)

    def cn(self):
        """
        Get the common name (CN) part of the certificate subject.
        Returns None, if the certificate is invalid.
        :return The common name (CN) part of the certificate subject or None when
            the certificate is not found or invalid.
        :rtype: str
        """
        try:
            return Bundle.cn(self)
        except X509Error:
            log.warn('certificate: %s, not valid', self.path)


class PulpBindings(Bindings):
    """
    Pulp (REST) API.
    """
    
    def __init__(self):
        host = cfg.server.host
        port = int(cfg.server.port)
        cert = os.path.join(cfg.filesystem.id_cert_dir, cfg.filesystem.id_cert_filename)
        connection = PulpConnection(host, port, cert_filename=cert)
        Bindings.__init__(self, connection)


class Conduit(HandlerConduit):
    """
    Provides integration between the gofer progress reporting
    and agent handler frameworks.
    """

    @property
    def consumer_id(self):
        """
        Get the current consumer ID
        :return: The unique consumer ID of the currently running agent
        :rtype:  str
        """
        bundle = ConsumerX509Bundle()
        return bundle.cn()

    def get_consumer_config(self):
        """
        Get the consumer configuration.
        :return: The consumer configuration object.
        :rtype: pulp.common.config.Config
        """
        return pulp_conf

    def update_progress(self, report):
        """
        Send the updated progress report.
        :param report: A handler progress report.
        :type report: object
        """
        context = Context.current()
        context.progress.details = report
        context.progress.report()

    def cancelled(self):
        """
        Get whether the current operation has been cancelled.
        :return: True if cancelled, else False.
        :rtype: bool
        """
        context = Context.current()
        return context.cancelled()


# --- actions ----------------------------------------------------------------


class RegistrationMonitor:
    """
    Monitor the registration (consumer) certificate for changes.
    When a change is detected, the bus attachment is changed
    as appropriate.  When removed, we set our UUID to None which
    will cause us to detach.  When changed, our UUID is changed
    which causes a detach/attach to be sure we are attached with
    the correct UUID.
    @cvar pmon: A path monitor object.
    :type pmon: PathMonitor
    """

    pmon = PathMonitor()

    @classmethod
    @action(days=0x8E94)
    def init(cls):
        """
        Start path monitor to track changes in the
        pulp identity certificate.
        """
        path = os.path.join(cfg.filesystem.id_cert_dir, cfg.filesystem.id_cert_filename)
        cls.pmon.add(path, cls.changed)
        cls.pmon.start()

    @classmethod
    def changed(cls, path):
        """
        A change in the pulp certificate has been detected.
        When the certificate has been deleted: the connection to the broker is
        terminated by setting the UUID to None.
        When the certificate has been added/updated: the plugin's configuration is
        updated using the pulp configuration; the uuid is updated and the connection
        to the broker is re-established.
        :param path: The changed file (ignored).
        :type path: str
        """
        log.info('changed: %s', path)
        plugin = Plugin.find(__name__)
        bundle = ConsumerX509Bundle()
        consumer_id = bundle.cn()
        if consumer_id:
            scheme = cfg.messaging.scheme
            host = cfg.messaging.host or cfg.server.host
            port = cfg.messaging.port
            url = '%s://%s:%s' % (scheme, host, port)
            plugin_conf = plugin.cfg()
            plugin_conf.messaging.url = url
            plugin_conf.messaging.cacert = cfg.messaging.cacert
            plugin_conf.messaging.clientcert = cfg.messaging.clientcert or \
                os.path.join(cfg.filesystem.id_cert_dir, cfg.filesystem.id_cert_filename)
        plugin.setuuid(consumer_id)


class Synchronization:
    """
    Misc actions used to synchronize with the server.
    """

    @staticmethod
    @action(minutes=cfg.profile.minutes)
    def profile():
        """
        Report the unit profile(s).
        """
        if Synchronization.registered():
            profile = Profile()
            profile.send()
        else:
            log.info('not registered, profile report skipped')

    @staticmethod
    def registered():
        """
        Get registration status.
        :return: True when a valid consumer ID can be obtained
            from the consumer certificate bundle.
        :rtype: bool
        """
        bundle = ConsumerX509Bundle()
        consumer_id = bundle.cn()
        return consumer_id is not None


# --- API --------------------------------------------------------------------


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
        bundle = ConsumerX509Bundle()
        bundle.delete()
        conduit = Conduit()
        dispatcher = Dispatcher()
        report = dispatcher.clean(conduit)
        return report.dict()

    @remote(secret=secret)
    def bind(self, bindings, options):
        """
        Bind to the specified repository ID.
        Delegated to content handlers.
        :param bindings: A list of bindings to add/update.
          Each binding is: {type_id:<str>, repo_id:<str>, details:<dict>}
            The 'details' are at the discretion of the distributor.
        :type bindings: list
        :param options: Bind options.
        :type options: dict
        :return: A dispatch report.
        :rtype: DispatchReport
        """
        conduit = Conduit()
        dispatcher = Dispatcher()
        report = dispatcher.bind(conduit, bindings, options)
        return report.dict()

    @remote(secret=secret)
    def unbind(self, bindings, options):
        """
        Unbind to the specified repository ID.
        Delegated to content handlers.
        :param bindings: A list of bindings to be removed.
          Each binding is: {type_id:<str>, repo_id:<str>}
        :type bindings: list
        :param options: Unbind options.
        :type options: dict
        :return: A dispatch report.
        :rtype: DispatchReport
        """
        conduit = Conduit()
        dispatcher = Dispatcher()
        report = dispatcher.unbind(conduit, bindings, options)
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
        :param units: A list of content units to be installed.
        :type units: list of:
            { type_id:<str>, unit_key:<dict> }
        :param options: Install options; based on unit type.
        :type options: dict
        :return: A dispatch report.
        :rtype: DispatchReport
        """
        conduit = Conduit()
        dispatcher = Dispatcher()
        report = dispatcher.install(conduit, units, options)
        return report.dict()

    @remote(secret=secret)
    def update(self, units, options):
        """
        Update the specified content units using the specified options.
        Delegated to content handlers.
        :param units: A list of content units to be updated.
        :type units: list of:
            { type_id:<str>, unit_key:<dict> }
        :param options: Update options; based on unit type.
        :type options: dict
        :return: A dispatch report.
        :rtype: DispatchReport
        """
        conduit = Conduit()
        dispatcher = Dispatcher()
        report = dispatcher.update(conduit, units, options)
        return report.dict()

    @remote(secret=secret)
    def uninstall(self, units, options):
        """
        Uninstall the specified content units using the specified options.
        Delegated to content handlers.
        :param units: A list of content units to be uninstalled.
        :type units: list of:
            { type_id:<str>, unit_key:<dict> }
        :param options: Uninstall options; based on unit type.
        :type options: dict
        :return: A dispatch report.
        :rtype: DispatchReport
        """
        conduit = Conduit()
        dispatcher = Dispatcher()
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
        :return: A dispatch report.
        :rtype: DispatchReport
        """
        bundle = ConsumerX509Bundle()
        consumer_id = bundle.cn()
        conduit = Conduit()
        bindings = PulpBindings()
        dispatcher = Dispatcher()
        report = dispatcher.profile(conduit)
        log.info('profile: %s' % report)
        for type_id, profile_report in report.details.items():
            if not profile_report['succeeded']:
                continue
            details = profile_report['details']
            http = bindings.profile.send(consumer_id, type_id, details)
            log.debug('profile (%s), reported: %d', type_id, http.response_code)
        return report.dict()
