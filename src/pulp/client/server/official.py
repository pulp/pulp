# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
import httplib
import locale
import os
#import sys
import urllib
from gettext import gettext as _

try:
    import json
except ImportError:
    import simplejson as json

from M2Crypto import SSL, httpslib

from pulp.client.logutil import getLogger
from pulp.client.server.base import Server, ServerRequestError


class PulpServer(Server):
    """
    Pulp server connection class.
    """

    def __init__(self, host, port=443, protocol='https', path_prefix='/pulp/api'):
        super(PulpServer, self).__init__(host, port, protocol, path_prefix)

        default_locale = locale.getdefaultlocale()[0].lower().replace('_', '-')
        headers = {'Accept': 'application/json',
                   'Accept-Language': default_locale,
                   'Content-Type': 'application/json'}
        self.headers.update(headers)

        self._log = getLogger('pulp')

        self.__certfile = None
        self.__keyfile = None
        self.__connection = None

    def __del__(self):
        if self.__connection is not None:
            self.__connection.close()

    # protected server connection methods -------------------------------------

    def _http_connection(self):
        return httplib.HTTPConnection(self.host, self.port)

    def _https_connection(self):
        # make sure that passed in username and password overrides cert/key auth
        if None in (self.__certfile, self.__keyfile) or \
                'Authorization' in self.headers:
            return httplib.HTTPSConnection(self.host, self.port)
        ssl_context = SSL.Context('sslv3')
        ssl_context.load_cert(self.__certfile, self.__keyfile)
        return httpslib.HTTPSConnection(self.host,
                                        self.port,
                                        ssl_context=ssl_context)

    def _connect(self):
        # make an appropriate connection to the pulp server and cache it
        if self.__connection is None:
            if self.protocol == 'http':
                self.__connection = self._http_connection()
            else:
                self.__connection = self._https_connection()
        return self.__connection

    # protected request utilities ---------------------------------------------

    def _build_url(self, path, queries=()):
        # build the request url from the path and queries dict or tuple
        path = '/'.join((self.path_prefix, path))
        queries = urllib.urlencode(queries)
        if queries:
            path = '?'.join((path, queries))
        # make sure the url is ascii and uses appropriate characters
        return urllib.quote(str(path))

    def _request(self, method, path, queries=(), body=None):
        # make a request to the pulp server and return the response
        # NOTE this throws a ServerRequestError if the request did not succeed
        connection = self._connect()
        url = self._build_url(path, queries)
        if body is not None:
            body = json.dumps(body)
        self._log.debug('sending %s request to %s' % (method, url))
        #print >> sys.stderr, 'sending %s request to %s' % (method, url)
        connection.request(method, url, body=body, headers=self.headers)
        response = connection.getresponse()
        response_body = response.read()
        try:
            response_body = json.loads(response_body)
        except:
            pass
        if response.status >= 300:
            raise ServerRequestError(response.status, response_body)
        return (response.status, response_body)

    # credentials setters -----------------------------------------------------

    def set_basic_auth_credentials(self, username, password):
        raw = ':'.join((username, password))
        encoded = base64.encodestring(raw)[:-1]
        self.headers['Authorization'] = 'Basic ' + encoded

    def set_ssl_credentials(self, certfile, keyfile):
        if not os.access(certfile, os.R_OK):
            raise RuntimeError(_('certificate file %s does not exist or cannot be read')
                               % certfile)
        if not os.access(keyfile, os.R_OK):
            raise RuntimeError(_('key file %s does not exist or cannot be read')
                               % keyfile)
        self.__certfile = certfile
        self.__keyfile = keyfile

    # request methods ---------------------------------------------------------

    def DELETE(self, path):
        return self._request('DELETE', path)

    def GET(self, path, queries=()):
        return self._request('GET', path, queries)

    def HEAD(self, path):
        return self._request('HEAD', path)

    def POST(self, path, body=None):
        return self._request('POST', path, body=body)

    def PUT(self, path, body):
        return self._request('PUT', path, body=body)
