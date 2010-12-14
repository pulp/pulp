# -*- coding: utf-8 -*-
from pulp.server.auth.cert_generator import verify_cert

# Copyright © 2010 Red Hat, Inc.
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

"""
Utility functions to manage user credentials in pulp.
"""

import logging

import oauth2

from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.repo import RepoApi
from pulp.server.api.user import UserApi
from pulp.server.auth import cert_generator
from pulp.server.auth.certificate import Certificate
from pulp.server.auth.password_util import check_password
from pulp.server.config import config
from pulp.server.db.model import User
from pulp.server.LDAPConnection import LDAPConnection


_consumer_api = ConsumerApi()
_repo_api = RepoApi()
_user_api = UserApi()

_log = logging.getLogger(__name__)


# username:password authentication --------------------------------------------

def _using_ldap():
    """
    Detects if pulp is configured for ldap
    @rtype: bool
    @return: True if using ldap, False otherwise
    """
    return config.has_section('ldap')


def _check_username_password_ldap(username, password):
    """
    Check a username and password against the ldap server.
    Return None if the username and password are not valid
    @type username: str
    @param username: the login of the user
    @type password: str or None
    @param password: password of the user, None => do not validate the password
    @rtype: L{pulp.server.db.model.User} instance or None
    @return: user corresponding to the credentials
    """
    ldap_uri = "ldap://localhost"
    if config.has_option('ldap', 'uri'):
        ldap_uri = config.get("ldap", "uri")
    else:
        _log.info("No valid server found, default to localhost")
    ldap_base = "dc=localhost"
    if config.has_option('ldap', 'base'):
        ldap_base = config.get('ldap', 'base')
    else:
        _log.info("No valid base found, default to localhost")
    ldap_server = LDAPConnection(ldap_uri)
    ldap_server.connect()
    status = None
    if password is not None:
        status = ldap_server.authenticate_user(ldap_base, username, password)
    else:
        status = ldap_server.lookup_user(ldap_base, username)
    if status is None:
        return None
    return User(username, username, password, username)


def _check_username_password_local(username, password):
    """
    Check a username and password against the local database.
    Return None if the username and password are not valid
    @type username: str
    @param username: the login of the user
    @type password: str or None
    @param password: password of the user, None => do not validate the password
    @rtype: L{pulp.server.db.model.User} instance or None
    @return: user corresponding to the credentials
    """
    user = _user_api.user(username)
    if user is None:
        _log.error('User [%s] specified in certificate was not found in the system' %
                   username)
        return None
    if password is not None:
        if not check_password(user['password'], password):
            _log.error('Password for user [%s] was incorrect' % username)
            return None
    return user


def check_username_password(username, password=None):
    """
    Check a username and password.
    Return None if the username and password are not valid
    @type username: str
    @param username: the login of the user
    @type password: str or None
    @param password: password of the user, None => do not validate the password
    @rtype: L{pulp.server.db.model.User} instance or None
    @return: user corresponding to the credentials
    """
    if _using_ldap():
        return _check_username_password_ldap(username, password)
    return _check_username_password_local(username, password)

# ssl cert authentication -----------------------------------------------------

def check_ssl_cert(cert_pem):
    """
    Check a client ssl certificate.
    Return None if the certificate is not valid
    @type cert_pem: str
    @param cert_pem: pem encoded ssl certificate
    @rtype: L{pulp.server.db.model.User} instance or None
    @return: user corresponding to the credentials
    """
    cert = Certificate(content=cert_pem)
    subject = cert.subject()
    encoded_user = subject.get('CN', None)
    if not encoded_user:
        return None
    if not verify_cert(cert_pem):
        _log.error('Auth certificate with CN [%s] is signed by a foreign CA' %
                   encoded_user)
        return None
    username, id = cert_generator.decode_admin_user(encoded_user)
    return check_username_password(username)

# oauth authentication --------------------------------------------------------

def check_oauth(username, method, url, auth, query):
    """
    Check OAuth header credentials.
    Return None if the credentials are invalid
    @type username: str
    @param username: username corresponding to credentials
    @type method: str
    @param method: http method
    @type url: str
    @param url: request url
    @type auth: str
    @param auth: http authorization header value
    @type query: str
    @param query: http request query string
    @rtype: L{pulp.server.db.model.User} instance or None
    @return: user corresponding to the credentials
    """
    headers = {'Authorization': auth}
    req = oauth2.Request.from_request(method, url, headers, query_string=query)
    if not req:
        return None
    if not (config.has_option('security', 'oauth_key') and
            config.has_option('security', 'oauth_secret')):
        _log.error("Attempting OAuth authentication and you do not have oauth_key and oauth_secret in pulp.conf")
        return None
    key = config.get('security', 'oauth_key')
    secret = config.get('security', 'oauth_secret')
    consumer = oauth2.Consumer(key=key, secret=secret)
    server = oauth2.Server()
    server.add_signature_method(oauth2.SignatureMethod_HMAC_SHA1())
    try:
        # this call has a return value, but failures are noted by the exception
        server.verify_request(req, consumer, None)
    except oauth2.Error, e:
        _log.error('error verifying OAuth signature: %s' % e)
        return None
    return _check_username_password_local(username)
