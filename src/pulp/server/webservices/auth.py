#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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

import base64
import re

from pulp.server.webservices import http


_whitespace_regex = re.compile('\w+')


class HTTPAuthError(Exception):
    pass


def is_http_basic_auth(credentials):
    """
    Check if the credentials are for http basic authorization
    @type credentials: str
    @param credentials: value of the HTTP_AUTHORIZATION header
    @return: True if the credentials are for http basic authorization,
             False otherwise
    """
    if len(credentials) < 5:
        return False
    type = credentials[:5].lower()
    return type == 'basic'


def http_basic_username_password(credentials):
    """
    Get the username and password from http basic authorization credentials
    """
    credentials = credentials.strip()
    if not _whitespace_regex.match(credentials):
        raise HTTPAuthError('malformed basic authentication information')
    encoded_str = _whitespace_regex.split(credentials, 1)[1].strip()
    decoded_str = base64.decodestring(encoded_str)
    if decoded_str.find(':') < 0:
        raise HTTPAuthError('malformed basic authentication information')
    return decoded_str.split(':', 1)
    
    
def is_http_digest_auth(credentials):
    """
    Check if the credentials are for http digest authorization
    @type credentials: str
    @param credentials: value of the HTTP_AUTHORIZATION header
    @return: True if the credentials are for http digest authorization,
             False otherwise
    """
    if len(credentials) < 6:
        return False
    type = credentials[:6].lower()
    return type == 'digest'


def http_digest_username_password(credentials):
    """
    Get the username and password from http digest authorization credentials
    """
    raise NotImplementedError('HTTP Digest Authorization not yet implemented')


def check_roles(roles):
    """
    Check the http headers for valid authentication information
    """
    # simple check to see if we're even receiving the credentials for now
    credentials = http.http_authorization()
    if credentials is None:
        return False
    if is_http_basic_auth(credentials):
        pass
    elif is_http_digest_auth(credentials):
        pass
    else:
        return False
    return True