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

from logging import getLogger

from M2Crypto import RSA, BIO
from M2Crypto.X509 import X509Error

from gofer.decorators import *
from gofer.agent.plugin import Plugin
from gofer.pmon import PathMonitor
from gofer.agent.rmi import Context
from gofer.messaging.auth import ValidationFailed

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


class Authenticator(object):
    """
    Provides message authentication using RSA keys.
    The server and the agent sign sent messages using their private keys
    and validate received messages using each others public keys.
    :ivar rsa_key: The private RSA key used for signing.
    :type rsa_key: RSA.RSA
    :ivar rsa_pub: The public RSA key used for validation.
    :type rsa_pub: RSA.RSA
    """

    def __init__(self):
        self.rsa_key = None
        self.rsa_pub = None

    def load(self):
        """
        Load both private and public RSA keys.
        """
        fp = open(cfg.authentication.rsa_key)
        try:
            pem = fp.read()
            bfr = BIO.MemoryBuffer(pem)
            self.rsa_key = RSA.load_key_bio(bfr)
        finally:
            fp.close()
        fp = open(cfg.server.rsa_pub)
        try:
            pem = fp.read()
            bfr = BIO.MemoryBuffer(pem)
            self.rsa_pub = RSA.load_pub_key_bio(bfr)
        finally:
            fp.close()

    def sign(self, digest):
        """
        Sign the specified message.
        :param digest: An AMQP message digest.
        :type digest: str
        :return: The message signature.
        :rtype: str
        """
        return self.rsa_key.sign(digest)

    def validate(self, uuid, digest, signature):
        """
        Validate the specified message and signature.
        :param uuid: The (unused) uuid of the sender.
        :type uuid: str
        :param digest: An AMQP message digest.
        :type digest: str
        :param signature: A message signature.
        :type signature: str
        :raises ValidationFailed: when message is not valid.
        """
        try:
            if not self.rsa_pub.verify(digest, signature):
                raise ValidationFailed()
        except RSA.RSAError:
            raise ValidationFailed()


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
        except (KeyError, X509Error):
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
            authenticator = Authenticator()
            authenticator.load()
            plugin_conf = plugin.cfg()
            plugin_conf.messaging.url = url
            plugin_conf.messaging.uuid = consumer_id
            plugin_conf.messaging.cacert = cfg.messaging.cacert
            plugin_conf.messaging.clientcert = cfg.messaging.clientcert or \
                os.path.join(cfg.filesystem.id_cert_dir, cfg.filesystem.id_cert_filename)
            plugin_conf.messaging.transport = cfg.messaging.transport
            plugin.authenticator = authenticator
            plugin.attach()
        else:
            plugin.detach()


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

    @remote
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

    @remote
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

    @remote
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

    @remote
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

    @remote
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

    @remote
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

    @remote
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
