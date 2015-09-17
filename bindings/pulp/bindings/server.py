from types import NoneType
import base64
import locale
import logging
import os
import urllib
try:
    import oauth2 as oauth
except ImportError:
    # python-oauth2 isn't available on RHEL 5.
    oauth = None

from M2Crypto import httpslib, m2, SSL

from pulp.bindings import exceptions
from pulp.bindings.responses import Response, Task
from pulp.common.compat import json
from pulp.common.constants import DEFAULT_CA_PATH
from pulp.common.util import ensure_utf_8, encode_unicode


class PulpConnection(object):
    """
    Stub for invoking methods against the Pulp server. By default, the
    constructor will assemble the necessary server component configured with
    the values provided. Instead of this behavior, the server_wrapper
    parameter can be used to pass in another mechanism to make the actual
    call to the server. The likely use of this is a duck-typed mock object
    for unit testing purposes.
    """

    def __init__(self,
                 host,
                 port=443,
                 path_prefix='/pulp/api',
                 timeout=120,
                 logger=None,
                 api_responses_logger=None,
                 username=None,
                 password=None,
                 oauth_key=None,
                 oauth_secret=None,
                 oauth_user='admin',
                 cert_filename=None,
                 server_wrapper=None,
                 verify_ssl=True,
                 ca_path=DEFAULT_CA_PATH):

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
        self.oauth_key = oauth_key
        self.oauth_secret = oauth_secret
        self.oauth_user = oauth_user

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

        # SSL validation settings
        self.verify_ssl = verify_ssl
        self.ca_path = ca_path

    def DELETE(self, path, body=None, log_request_body=True, ignore_prefix=False):
        return self._request('DELETE', path, body=body, log_request_body=log_request_body,
                             ignore_prefix=ignore_prefix)

    def GET(self, path, queries=(), ignore_prefix=False):
        return self._request('GET', path, queries, ignore_prefix=ignore_prefix)

    def HEAD(self, path, ignore_prefix=False):
        return self._request('HEAD', path, ignore_prefix=ignore_prefix)

    def POST(self, path, body=None, ensure_encoding=True, log_request_body=True,
             ignore_prefix=False):
        return self._request('POST', path, body=body, ensure_encoding=ensure_encoding,
                             log_request_body=log_request_body, ignore_prefix=ignore_prefix)

    def PUT(self, path, body, ensure_encoding=True, log_request_body=True, ignore_prefix=False):
        return self._request('PUT', path, body=body, ensure_encoding=ensure_encoding,
                             log_request_body=log_request_body, ignore_prefix=ignore_prefix)

    # protected request utilities ---------------------------------------------

    def _request(self, method, path, queries=(), body=None, ensure_encoding=True,
                 log_request_body=True, ignore_prefix=False):
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

        :param ensure_encoding: toggle proper string encoding for the body
        :type ensure_encoding: bool

        :param log_request_body: Toggle logging of the request body, defaults to true
        :type log_request_body: bool

        :param ignore_prefix: when building the url, disregard the self.path_prefix
        :type  ignore_prefix: bool

        :return:    Response object
        :rtype:     pulp.bindings.responses.Response

        :raises:    ConnectionException or one of the RequestExceptions
                    (depending on response codes) in case of unsuccessful
                    request
        """
        url = self._build_url(path, queries, ignore_prefix)
        if ensure_encoding:
            body = self._process_body(body)
        if not isinstance(body, (NoneType, basestring)):
            body = json.dumps(body)
        self.log.debug('sending %s request to %s' % (method, url))

        response_code, response_body = self.server_wrapper.request(method, url, body)

        if self.api_responses_logger:
            if log_request_body:
                self.api_responses_logger.info(
                    '%s request to %s with parameters %s' % (method, url, body))
            else:
                self.api_responses_logger.info(
                    '%s request to %s' % (method, url))
            self.api_responses_logger.info("Response status : %s \n" % response_code)
            self.api_responses_logger.info(
                "Response body :\n %s\n" % json.dumps(response_body, indent=2))

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

    def _process_body(self, body):
        """
        Process the request body, ensuring the proper encoding.
        @param body: request body to process
        @return: properly encoded request body
        """
        if isinstance(body, (list, set, tuple)):
            return [self._process_body(b) for b in body]
        elif isinstance(body, dict):
            return dict((self._process_body(k), self._process_body(v)) for k, v in body.items())
        return ensure_utf_8(body)

    def _handle_exceptions(self, response_code, response_body):

        code_class_mappings = {400: exceptions.BadRequestException,
                               401: exceptions.PermissionsException,
                               404: exceptions.NotFoundException,
                               409: exceptions.ConflictException}

        if response_code not in code_class_mappings:

            # Apache errors are simply strings as compared to Pulp's dicts,
            # so differentiate based on that so we don't get a parse error

            if isinstance(response_body, basestring):
                raise exceptions.ApacheServerException(response_body)
            else:
                raise exceptions.PulpServerException(response_body)

        else:
            raise code_class_mappings[response_code](response_body)

    def _build_url(self, path, queries, ignore_prefix):
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
        :param ignore_prefix: when building the url, disregard the self.path_prefix
        :type  ignore_prefix: bool

        :return:    path that is a composite of self.path_prefix, path, and
                    queries. May be relative or absolute depending on the nature
                    of self.path_prefix
        """
        # build the request url from the path and queries dict or tuple
        if not path.startswith(self.path_prefix) and not ignore_prefix:
            if path.startswith('/'):
                path = path[1:]
            path = '/'.join((self.path_prefix, path))
            # Check if path is ascii and uses appropriate characters,
            # else convert to binary or unicode as necessary.
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


