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
import sys
import urllib
import urllib2


HTTP_SCHEME = 'http'
HTTPS_SCHEME = 'https'


# multiple inheritance is to shut PyCharm up about not being derived from Exception
class InvalidHostSSLCertificate(urllib2.URLError, Exception): pass
class ProxyConnectionFailed(urllib2.URLError, Exception): pass

# -- pulp connection class -----------------------------------------------------

class PulpConnection(httplib.HTTPSConnection):

    _ports = {HTTP_SCHEME: httplib.HTTP_PORT, HTTPS_SCHEME: httplib.HTTPS_PORT}

    def __init__(self, host, port=None, scheme=HTTP_SCHEME, strict=None,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None,
                 key_file=None, cert_file=None, ca_cert_file=None, validate_host=True,
                 is_proxy=False):

        assert scheme in (HTTP_SCHEME, HTTPS_SCHEME)

        httplib.HTTPSConnection.__init__(self, host, port, key_file, cert_file,
                                         strict, timeout, source_address)

        self.ca_cert_file = ca_cert_file
        self.validate_host = validate_host

        self.is_proxy = is_proxy
        # will be changed in the request if connection is a proxy
        self._real_host = self.host
        self._real_port = self.port

        self.scheme = scheme

    @property
    def default_port(self):
        return self._ports[self.scheme]

    def request(self, method, url, body=None, headers=None):
        headers = headers or {}
        protocol, remainder = urllib.splittype(url)

        if protocol not in (HTTP_SCHEME, HTTPS_SCHEME):
            raise ValueError('Unsupported URL protocol: %s' % url)

        if self.is_proxy:
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

        if self.scheme == HTTP_SCHEME:
            httplib.HTTPConnection.connect(self)

        else: # HTTPS_SCHEME
            self._validate_server_ssl_cert()
            self._ssl_wrap_socket()
            return httplib.HTTPSConnection.connect(self)

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

        # XXX (jconnor 2013-04-12) I don't think I need to do this unless we're
        # proxying an https request via an http proxy

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

        if code != 200:
            self.close()
            raise ProxyConnectionFailed('Proxy connection failed: %d %s' % (code, message.strip()))

        while True:
            line = response.fp.readline()
            if line == '\r\n': break

# -- pulp handler --------------------------------------------------------------

class PulpHandler(urllib2.HTTPHandler,
                  urllib2.HTTPSHandler,
                  urllib2.ProxyHandler):

    def __init__(self, key_file=None, cert_file=None, ca_cert_file=None,
                 verify_host=False, proxy_url=None, proxy_port=None,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT):

        proxies = {}

        urllib2.HTTPHandler.__init__(self)
        urllib2.HTTPSHandler.__init__(self)
        urllib2.ProxyHandler.__init__(self, proxies)

        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_cert_file = ca_cert_file
        self.verify_host = verify_host

        self.proxy_url = proxy_url
        self.proxy_port = proxy_port

        self.timeout = timeout

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
        #req.set_proxy(proxy)
        kwargs = {'scheme': scheme,
                  'is_proxy': True,
                  'timeout': self.timeout}
        factory = functools.partial(pulp_connection_factory, **kwargs)
        return self.do_open(factory, req)


def pulp_connection_factory(req, scheme, key_file=None, cert_file=None, ca_cert_file=None,
                            verify_host=False, is_proxy=False, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,):
    # NOTE strict is always set to True; and we do not allow overriding of the
    # source_address: always None
    connection = PulpConnection(req.host, req.port, scheme, True, timeout, None,
                                key_file, cert_file, ca_cert_file, verify_host, is_proxy)
    return connection









































# these have to be defined elsewhere, but I'm too lazy to go digging around
HTTP_PORT = 80
HTTPS_PORT = 443

class CannotVerifyHost(urllib2.URLError): pass

# http://stackoverflow.com/questions/1875052/using-paired-certificates-with-urllib2
# http://bugs.python.org/issue3466

