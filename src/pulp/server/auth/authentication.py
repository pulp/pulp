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
from gettext import gettext as _

from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.repo import RepoApi
from pulp.server.api.user import UserApi
from pulp.server.auth import cert_generator
from pulp.server.auth.certificate import Certificate
from pulp.server.auth.password_util import check_password
from pulp.server.auth.principal import get_principal
from pulp.server.config import config
from pulp.server.db.model import User
from pulp.server.LDAPConnection import LDAPConnection
from pulp.server.pexceptions import PulpException


_consumer_api = ConsumerApi()
_repo_api = RepoApi()
_user_api = UserApi()

_log = logging.getLogger(__name__)


def _using_ldap():
    return config.has_section('ldap')


def _check_username_password_ldap(username, password):
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
    if _using_ldap():
        return _check_username_password_ldap(username, password)
    return _check_username_password_local(username, password)


def cert_authentication(cert_pem):
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
