from gettext import gettext as _
import logging

import oauth2

from pulp.server.auth import ldap_connection
from pulp.server.config import config
from pulp.server.db import model
from pulp.server.db.model.consumer import Consumer
from pulp.server.exceptions import PulpException
from pulp.server.managers import factory


_logger = logging.getLogger(__name__)


class AuthenticationManager(object):
    """
    Manages user and consumer authentication in pulp.
    """
    def _check_username_password_local(self, username, password=None):
        """
        Check a username and password against the local database.
        Return None if the username and password are not valid

        :type username: str
        :param username: the login of the user

        :type password: str or None
        :param password: password of the user, None => do not validate the password

        :rtype: L{pulp.server.db.model.auth.User} instance or None
        :return: user corresponding to the credentials
        """
        user = model.User.objects(login=username).first()
        if user is None:
            _logger.debug(_('User [%(u)s] specified in certificate was not found in the system') %
                          {'u': username})
            return None

        if user['password'] is None and password is not None:
            _logger.debug('This is an ldap user %s' % user)
            return None

        if password is not None:
            if not user.check_password(password):
                _logger.debug('Password for user [%s] was incorrect' % username)
                return None

        return user

    def _check_username_password_ldap(self, username, password=None):
        """
        Check a username and password against the ldap server.
        Return None if the username and password are not valid

        :type username: str
        :param username: the login of the user

        :type password: str or None
        :param password: password of the user, None => do not validate the password

        :rtype: L{pulp.server.db.model.auth.User} instance or None
        :return: user corresponding to the credentials
        """

        ldap_uri = config.get('ldap', 'uri')
        ldap_base = config.get('ldap', 'base')
        ldap_tls = config.getboolean('ldap', 'tls')

        ldap_filter = None
        if config.has_option('ldap', 'filter'):
            ldap_filter = config.get('ldap', 'filter')

        ldap_server = ldap_connection.LDAPConnection(server=ldap_uri, tls=ldap_tls)
        ldap_server.connect()
        user = ldap_server.authenticate_user(ldap_base, username, password,
                                             filter=ldap_filter)
        return user

    def check_username_password(self, username, password=None):
        """
        Check username and password.
        Return None if the username and password are not valid

        :type username: str
        :param username: the login of the user

        :type password: str or None
        :param password: password of the user, None => do not validate the password

        :rtype: str or None
        :return: user login corresponding to the credentials
        """
        user = self._check_username_password_local(username, password)
        if user is None and config.getboolean('ldap', 'enabled'):
            user = self._check_username_password_ldap(username, password)
        if user is not None:
            return user['login']
        return None

    def check_user_cert(self, cert_pem):
        """
        Check a client ssl certificate.
        Return None if the certificate is not valid

        :type cert_pem: str
        :param cert_pem: pem encoded ssl certificate

        :rtype: str or None
        :return: user login corresponding to the credentials
        """
        cert = factory.certificate_manager(content=cert_pem)
        subject = cert.subject()
        encoded_user = subject.get('CN', None)

        if not encoded_user:
            return None

        cert_gen_manager = factory.cert_generation_manager()
        if not cert_gen_manager.verify_cert(cert_pem):
            _logger.error(_('Auth certificate with CN [%(u)s] is signed by a foreign CA') %
                          {'u': encoded_user})
            return None

        try:
            username, id = cert_gen_manager.decode_admin_user(encoded_user)
        except PulpException:
            return None

        return self.check_username_password(username)

    def check_consumer_cert(self, cert_pem):
        """
        Check a consumer ssl certificate.
        Return None if the certificate is not valid

        :type cert_pem: str
        :param cert_pem: pem encoded ssl certificate

        :rtype: str or None
        :return: id of a consumer corresponding to the credentials
        """
        cert = factory.certificate_manager(content=cert_pem)
        subject = cert.subject()
        consumerid = subject.get('CN', None)

        if consumerid is None:
            return None

        cert_gen_manager = factory.cert_generation_manager()
        if not cert_gen_manager.verify_cert(cert_pem):
            _logger.error(_('Auth certificate with CN [%(cn)s] is signed by a foreign CA') %
                          {'cn': consumerid})
            return None

        return consumerid

    def check_oauth(self, username, method, url, auth, query):
        """
        Check OAuth header credentials.
        Return None if the credentials are invalid

        :type username: str
        :param username: username corresponding to credentials

        :type method: str
        :param method: http method

        :type url: str
        :param url: request url

        :type auth: str
        :param auth: http authorization header value

        :type query: str
        :param query: http request query string

        :rtype: str or None
        :return: user login corresponding to the credentials
        """
        is_consumer = False
        headers = {'Authorization': auth}
        req = oauth2.Request.from_request(method, url, headers, query_string=query)

        if not req:
            return None, is_consumer

        if not (config.has_option('oauth', 'oauth_key') and
                config.has_option('oauth', 'oauth_secret')):
            _logger.error(_("Attempting OAuth authentication and you do not have oauth_key and "
                            "oauth_secret in pulp.conf"))
            return None, is_consumer

        key = config.get('oauth', 'oauth_key')
        secret = config.get('oauth', 'oauth_secret')

        consumer = oauth2.Consumer(key=key, secret=secret)
        server = oauth2.Server()
        server.add_signature_method(oauth2.SignatureMethod_HMAC_SHA1())

        try:
            # this call has a return value, but failures are noted by the exception
            server.verify_request(req, consumer, None)
        except oauth2.Error, e:
            _logger.error('error verifying OAuth signature: %s' % e)
            return None, is_consumer

        user = self._check_username_password_local(username)
        if user is not None:
            return user['login'], is_consumer
        consumer = Consumer.get_collection().find_one({'id': username})
        if consumer is not None:
            is_consumer = True
            return consumer['id'], is_consumer

        return None, is_consumer
