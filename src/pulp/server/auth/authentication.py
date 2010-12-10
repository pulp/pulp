# -*- coding: utf-8 -*-

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
from pulp.server.LDAPConnection import LDAPConnection
from pulp.server.pexceptions import PulpException


_consumer_api = ConsumerApi()
_repo_api = RepoApi()
_user_api = UserApi()

_log = logging.getLogger(__name__)


def _check_username(username):
    return None


def cert_authentication(cert_pem):
    cert = Certificate(content=cert_pem)
    subject = cert.subject()
    encoded_user = subject.get('CN', None)
    if not encoded_user:
        return None
    username, id = cert_generator.decode_admin_user(encoded_user)
    return _check_username(username)
