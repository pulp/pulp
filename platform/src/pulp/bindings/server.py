# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
import locale
import logging
from M2Crypto import SSL, httpslib
import urllib
from pulp.bindings.responses import Response, Task

try:
    import json
except ImportError:
    import simplejson as json

import pulp.bindings.exceptions as exceptions

# -- server connection --------------------------------------------------------

class PulpConnection(object):
    """
    Stub for invoking methods against the Pulp server. By default, the
    constructor will assemble the necessary server component configured with
    the values provided. Instead of this behavior, the server_wrapper
    parameter can be used to pass in another mechanism to make the actual
    call to the server. The likely use of this is a duck-typed mock object
    for unit testing purposes.
    """

    def __init__(self, host, port=443, path_prefix='/pulp/api', timeout=120,
                 logger=None, api_responses_logger=None,
                 username=None, password=None, cert_filename=None, server_wrapper=None):

        self.host = host
        self.port = port
        self.path_prefix = path_prefix
        self.timeout = timeout

        self.log = logger or logging.getLogger(__name__)
        self.api_responses_logger = api_responses_logger

        # Credentials
        self.username = username
        self.password = password
        self.cert_filename = cert_filename

        # Locale
        default_locale = locale.getdefaultlocale()[0]
        if default_locale:
            default_locale = default_locale.lower().replace('_', '-')
        else:
            default_locale = 'en-us'

        # Headers
        self.headers = {'Accept': 'application/json',
                        'Accept-Language': default_locale,
                        'Content-Type': 'application/json'}

        # Server Wrapper
        if server_wrapper:
            self.server_wrapper = server_wrapper
        else:
            self.server_wrapper = HTTPSServerWrapper(self)

    # -- public methods -------------------------------------------------------

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

    # protected request utilities ---------------------------------------------

    def _request(self, method, path, queries=(), body=None):
        """
        make a HTTP request to the pulp server and return the response

        :param method:  name of an HTTP method such as GET, POST, PUT, HEAD
                        or DELETE
        :type  method:  basestring

        :param path:    URL for this request
        :type  path:    basestring

        :param queries: mapping object or a sequence of 2-element tuples,
                        in either case representing key-value pairs to be used
                        as query parameters on the URL.
        :type  queries: mapping object or sequence of 2-element tuples

        :param body:    Data structure that will be JSON serialized and send as
                        the request's body.
        :type  body:    Anything that is JSON-serializable.

        :return:    Response object
        :rtype:     pulp.bindings.responses.Response

        :raises:    ConnectionException or one of the RequestExceptions
                    (depending on response codes) in case of unsuccessful
                    request
        """
        url = self._build_url(path, queries)
        if not isinstance(body, (type(None), str,)):
            body = json.dumps(body)
        self.log.debug('sending %s request to %s' % (method, url))

        response_code, response_body = self.server_wrapper.request(method, url, body)

        if self.api_responses_logger:
            self.api_responses_logger.info('%s request to %s with parameters %s' % (method, url, body))
            self.api_responses_logger.info("Response status : %s \n" % response_code)
            self.api_responses_logger.info("Response body :\n %s\n" % json.dumps(response_body, indent=2))

        if response_code >= 300:
            self._handle_exceptions(response_code, response_body)
        elif response_code == 200 or response_code == 201:
            body = response_body
        elif response_code == 202:
            if isinstance(response_body, list):
                body = [Task(t) for t in response_body]
            else:
                body = Task(response_body)

        return Response(response_code, body)

    def _handle_exceptions(self, response_code, response_body):

        code_class_mappings = {400 : exceptions.BadRequestException,
                               401 : exceptions.PermissionsException,
                               404 : exceptions.NotFoundException,
                               409 : exceptions.ConflictException}

        if response_code not in code_class_mappings:
            raise exceptions.PulpServerException(response_body)
        else:
            raise code_class_mappings[response_code](response_body)

    def _build_url(self, path, queries=()):
        """
        Takes a relative path and query parameters, combines them with the
        base path, and returns the result. Handles utf-8 encoding as necessary.

        :param path:    relative path for this request, relative to
                        self.base_prefix. NOTE: if this parameter starts with a
                        leading '/', this method will strip it and treat it as
                        relative. That is not a standards-compliant way to
                        combine path segments, so be aware.
        :type  path:    basestring

        :param queries: mapping object or a sequence of 2-element tuples,
                        in either case representing key-value pairs to be used
                        as query parameters on the URL.
        :type  queries: mapping object or sequence of 2-element tuples

        :return:    path that is a composite of self.path_prefix, path, and
                    queries. May be relative or absolute depending on the nature
                    of self.path_prefix
        """
        # build the request url from the path and queries dict or tuple
        if not path.startswith(self.path_prefix):
            if path.startswith('/'):
                path = path[1:]
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

# -- wrapper classes ----------------------------------------------------------

class HTTPSServerWrapper(object):
    """
    Used by the PulpConnection class to make an invocation against the server.
    This abstraction is used to simplify mocking. In this implementation, the
    intricacies (read: ugliness) of invoking and getting the response from
    the HTTPConnection class are hidden in favor of a simpler API to mock.
    """

    def __init__(self, pulp_connection):
        self.pulp_connection = pulp_connection

    def request(self, method, url, body):

        headers = dict(self.pulp_connection.headers) # copy so we don't affect the calling method

        # Create a new connection each time since HTTPSConnection has problems
        # reusing a connection for multiple calls (lame).
        ssl_context = None
        if self.pulp_connection.username and self.pulp_connection.password:
            raw = ':'.join((self.pulp_connection.username, self.pulp_connection.password))
            encoded = base64.encodestring(raw)[:-1]
            headers['Authorization'] = 'Basic ' + encoded
        elif self.pulp_connection.cert_filename:
            ssl_context = SSL.Context('sslv3')
            ssl_context.set_session_timeout(self.pulp_connection.timeout)
            ssl_context.load_cert(self.pulp_connection.cert_filename)

        # Can't pass in None, so need to decide between two signatures (also lame)
        if ssl_context is not None:
            connection = httpslib.HTTPSConnection(self.pulp_connection.host, self.pulp_connection.port, ssl_context=ssl_context)
        else:
            connection = httpslib.HTTPSConnection(self.pulp_connection.host, self.pulp_connection.port)

        # Request against the server
        connection.request(method, url, body=body, headers=headers)

        try:
            response = connection.getresponse()
        except SSL.SSLError, err:
            # Translate stale login certificate to an auth exception
            if 'sslv3 alert certificate expired' == str(err):
                raise exceptions.PermissionsException()
            else:
                raise exceptions.ConnectionException(None, str(err), None)

        # Attempt to deserialize the body (should pass unless the server is busted)
        response_body = response.read()

        try:
            response_body = json.loads(response_body)
        except:
            pass
        return response.status, response_body
