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
import urllib2


HTTP_SCHEME = 'http'
HTTPS_SCHEME = 'https'


# multiple inheritance is to shut PyCharm up about these not being derived from Exception
class InvalidHostSSLCertificate(urllib2.URLError, Exception): pass
class ProxyConnectionFailed(urllib2.URLError, Exception): pass

# -- http downloader connection class ------------------------------------------

class HTTPDownloaderConnection(object):
    """
    Connection class that handles the HTTP and HTTPS protocols for direct and
    proxied connections.
    """

    _ports = {HTTP_SCHEME: httplib.HTTP_PORT, HTTPS_SCHEME: httplib.HTTPS_PORT}

    def __init__(self,
                 scheme,
                 host,
                 port=None,
                 key_file=None,
                 cert_file=None,
                 ca_cert_file=None,
                 validate_host=True,
                 proxy_scheme=None,
                 proxy_host=None,
                 proxy_port=None,
                 proxy_user=None,
                 proxy_password=None,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT):

        assert scheme in (HTTP_SCHEME, HTTPS_SCHEME)
        assert proxy_scheme in (None, HTTP_SCHEME, HTTPS_SCHEME)

        self._scheme = scheme
        self._host = host
        self._port = port

        self._key_file = key_file
        self._cert_file = cert_file
        self._ca_cert_file = ca_cert_file
        self._validate_host = validate_host

        self._proxy_scheme = proxy_scheme
        self._proxy_host = proxy_host
        self._proxy_port = proxy_port
        self._proxy_user = proxy_user
        self._proxy_password = proxy_password

        self._timeout = timeout
        self._connection = None

    # -- properties in the various formats expected by networking APIs ---------

    @property
    def url(self):
        return '%s://%s' % (self._scheme, self.host)

    @property
    def host(self):
        if not self._port:
            return self._host
        return ':'.join((self._host, str(self._port)))

    @property
    def server(self):
        if ':' not in self._host:
            return self._host
        return self._host.split(':', 1)[0]

    @property
    def port(self):
        if self._port:
            return int(self._port)
        if ':' in self._host:
            return int(self._host.rsplit(':', 1)[-1])
        return self._ports[self._scheme]

    @property
    def proxy_url(self):
        if self._proxy_host is None:
            return None
        return '%s://%s' % (self._proxy_scheme, self.proxy_host)

    @property
    def proxy_host(self):
        if self._proxy_host is None:
            return None
        credentials = ''
        if self.proxy_credentials is not None:
            credentials = self.proxy_credentials + '@'
        if not self._proxy_port:
            return credentials + self._proxy_host
        return credentials + ':'.join((self._proxy_host, str(self._proxy_port)))

    @property
    def proxy_server(self):
        if self._proxy_host is None:
            return None
        if ':' not in self._proxy_host:
            return self._proxy_host
        return self._proxy_host.split(':', 1)[0]

    @property
    def proxy_port(self):
        if self._proxy_host is None:
            return None
        if self._proxy_port:
            return int(self._proxy_port)
        if ':' in self._proxy_host:
            return int(self._proxy_host.rsplit(':', 1)[-1])
        return self._ports[self._proxy_scheme]

    @property
    def proxy_credentials(self):
        if None in (self._proxy_host, self._proxy_user):
            return None
        if self._proxy_password is None:
            return self._proxy_user
        return ':'.join((self._proxy_user, self._proxy_password))

    # -- connection management -------------------------------------------------

    def connect(self):

        if self._scheme == HTTPS_SCHEME and self._validate_host:
            self._validate_host()

        # proxied connection
        if self.proxy_host is not None:
            self._connection = self._proxy_connection()

        # direct connection
        else:
            self._connection = self._direct_connection()

        self._connection.connect()

    def close(self):
        if self._connection is None:
            return

        self._connection.close()
        self._connection = None

    # -- connection utilities --------------------------------------------------

    def _validate_host(self):
        try:
            ssl.get_server_certificate((self.server, self.port), ca_certs=self._ca_cert_file)

        except ssl.SSLError:
            raise InvalidHostSSLCertificate('Cannot verify host <%s> with ca cert: %s' %
                                            (self.host, str(self._ca_cert_file)))

    def _direct_connection(self):
        if self._scheme == HTTP_SCHEME:
            return self._http_direct_connection()

        # HTTPS_SCHEME
        return self._https_direct_connection()

    def _proxy_connection(self):
        if self._proxy_scheme == HTTP_SCHEME:
            return self._http_proxy_connection()

        # HTTPS_SCHEME
        return self._https_proxy_connection()

    def _http_direct_connection(self):
        connection = httplib.HTTPConnection(self.url, timeout=self._timeout)
        return connection

    def _https_direct_connection(self):
        connection = httplib.HTTPSConnection(self.url, key_file=self._key_file,
                                             cert_file=self._cert_file, timeout=self._timeout)
        return connection

    def _http_proxy_connection(self):
        connection = httplib.HTTPConnection(self.proxy_url, timeout=self._timeout)
        self._complete_proxy_connection(connection)
        return connection

    def _https_proxy_connection(self):
        connection = httplib.HTTPSConnection(self.proxy_url, timeout=self._timeout)
        self._complete_proxy_connection(connection)
        return connection

    def _complete_proxy_connection(self, connection):
        self._send_proxy_connect_request(connection)

        if self._scheme == HTTP_SCHEME:
            return

        # HTTPS_SCHEME
        self._ssl_wrap_connection_socket(connection)

    def _send_proxy_connect_request(self, connection):
        connection.send('CONNECT %s:%d HTTP/1.0\r\n\r\n' % (self.server, self.port))

        # expect a HTTP/1.0 200 Connection established
        response = connection.response_class(connection.sock, method=connection._method)
        version, code, message = response._read_status()

        if code != httplib.OK:
            connection.close()
            raise ProxyConnectionFailed('Proxy connection to <%s> failed: %d %s' %
                                        (self.proxy_url, code, message.strip()))

        while True:
            line = response.fp.readline()
            if line == '\r\n': break

    def _ssl_wrap_connection_socket(self, connection):
        if None in (self._key_file, self._cert_file):
            return

        ssl_sock = ssl.wrap_socket(connection.sock, self._key_file, self._cert_file)
        connection.sock = ssl_sock

    # -- request/response methods ----------------------------------------------

    def request(self, method, url, body=None, headers=None):
        self.close()
        self.connect()
        headers = headers or {}
        return self._connection.request(method, url, body, headers)

    def getresponse(self, buffering=False):
        assert self._connection is not None
        return self._connection.getresponse(buffering=buffering)