class HTTPSServerWrapper(object):
    """
    Used by the PulpConnection class to make an invocation against the server.
    This abstraction is used to simplify mocking. In this implementation, the
    intricacies (read: ugliness) of invoking and getting the response from
    the HTTPConnection class are hidden in favor of a simpler API to mock.
    """

    def __init__(self, pulp_connection):
        """
        :param pulp_connection: A pulp connection object.
        :type pulp_connection: PulpConnection
        """
        self.pulp_connection = pulp_connection

    def request(self, method, url, body):
        """
        Make the request against the Pulp server, returning a tuple of (status_code, respose_body).
        This method creates a new connection each time since HTTPSConnection has problems
        reusing a connection for multiple calls (as claimed by a prior comment in this module).

        :param method: The HTTP method to be used for the request (GET, POST, etc.)
        :type  method: str
        :param url:    The Pulp URL to make the request against
        :type  url:    str
        :param body:   The body to pass with the request
        :type  body:   str
        :return:       A 2-tuple of the status_code and response_body. status_code is the HTTP
                       status code (200, 404, etc.). If the server's response is valid json,
                       it will be parsed and response_body will be a dictionary. If not, it will be
                       returned as a string.
        :rtype:        tuple
        """
        headers = dict(self.pulp_connection.headers)  # copy so we don't affect the calling method

        # Despite the confusing name, 'sslv23' configures m2crypto to use any available protocol in
        # the underlying openssl implementation.
        ssl_context = SSL.Context('sslv23')
        # This restricts the protocols we are willing to do by configuring m2 not to do SSLv2.0 or
        # SSLv3.0. EL 5 does not have support for TLS > v1.0, so we have to leave support for
        # TLSv1.0 enabled.
        ssl_context.set_options(m2.SSL_OP_NO_SSLv2 | m2.SSL_OP_NO_SSLv3)

        if self.pulp_connection.verify_ssl:
            ssl_context.set_verify(SSL.verify_peer, depth=100)
            # We need to stat the ca_path to see if it exists (error if it doesn't), and if so
            # whether it is a file or a directory. m2crypto has different directives depending on
            # which type it is.
            if os.path.isfile(self.pulp_connection.ca_path):
                ssl_context.load_verify_locations(cafile=self.pulp_connection.ca_path)
            elif os.path.isdir(self.pulp_connection.ca_path):
                ssl_context.load_verify_locations(capath=self.pulp_connection.ca_path)
            else:
                # If it's not a file and it's not a directory, it's not a valid setting
                raise exceptions.MissingCAPathException(self.pulp_connection.ca_path)
        ssl_context.set_session_timeout(self.pulp_connection.timeout)

        if self.pulp_connection.username and self.pulp_connection.password:
            raw = ':'.join((self.pulp_connection.username, self.pulp_connection.password))
            encoded = base64.encodestring(raw)[:-1]
            headers['Authorization'] = 'Basic ' + encoded
        elif self.pulp_connection.cert_filename:
            ssl_context.load_cert(self.pulp_connection.cert_filename)

        # oauth configuration. This block is only True if oauth is not None, so it won't run on RHEL
        # 5.
        if self.pulp_connection.oauth_key and self.pulp_connection.oauth_secret and oauth:
            oauth_consumer = oauth.Consumer(
                self.pulp_connection.oauth_key,
                self.pulp_connection.oauth_secret)
            oauth_request = oauth.Request.from_consumer_and_token(
                oauth_consumer,
                http_method=method,
                http_url='https://%s:%d%s' % (self.pulp_connection.host, self.pulp_connection.port,
                                              url))
            oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), oauth_consumer, None)
            oauth_header = oauth_request.to_header()
            # unicode header values causes m2crypto to do odd things.
            for k, v in oauth_header.items():
                oauth_header[k] = encode_unicode(v)
            headers.update(oauth_header)
            headers['pulp-user'] = self.pulp_connection.oauth_user

        connection = httpslib.HTTPSConnection(
            self.pulp_connection.host, self.pulp_connection.port, ssl_context=ssl_context)

        try:
            # Request against the server
            connection.request(method, url, body=body, headers=headers)
            response = connection.getresponse()
        except SSL.SSLError, err:
            # Translate stale login certificate to an auth exception
            if 'sslv3 alert certificate expired' == str(err):
                raise exceptions.ClientCertificateExpiredException(
                    self.pulp_connection.cert_filename)
            elif 'certificate verify failed' in str(err):
                raise exceptions.CertificateVerificationException()
            else:
                raise exceptions.ConnectionException(None, str(err), None)

        # Attempt to deserialize the body (should pass unless the server is busted)
        response_body = response.read()

        try:
            response_body = json.loads(response_body)
        except:
            pass
        return response.status, response_body
