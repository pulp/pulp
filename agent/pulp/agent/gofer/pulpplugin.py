"""
Pulp (gofer) plugin.
Contains recurring actions and remote classes.
"""

import os

from time import sleep
from gettext import gettext as _
from logging import getLogger

from M2Crypto import RSA, BIO
from M2Crypto.X509 import X509Error

from gofer.decorators import initializer, remote, action
from gofer.agent.plugin import Plugin
from gofer.pmon import PathMonitor
from gofer.agent.rmi import Context
from gofer.messaging.auth import ValidationFailed

from pulp.common.bundle import Bundle
from pulp.common.config import parse_bool
from pulp.agent.lib.dispatcher import Dispatcher
from pulp.agent.lib.conduit import Conduit as HandlerConduit
from pulp.bindings.server import PulpConnection
from pulp.bindings.bindings import Bindings
from pulp.bindings.exceptions import NotFoundException
from pulp.client.consumer.config import read_config


log = getLogger(__name__)

# pulp consumer configuration
# the graph (cfg) is provided for syntactic convenience

pulp_conf = read_config()
cfg = pulp_conf.graph()

# monitor file paths
path_monitor = PathMonitor()

# this plugin object
plugin = Plugin.find(__name__)

# registration status
registered = False


class ValidateRegistrationFailed(Exception):
    """
    The REST call to the server to validate registration failed.
    """
    pass


@initializer
def init_plugin():
    """
    Plugin initialization.
    Called exactly once after the plugin has been loaded.
      1. Update the plugin configuration using the consumer configuration.
      2. Register the consumer certificate bundle path for monitoring.
      3. Start the path monitor.
      4. Validate registration.
      5. If registered, update settings.
    """
    path = os.path.join(cfg.filesystem.id_cert_dir, cfg.filesystem.id_cert_filename)
    path_monitor.add(path, certificate_changed)
    path_monitor.start()
    while True:
        try:
            validate_registration()
            if registered:
                update_settings()
            # DONE
            break
        except ValidateRegistrationFailed:
            sleep(60)


def validate_registration():
    """
    Validate the registration status using the Pulp REST API.
    This is done by fetching the consumer using the ID contained in the certificate.
    Then, matching the UID in the certificate with the _id (database ID) returned
    by the server.
    """
    global registered
    registered = False
    bundle = ConsumerX509Bundle()

    if not bundle.valid():
        return

    try:
        consumer_id = bundle.cn()
        bindings = PulpBindings()
        reply = bindings.consumer.consumer(consumer_id)
        _id = reply.response_body['_id']['$oid']
        if _id == bundle.uid():
            registered = True
    except NotFoundException:
        # not registered
        pass
    except Exception, e:
        msg = _('validate registration failed: %(r)s')
        log.warn(msg, {'r': str(e)})
        raise ValidateRegistrationFailed()


def update_settings():
    """
    Update the plugin settings using the consumer configuration.
    """
    pulp_conf.update(read_config())
    scheme = cfg.messaging.scheme
    host = cfg.messaging.host or cfg.server.host
    port = cfg.messaging.port
    adapter = cfg.messaging.transport
    plugin.cfg.messaging.url = '%s+%s://%s:%s' % (adapter, scheme, host, port)
    plugin.cfg.messaging.uuid = get_agent_id()
    plugin.cfg.messaging.cacert = cfg.messaging.cacert
    plugin.cfg.messaging.clientcert = cfg.messaging.clientcert or \
        os.path.join(cfg.filesystem.id_cert_dir, cfg.filesystem.id_cert_filename)
    plugin.authenticator = Authenticator()
    log.info(_('plugin configuration updated'))


def certificate_changed(path):
    """
    The consumer certificate bundle has changed.
    This indicates a change in registration to pulp.
      1. Validate registration.
      2. If registered, attach to the message broker.
         If not, detach.
    :param path: The absolute path to the changed bundle.
    :type path: str
    """
    log.info(_('changed: %(p)s'), {'p': path})
    while True:
        try:
            validate_registration()
            if registered:
                update_settings()
                plugin.attach()
            else:
                plugin.detach()
            # DONE
            break
        except ValidateRegistrationFailed:
            sleep(60)


