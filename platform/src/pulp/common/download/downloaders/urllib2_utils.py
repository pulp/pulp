# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import functools
import httplib
import socket
import ssl
import urllib
import urllib2


HTTP_SCHEME = 'http'
HTTPS_SCHEME = 'https'


# multiple inheritance is to shut PyCharm up about these not being derived from Exception
class InvalidHostSSLCertificate(urllib2.URLError, Exception): pass
class ProxyConnectionFailed(urllib2.URLError, Exception): pass

# -- pulp connection class -----------------------------------------------------

class PulpConnection(httplib.HTTPSConnection):
    """
    Connection class that does all the heavy lifting for the PulpHandler class.
    """

    _ports = {HTTP_SCHEME: httplib.HTTP_PORT, HTTPS_SCHEME: httplib.HTTPS_PORT}

    def __init__(self, host, port=None, scheme=HTTP_SCHEME, strict=None,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None,
                 key_file=None, cert_file=None, ca_cert_file=None, validate_host=True,
                 is_proxy=False):

        assert scheme in (HTTP_SCHEME, HTTPS_SCHEME)

        self.scheme = scheme

        httplib.HTTPSConnection.__init__(self, host, port, key_file, cert_file,
                                         strict, timeout, source_address)

        self.ca_cert_file = ca_cert_file
        self.validate_host = validate_host

        self.is_proxy = is_proxy
        # will be changed in the request if connection is a proxy
        self._real_host = self.host
        self._real_port = self.port

    @property
    def default_port(self):
        return self._ports[self.scheme]

    def request(self, method, url, body=None, headers=None):
        """
        Send an HTTP or HTTPS request, as appropriate; and parse the request
        URL in case it's a proxied request.
        """
        protocol = self.scheme
        headers = headers or {}

        if self.is_proxy:
            # if it's a proxied connection, a full URL is passed in, so parse it

            protocol, remainder = urllib.splittype(url)

            if protocol not in (HTTP_SCHEME, HTTPS_SCHEME):
                raise ValueError('Unsupported URL protocol: %s' % url)

            host, remainder = urllib.splithost(remainder)
            host, port = urllib.splitnport(host)
            port = port or self._ports[protocol]

            self._real_host = host
            self._real_port = port

        if protocol == HTTP_SCHEME:
            httplib.HTTPConnection.request(self, method, url, body, headers)
        else: # HTTPS_SCHEME
            httplib.HTTPSConnection.request(self, method, url, body, headers)

    def connect(self):
        """
        Make an HTTP or HTTPS connection to the configured host.
        Send a proxy CONNECT request if it's a proxied connection.
        """
        if self.scheme == HTTP_SCHEME:
            httplib.HTTPConnection.connect(self)

        else: # HTTPS_SCHEME
            self._validate_server_ssl_cert()
            self._ssl_wrap_socket()
            httplib.HTTPSConnection.connect(self)

        self._send_proxy_connect_request()

    def _validate_server_ssl_cert(self):

        if not self.validate_host:
            return

        try:
            ssl.get_server_certificate((self._real_host, self._real_port))

        except ssl.SSLError:
            raise InvalidHostSSLCertificate('Cannot verify host <%s> with ca cert: %s' %
                                            (self._real_host, self.ca_cert_file))

    def _ssl_wrap_socket(self):

        ssl_sock = ssl.wrap_socket(self.sock, self.key_file, self.cert_file)
        self.sock = httplib.FakeSocket(self.sock, ssl_sock)

    def _send_proxy_connect_request(self):

        if not self.is_proxy:
            return

        # send proxy CONNECT request
        self.send('CONNECT %s:%d HTTP/1.0\r\n\r\n' % (self._real_host, self._real_port))

        # expect a HTTP/1.0 200 Connection established
        response = self.response_class(self.sock, strict=self.strict, method=self._method)
        (version, code, message) = response._read_status()

        if code != httplib.OK:
            self.close()
            raise ProxyConnectionFailed('Proxy connection failed: %d %s' % (code, message.strip()))

        while True:
            line = response.fp.readline()
            if line == '\r\n': break

# -- pulp handler --------------------------------------------------------------

