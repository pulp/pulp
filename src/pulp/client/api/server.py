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

import base64
import httplib
import locale
import os
import sys
import urllib
from gettext import gettext as _

try:
    import json
except ImportError:
    import simplejson as json

from M2Crypto import SSL, httpslib

from pulp.client.lib.logutil import getLogger, getResponseLogger
# current active server -------------------------------------------------------

active_server = None


def set_active_server(server):
    global active_server
    assert isinstance(server, Server)
    active_server = server

# base server class -----------------------------------------------------------

class ServerRequestError(Exception):
    """
    Exception to indicate a less than favorable response from the server.
    The arguments are [0] the response status as an integer and
    [1] the response message as a dict, if we managed to decode from json,
    or a str if we didn't [2] potentially a traceback, if the server response
    was a python error, otherwise it will be None
    """
    pass


class NoCredentialsError(Exception):
    """
    Indicates an attempt was made to do a server call without providing
    authentication credentials, either through a certificate or as command
    line flags.
    """
    pass

class Bytes(str):
    """
    Binary (non-json) PUT/POST request body wrapper.
    """
    pass


class Server(object):
    """
    Base server class.
    @ivar host: host name of the pulp server
    @ivar port: port the pulp server is listening on (443)
    @ivar protocol: protocol the pulp server is using (http, https)
    @ivar path_prefix: mount point of the pulp api (/pulp/api)
    @ivar headers: dictionary of http headers to send in requests
    @ivar timeout: connection timeout value in seconds
    """

    def __init__(self, host, port=80, protocol='http', path_prefix='', timeout=60):
        assert protocol in ('http', 'https')

        self.host = host
        self.port = port
        self.protocol = protocol
        self.path_prefix = path_prefix
        self.headers = {}
        self.timeout = timeout

    # credentials setters -----------------------------------------------------

    def set_basic_auth_credentials(self, username, password):
        """
        Set username and password credentials for http basic auth
        @type username: str
        @param username: username
        @type password: str
        @param password: password
        """
        raise NotImplementedError('base server class method called')

    def set_ssl_credentials(self, certfile):
        """
        Set ssl certificate and public key credentials
        @type certfile: str
        @param certfile: absolute path to the certificate file
        @type keyfile: str
        @param keyfile: absolute path to the public key file
        @raise RuntimeError: if either of the files cannot be found or read
        """
        raise NotImplementedError('base server class method called')

    def has_credentials_set(self):
        raise NotImplementedError('base server class method called')

    # request methods ---------------------------------------------------------

    def DELETE(self, path, body=None):
        """
        Send a DELETE request to the pulp server.
        @type path: str
        @param path: path of the resource to delete
        @rtype: (int, dict or None or str)
        @return: tuple of the http response status and the response body
        @raise ServerRequestError: if the request fails
        """
        raise NotImplementedError('base server class method called')

    def GET(self, path, queries=()):
        """
        Send a GET request to the pulp server.
        @type path: str
        @param path: path of the resource to get
        @type queries: dict or iterable of tuple pairs
        @param queries: dictionary of iterable of key, value pairs to send as
                        query parameters in the request
        @rtype: (int, dict or None or str)
        @return: tuple of the http response status and the response body
        @raise ServerRequestError: if the request fails
        """
        raise NotImplementedError('base server class method called')

    def HEAD(self, path):
        """
        Send a HEAD request to the pulp server.
        @type path: str
        @param path: path of the resource to check
        @rtype: (int, dict or None or str)
        @return: tuple of the http response status and the response body
        @raise ServerRequestError: if the request fails
        """
        raise NotImplementedError('base server class method called')

    def POST(self, path, body=None):
        """
        Send a POST request to the pulp server.
        @type path: str
        @param path: path of the resource to post to
        @type body: dict or None
        @param body: (optional) dictionary for json encoding of post parameters
        @rtype: (int, dict or None or str)
        @return: tuple of the http response status and the response body
        @raise ServerRequestError: if the request fails
        """
        raise NotImplementedError('base server class method called')

    def PUT(self, path, body):
        """
        Send a PUT request to the pulp server.
        @type path: str
        @param path: path of the resource to put
        @type body: dict
        @param body: dictionary for json encoding of resource
        @rtype: (int, dict or None or str)
        @return: tuple of the http response status and the response body
        @raise ServerRequestError: if the request fails
        """
        raise NotImplementedError('base server class method called')

# pulp server class -----------------------------------------------------------

