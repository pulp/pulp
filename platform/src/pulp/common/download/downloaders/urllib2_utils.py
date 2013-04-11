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

import httplib
import socket
import ssl
import sys
import urllib
import urllib2


HTTP_SCHEME = 'http'
HTTPS_SCHEME = 'https'


class InvalidHostSSLCertificate(urllib2.URLError): pass



class PulpConnection(httplib.HTTPSConnection):

    _ports = {'http': httplib.HTTP_PORT, 'https': httplib.HTTPS_PORT}

    def __init__(self, host, port=None, strict=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None,
                 key_file=None, cert_file=None, ca_cert_file=None, validate_host=True,
                 proxy_host=None, proxy_port=None, scheme='http'):

        httplib.HTTPSConnection.__init__(self, host, port, key_file, cert_file, strict, timeout, source_address)

        self.ca_cert_file = ca_cert_file
        self.validate_host = validate_host
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.scheme = scheme

    @property
    def default_port(self):
        return self._ports[self.scheme]

    def connect(self):
        if self.scheme == HTTP_SCHEME:
            return httplib.HTTPConnection.connect(self)
        self._validate_server_ssl_cert()
        return httplib.HTTPSConnection.connect(self)

    def _validate_server_ssl_cert(self):
        if not self.validate_host:
            return

        try:
            ssl.get_server_certificate((self.host, self.port))

        except ssl.SSLError:
            raise InvalidHostSSLCertificate('Cannot verify host <%s> with ca cert: %s' %
                                            (self.host, self.ca_cert_file))











































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