# -- http downloader handler ---------------------------------------------------

class HTTPDownloaderHandler(urllib2.HTTPHandler,
                            urllib2.HTTPSHandler,
                            urllib2.ProxyHandler):
    """
    urllib2 Handler class

    This class replaces the default HTTPHandler, HTTPSHandler, and ProxyHandler,

    It allows proxied HTTP and HTTPS requests as well as SSL validation.
    """

    def __init__(self,
                 key_file=None,
                 cert_file=None,
                 ca_cert_file=None,
                 validate_host=True,
                 proxy_scheme=None,
                 proxy_server=None,
                 proxy_port=None,
                 proxy_user=None,
                 proxy_password=None,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT):

        urllib2.HTTPHandler.__init__(self)
        urllib2.HTTPSHandler.__init__(self)
        urllib2.ProxyHandler.__init__(self, {}) # <- proxy info in connection

        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_cert_file = ca_cert_file
        self.validate_host = validate_host

        self.proxy_scheme = proxy_scheme
        self.proxy_server = proxy_server
        self.proxy_port = proxy_port
        self.proxy_user = proxy_user
        self.proxy_password = proxy_password

        self.timeout = timeout

    # -- handler chain methods -------------------------------------------------

    def default_open(self, req):
        # there is no *default* open
        return None

    def http_open(self, req):
        if req.get_type() != HTTP_SCHEME:
            return None

        kwargs = {'scheme': HTTP_SCHEME}
        kwargs.update(self._common_kwargs())

        factory = functools.partial(http_downloader_connection_factory, **kwargs)
        return self.do_open(factory, req)

    def https_open(self, req):
        if req.get_type() != HTTPS_SCHEME:
            return None

        kwargs = {'scheme': HTTPS_SCHEME}
        kwargs.update(self._common_kwargs())

        factory = functools.partial(http_downloader_connection_factory, **kwargs)
        return self.do_open(factory, req)

    def proxy_open(self, req, proxy, scheme):
        # proxied connections are not handled here, but are automatically
        # handled by the http downloader connection class.
        return None

    # -- handler utilities -----------------------------------------------------

    def _common_kwargs(self):
        kwargs = {'key_file': self.key_file,
                  'cert_file': self.cert_file,
                  'ca_cert_file': self.ca_cert_file,
                  'validate_host': self.validate_host,
                  'proxy_scheme': self.proxy_scheme,
                  'proxy_host': self.proxy_server,
                  'proxy_port': self.proxy_port,
                  'proxy_user': self.proxy_user,
                  'proxy_password': self.proxy_password,
                  'timeout': self.timeout,}
        return kwargs

# -- http downloader connection factory method ---------------------------------

def http_downloader_connection_factory(host, **kwargs):
    kwargs['host'] = host
    connection = HTTPDownloaderConnection(**kwargs)
    return connection