class PulpHandler(urllib2.HTTPHandler,
                  urllib2.HTTPSHandler,
                  urllib2.ProxyHandler):
    """
    urllib2 Handler class

    This class replaces the default HTTPHandler, HTTPSHandler, and ProxyHandler,

    It allows proxied HTTPS requests as well as SSL verification.
    """

    def __init__(self, key_file=None, cert_file=None, ca_cert_file=None,
                 verify_host=False, proxy_url=None, proxy_port=None,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT):

        proxies = {} # this has the consequence of not using proxies configured elsewhere

        complete_proxy_url = build_proxy_url(proxy_url, proxy_port)
        if complete_proxy_url is not None:
            proxies[urllib.splittype(complete_proxy_url)[0]] = complete_proxy_url

        urllib2.HTTPHandler.__init__(self)
        urllib2.HTTPSHandler.__init__(self)
        urllib2.ProxyHandler.__init__(self, proxies)

        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_cert_file = ca_cert_file
        self.verify_host = verify_host

        self.proxy_url = complete_proxy_url

        self.timeout = timeout

    # handler chain methods

    def http_open(self, req):
        kwargs = {'scheme': HTTP_SCHEME,
                  'timeout': self.timeout}
        factory = functools.partial(pulp_connection_factory, **kwargs)
        return self.do_open(factory, req)

    def https_open(self, req):
        kwargs = {'scheme': HTTPS_SCHEME,
                  'key_file': self.key_file,
                  'cert_file': self.cert_file,
                  'ca_cert_file': self.ca_cert_file,
                  'verify_host': self.verify_host,
                  'timeout': self.timeout}
        factory = functools.partial(pulp_connection_factory, **kwargs)
        return self.do_open(factory, req)

    def proxy_open(self, req, proxy, scheme):
        kwargs = {'scheme': scheme,
                  'proxy_url': self.proxy_url,
                  'timeout': self.timeout}
        factory = functools.partial(pulp_connection_factory, **kwargs)
        return self.do_open(factory, req)


def pulp_connection_factory(host, scheme, key_file=None, cert_file=None, ca_cert_file=None,
                            verify_host=False, proxy_url=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,):
    """
    Factory method for constructing a PulpConnection instance.

    :param host: host and port string in the format, host:port
    :type host: str
    :param scheme: URL scheme (one of http or https)
    :type scheme: str
    :param key_file: path to the client key file
    :type key_file: str or None
    :param cert_file: path to the client certificate file
    :type cert_file: str or None
    :param ca_cert_file: path to a certificate authority file
    :type ca_cert_file: str or None
    :param verify_host: toggle host's SSL certificate verification
    :type verify_host: bool
    :param proxy_url: proxy URL
    :type proxy_url: str or None
    :param timeout: connection timeout
    :type timeout: int or float
    :return: a connection object used to make requests
    :rtype: PulpConnection
    """
    is_proxy = proxy_url is not None
    if is_proxy:
        host = proxy_url
    # NOTE strict is always set to True
    # we do not allow overriding of the source_address
    connection = PulpConnection(host, None, scheme, True, timeout, None,
                                key_file, cert_file, ca_cert_file, verify_host,
                                is_proxy)
    return connection

# -- utility methods -----------------------------------------------------------

def build_proxy_url(proxy_url, proxy_port, proxy_username=None, proxy_password=None):
    """
    Build a complete proxy URL out of its component parts.

    Returns a URL string in the form: scheme://username:password@host:port/

    :param proxy_url: proxy URL in the form of scheme://host/
    :type proxy_url: str or None
    :param proxy_port: proxy port number
    :type proxy_port: int or None
    :param proxy_username: username for proxy authentication
    :type proxy_username: str or None
    :param proxy_password: password for proxy authentication
    :type proxy_password: str or None
    :return: full proxy URL
    :rtype: str or None
    """
    if proxy_url is None:
        return None

    proxy_scheme, remainder = urllib.splittype(proxy_url)
    proxy_host, remainder = urllib.splithost(remainder)
    proxy_port = proxy_port or ''

    proxy_auth = ''
    if proxy_username is not None:
        proxy_auth = proxy_username if not proxy_password else ':'.join((proxy_username, proxy_password))

    proxy_url = '%s://%s%s%s/' % (proxy_scheme,
                                  proxy_auth and proxy_auth + '@',
                                  proxy_host,
                                  proxy_port and ':' + str(proxy_port))
    return proxy_url