class PulpServer(Server):
    """
    Pulp server connection class.
    """

    def __init__(self, host, port=443, protocol='https', path_prefix='/pulp/api', timeout=120):
        super(PulpServer, self).__init__(host, port, protocol, path_prefix, timeout)

        default_locale = locale.getdefaultlocale()[0]
        if default_locale:
            default_locale = default_locale.lower().replace('_', '-')
        else:
            default_locale = 'en-us'

        headers = {'Accept': 'application/json',
                   'Accept-Language': default_locale,
                   'Content-Type': 'application/json'}
        self.headers.update(headers)

        self._log = getLogger('pulp')

        self.__certfile = None


    # protected server connection methods -------------------------------------

    def _http_connection(self):
        return httplib.HTTPConnection(self.host, self.port, timeout=self.timeout)

    def _https_connection(self):
        # make sure that passed in username and password overrides cert/key auth
        if self.__certfile is None or \
                'Authorization' in self.headers:
            return httplib.HTTPSConnection(self.host, self.port)
        ssl_context = SSL.Context('sslv3')
        ssl_context.set_session_timeout(self.timeout)
        ssl_context.load_cert(self.__certfile)
        #print >> sys.stderr, 'making connection with: %s' % (self.__certfile)
        return httpslib.HTTPSConnection(self.host,
                                        self.port,
                                        ssl_context=ssl_context)

    def _connect(self):
        # make sure credentials are set
        if not self.has_credentials_set():
            msg = _('No valid authorization credentials found')
            # try to deduce the name of the script, if we're being run from one
            if sys.argv:
                msg += _(', please see: %s --help') % os.path.basename(sys.argv[0])
            raise NoCredentialsError(None, msg)
        # make an appropriate connection to the pulp server
        if self.protocol == 'http':
            return self._http_connection()
        else:
            return self._https_connection()

    # protected request utilities ---------------------------------------------

    def _build_url(self, path, queries=()):
        # build the request url from the path and queries dict or tuple
        if not path.startswith(self.path_prefix):
            path = '/'.join((self.path_prefix, path))
        # Check if path is ascii and uses appropriate characters, else convert to binary or unicode as necessary.
        try:
            path = urllib.quote(str(path))
        except UnicodeEncodeError:
            path = urllib.quote(path.encode('utf-8'))
        except UnicodeDecodeError:
            path = urllib.quote(path.decode('utf-8'))
        queries = urllib.urlencode(queries)
        if queries:
            path = '?'.join((path, queries))
        return path

    def _request(self, method, path, queries=(), body=None):
        # make a request to the pulp server and return the response
        # NOTE this throws a ServerRequestError if the request did not succeed
        connection = self._connect()
        url = self._build_url(path, queries)
        if not isinstance(body, (type(None), Bytes,)):
            body = json.dumps(body)
        self._log.debug('sending %s request to %s' % (method, url))
        #print >> sys.stderr, 'sending %s request to %s' % (method, url)
        connection.request(method, url, body=body, headers=self.headers)
        try:
            response = connection.getresponse()
        except SSL.SSLError, err:
            raise ServerRequestError(None, str(err), None)
        response_body = response.read()
        try:
            response_body = json.loads(response_body)
        except:
            pass

        if os.getenv("API_RESPONSE_LOG"):
            self._response_log = getResponseLogger('api_responses', os.getenv("API_RESPONSE_LOG"))
            self._response_log.info('%s request to %s with parameters %s' % (method, url, body))
            self._response_log.info("Response status and reason : %s  %s\n" % (response.status, response.reason))
            self._response_log.info("Response body :\n %s\n" % json.dumps(response_body, indent=2))
                
        if response.status >= 300:
            # if the server has responded with a python traceback
            # try to split it out
            if isinstance(response_body, basestring) and \
                    response_body.startswith('Traceback'):
                traceback, message = response_body.strip().rsplit('\n', 1)
                raise ServerRequestError(response.status, message, traceback)
            raise ServerRequestError(response.status, response_body, None)
        return (response.status, response_body)

    def _encoded(self, body):
        if body is None:
            return body

    # credentials setters -----------------------------------------------------

    def set_basic_auth_credentials(self, username, password):
        raw = ':'.join((username, password))
        encoded = base64.encodestring(raw)[:-1]
        self.headers['Authorization'] = 'Basic ' + encoded

    def set_ssl_credentials(self, certfile):
        if not os.access(certfile, os.R_OK):
            raise RuntimeError(_('certificate file %s does not exist or cannot be read')
                               % certfile)
        self.__certfile = certfile

    def has_credentials_set(self):
        return 'Authorization' in self.headers or self.__certfile is not None

    # request methods ---------------------------------------------------------

    def DELETE(self, path, body=None):
        return self._request('DELETE', path, body=body)

    def GET(self, path, queries=()):
        return self._request('GET', path, queries)

    def HEAD(self, path):
        return self._request('HEAD', path)

    def POST(self, path, body=None):
        return self._request('POST', path, body=body)

    def PUT(self, path, body):
        return self._request('PUT', path, body=body)
