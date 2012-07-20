# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Pulp Interactive Client
This module is meant to be imported to talk to pulp webservices interactively
from an interpreter. It provides convenience methods for connecting to pulp as
well as performing many common pulp tasks.
"""

import base64
import httplib
import json
import os
import sys
import types
import urllib

HOST = 'localhost'
PORT = 443
PATH_PREFIX = '/pulp/api'
AUTH_SCHEME = 'basic' # can also be 'oauth' (XXX not really)
USER = 'admin'
PASSWORD = 'admin'

# connection management -------------------------------------------------------

_CONNECTION = None

def connect():
    global _CONNECTION
    _CONNECTION = httplib.HTTPSConnection(HOST, PORT)

# auth credentials ------------------------------------------------------------

def set_basic_auth_credentials(user, password):
    global AUTH_SCHEME, USER, PASSWORD
    AUTH_SCHEME = 'basic'
    USER = user
    PASSWORD = password


# XXX misspelled as well as incorrect
#def set_oauth_credentials(user):
#    global _auth_scheme, _user, _password
#    _auth_scheme = 'oauth'
#    _user = user
#    _password = ''

# requests --------------------------------------------------------------------

class RequestError(Exception):
    pass


def _auth_header():
    def _basic_auth_header():
        raw = ':'.join((USER, PASSWORD))
        encoded = base64.encodestring(raw)[:-1]
        return {'Authorization': 'Basic %s' % encoded}
    def _oauth_header():
        return {}
    if AUTH_SCHEME == 'basic':
        return _basic_auth_header()
    if AUTH_SCHEME == 'oauth':
        return _oauth_header()
    return {}


def _request(method, path, body=None):
    if _CONNECTION is None:
        raise RuntimeError('You must run connect() before making requests')
    if not isinstance(body, types.NoneType):
        body = json.dumps(body)
    _CONNECTION.request(method,
                        PATH_PREFIX + path,
                        body=body,
                        headers=_auth_header())
    response = _CONNECTION.getresponse()
    response_body = response.read()
    try:
        response_body = json.loads(response_body)
    except:
        pass
    if response.status > 299:
        raise RequestError('Server response: %d\n%s' %
                           (response.status, response_body))
    return (response.status, response_body)


def GET(path, **params):
    if params:
        path = '?'.join((path, urllib.urlencode(params)))
    return _request('GET', path)


def OPTIONS(path):
    return _request('OPTIONS', path)


def PUT(path, body):
    return _request('PUT', path, body)


def POST(path, body=None):
    return _request('POST', path, body)


def DELETE(path):
    return _request('DELETE', path)

# repo management -------------------------------------------------------------

def list_repos():
    return GET('/repositories/')


def get_repo(id):
    return GET('/repositories/%s/' % id)


def create_repo(id, name=None, arch='noarch', **kwargs):
    """
    Acceptable keyword arguments are any arguments for a new Repo model.
    Common ones are: feed and sync_schedule
    """
    kwargs.update({'id': id, 'name': name or id, 'arch': arch})
    return POST('/repositories/', kwargs)


def update_repo(id, **kwargs):
    """
    Acceptable keyword arguments are any arguments for a new Repo model.
    Common ones are: feed and sync_schedule
    """
    return PUT('/repositories/%s/' % id, kwargs)


def delete_repo(id):
    return DELETE('/repositories/%s/' % id)


def schedules():
    """
    List the sync schedules for all the repositories.
    """
    return GET('/repositories/schedules/')


def sync_history(id):
    return GET('/repositories/%s/history/sync/' % id)

# -----------------------------------------------------------------------------

if __name__ == '__main__':
    print >> sys.stderr, 'Not a script, import as a module in an interpreter'
    sys.exit(os.EX_USAGE)