class PulpHandler(urllib2.HTTPHandler,
                  urllib2.HTTPSHandler,
                  urllib2.ProxyHandler):

    def __init__(self, key_file, cert_file, ca_cert_file=None, verify_host=False, verified_host_cache=None, timeout=300):

        urllib2.HTTPSHandler.__init__(self)

        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_cert_file = ca_cert_file

        self.verify_host = verify_host
        if verified_host_cache is None:
            verified_host_cache = {}
        self.verified_host_cache = verified_host_cache

        self.timeout = timeout

    def http_open(self, req):
        pass

    def https_open(self, req):

        # Rather than pass in a reference to a connection class, we pass in
        # a reference to a function which, for all intents and purposes,
        # will behave as a constructor
        return self.do_open(self.http_class_factory, req)

    def proxy_open(self, req, proxy, type):
        pass

    def http_class_factory(self, host):

        self._verify_host(host)

        return httplib.HTTPSConnection(host,
                                       key_file=self.key_file,
                                       cert_file=self.cert_file,
                                       timeout=self.timeout)

    def _verify_host(self, host):
        if not self.verify_host:
            return

        cannot_verify_host_error = CannotVerifyHost('Cannot verify host <%s> with ca cert file: %s' %
                                                    (host, self.ca_cert_file))

        if host in self.verified_host_cache:
            if self.verified_host_cache[host]:
                return
            raise cannot_verify_host_error

        if ':' not in host:
            port = 443
        else:
            port = int(host.rsplit(':', 1)[-1])

        try:
            # this will raise an ssl.SSLError exception if the cert is invalid
            ssl.get_server_certificate((host, port), ca_certs=self.ca_cert_file)

        except ssl.SSLError:
            self.verified_host_cache[host] = False
            raise cannot_verify_host_error, None, sys.exc_info()[2]

        else:
            self.verified_host_cache[host] = True

# -- proxy server utilities ----------------------------------------------------

# http://code.activestate.com/recipes/456195/ (r2)
# urllib2 opener to connection through a proxy using the CONNECT method, (useful for SSL)
# tested with python 2.4

class ProxyHTTPConnection(httplib.HTTPConnection):

    _ports = {'http': HTTP_PORT, 'https': HTTPS_PORT}

    def request(self, method, url, body=None, headers=None):

        headers = headers or {}
        protocol, rest = urllib.splittype(url)

        if protocol is None:
            raise ValueError("Unknown URL type: %s" % url)

        host, rest = urllib.splithost(rest)
        host, port = urllib.splitport(host)

        if port is None:
            try:
                port = self._ports[protocol]

            except KeyError:
                raise ValueError("Unknown protocol for: %s" % url)

        self._real_host = host
        self._real_port = port

        httplib.HTTPConnection.request(self, method, url, body, headers)


    def connect(self):

        httplib.HTTPConnection.connect(self)

        # send proxy CONNECT request
        self.send("CONNECT %s:%d HTTP/1.0\r\n\r\n" % (self._real_host, self._real_port))

        # expect a HTTP/1.0 200 Connection established
        response = self.response_class(self.sock, strict=self.strict, method=self._method)
        (version, code, message) = response._read_status()

        if code != 200:
            self.close()
            raise socket.error("Proxy connection failed: %d %s" % (code, message.strip()))

        while True:
            line = response.fp.readline()
            if line == '\r\n': break


class ProxyHTTPSConnection(ProxyHTTPConnection):

    default_port = HTTPS_PORT

    def __init__(self, host, port = None, key_file = None, cert_file = None, strict = None):

        ProxyHTTPConnection.__init__(self, host, port)

        self.key_file = key_file
        self.cert_file = cert_file

    def connect(self):

        ProxyHTTPConnection.connect(self)

        # make the sock ssl-aware
        ssl = socket.ssl(self.sock, self.key_file, self.cert_file)
        self.sock = httplib.FakeSocket(self.sock, ssl)


class ConnectHTTPHandler(urllib2.HTTPHandler):

    def __init__(self, proxy=None, debuglevel=0):

        self.proxy = proxy

        urllib2.HTTPHandler.__init__(self, debuglevel)

    def do_open(self, http_class, req):

        if self.proxy is not None:
            req.set_proxy(self.proxy, 'http')

        return urllib2.HTTPHandler.do_open(self, ProxyHTTPConnection, req)


class ConnectHTTPSHandler(urllib2.HTTPSHandler):

    def __init__(self, proxy=None, debuglevel=0):

        self.proxy = proxy

        urllib2.HTTPSHandler.__init__(self, debuglevel)

    def do_open(self, http_class, req):

        if self.proxy is not None:
            req.set_proxy(self.proxy, 'https')

        return urllib2.HTTPSHandler.do_open(self, ProxyHTTPSConnection, req)