def get_agent_id():
    """
    Get the agent ID.
    Format: pulp.agent.<consumer_id>
    :return: The agent ID or None when not registered.
    :rtype: str
    """
    bundle = ConsumerX509Bundle()
    consumer_id = bundle.cn()
    if consumer_id:
        return 'pulp.agent.%s' % consumer_id
    else:
        return None


def get_secret():
    """
    Get the shared secret.
    The shared secret is the DB _id for the consumer object as specified
    in the UID part of the certificate distinguished name (DN).
    :return: The secret.
    :rtype: str
    """
    bundle = ConsumerX509Bundle()
    return bundle.uid()


class Authenticator(object):
    """
    Provides message authentication using RSA keys.
    The server and the agent sign sent messages using their private keys
    and validate received messages using each others public keys.
    """

    def sign(self, digest):
        """
        Sign the specified message.
        :param digest: A message digest.
        :type digest: str
        :return: The message signature.
        :rtype: str
        """
        fp = open(cfg.authentication.rsa_key)
        try:
            pem = fp.read()
            bfr = BIO.MemoryBuffer(pem)
            key = RSA.load_key_bio(bfr)
            return key.sign(digest)
        finally:
            fp.close()

    def validate(self, document, digest, signature):
        """
        Validate the specified message and signature.
        :param document: The original signed document.
        :type document: str
        :param digest: A message digest.
        :type digest: str
        :param signature: A message signature.
        :type signature: str
        :raises ValidationFailed: when message is not valid.
        """
        fp = open(cfg.server.rsa_pub)
        try:
            pem = fp.read()
            bfr = BIO.MemoryBuffer(pem)
            key = RSA.load_pub_key_bio(bfr)
            try:
                if not key.verify(digest, signature):
                    raise ValidationFailed()
            except RSA.RSAError:
                raise ValidationFailed()
        finally:
            fp.close()


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
            msg = _('certificate: %(p)s, not valid')
            log.warn(msg, {'p': self.path})

    def uid(self):
        """
        Get the userid (UID) part of the certificate subject.
        Returns None, if the certificate is invalid.
        :return The userid (UID) part of the certificate subject or None when
            the certificate is not found or invalid.
        :rtype: str
        """
        try:
            return Bundle.uid(self)
        except X509Error:
            msg = _('certificate: %(p)s, not valid')
            log.warn(msg, {'p': self.path})


class PulpBindings(Bindings):
    """
    Pulp (REST) API.
    """
    def __init__(self):
        host = cfg.server.host
        port = int(cfg.server.port)
        verify_ssl = parse_bool(cfg.server.verify_ssl)
        ca_path = cfg.server.ca_path
        cert = os.path.join(cfg.filesystem.id_cert_dir, cfg.filesystem.id_cert_filename)
        connection = PulpConnection(
            host=host,
            port=port,
            cert_filename=cert,
            verify_ssl=verify_ssl,
            ca_path=ca_path)
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


# --- scheduled actions ------------------------------------------------------


@action(minutes=cfg.profile.minutes)
def update_profile():
    """
    Report the unit profile(s).
    """
    if registered:
        profile = Profile()
        profile.send()
    else:
        msg = _('not registered, profile report skipped')
        log.info(msg)


# --- API --------------------------------------------------------------------


class Consumer(object):
    """
    Consumer Management.
    """

    @remote(secret=get_secret)
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

    @remote(secret=get_secret)
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

    @remote(secret=get_secret)
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


class Content(object):
    """
    Content Management.
    """

    @remote(secret=get_secret)
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

    @remote(secret=get_secret)
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

    @remote(secret=get_secret)
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


class Profile(object):
    """
    Profile Management
    """

    @remote(secret=get_secret)
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

        msg = _('reporting profiles: %(r)s')
        log.debug(msg, {'r': report})

        for type_id, profile_report in report.details.items():
            if not profile_report['succeeded']:
                continue

            details = profile_report['details']
            http = bindings.profile.send(consumer_id, type_id, details)

            msg = _('profile (%(t)s), reported: %(r)s')
            log.info(msg, {'t': type_id, 'r': http.response_code})

        return report.dict()
