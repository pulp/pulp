# -*- coding: utf-8 -*-
"""
This module contains a subclass of the Requests HTTP adapter. It overrides a few
methods from the parent class in order to address[0] an issue with updating SSL
configuration. Once the patch for #2863 is merged into upstream and available on
plaforms we support this module should be removed and Pulp should use the default
HTTP adapter.

Be aware that this adapter is _not_ API-compatible with the 2.y series of Requests.

[0] https://github.com/kennethreitz/requests/issues/2863
"""

import os.path
import socket
try:
    from threading import RLock
except ImportError:  # threading is an optional module and may not be present.
    from dummy_threading import RLock

from requests.adapters import (DEFAULT_POOLBLOCK, DEFAULT_POOLSIZE, DEFAULT_RETRIES,
                               HTTPAdapter)
from requests.packages.urllib3.response import HTTPResponse
from requests.packages.urllib3.util import Timeout as TimeoutSauce
from requests.compat import urlparse, basestring
from requests.structures import CaseInsensitiveDict
from requests.packages.urllib3.exceptions import ClosedPoolError
from requests.packages.urllib3.exceptions import ConnectTimeoutError
from requests.packages.urllib3.exceptions import HTTPError as _HTTPError
from requests.packages.urllib3.exceptions import MaxRetryError
from requests.packages.urllib3.exceptions import ProxyError as _ProxyError
from requests.packages.urllib3.exceptions import ProtocolError
from requests.packages.urllib3.exceptions import ReadTimeoutError
from requests.packages.urllib3.exceptions import SSLError as _SSLError
from requests.packages.urllib3.exceptions import ResponseError
from requests.cookies import extract_cookies_to_jar
from requests.exceptions import (ConnectionError, ConnectTimeout, ReadTimeout, SSLError,
                                 ProxyError, RetryError)
from requests.utils import (DEFAULT_CA_BUNDLE_PATH, get_encoding_from_headers,
                            prepend_scheme_if_needed)
from requests.models import Response


class PulpHTTPAdapter(HTTPAdapter):
    """The built-in HTTP Adapter for urllib3.

    Provides a general-case interface for Requests sessions to contact HTTP and
    HTTPS urls by implementing the Transport Adapter interface. This class will
    usually be created by the :class:`Session <Session>` class under the
    covers.

    :param pool_connections: The number of urllib3 connection pools to cache.
    :param pool_maxsize: The maximum number of connections to save in the pool.
    :param max_retries: The maximum number of retries each connection
        should attempt. Note, this applies only to failed DNS lookups, socket
        connections and connection timeouts, never to requests where data has
        made it to the server. By default, Requests does not retry failed
        connections. If you need granular control over the conditions under
        which we retry a request, import urllib3's ``Retry`` class and pass
        that instead.
    :param pool_block: Whether the connection pool should block for connections.

    Usage::

      >>> import requests
      >>> s = requests.Session()
      >>> a = requests.adapters.HTTPAdapter(max_retries=3)
      >>> s.mount('http://', a)
    """

    def __init__(self, pool_connections=DEFAULT_POOLSIZE,
                 pool_maxsize=DEFAULT_POOLSIZE, max_retries=DEFAULT_RETRIES,
                 pool_block=DEFAULT_POOLBLOCK):
        self._pool_kw_lock = RLock()
        super(PulpHTTPAdapter, self).__init__(pool_connections=pool_connections,
                                              pool_maxsize=pool_maxsize, max_retries=max_retries,
                                              pool_block=pool_block)

    def __setstate__(self, state):
        # Can't handle by adding 'proxy_manager' to self.__attrs__ because
        # self.poolmanager uses a lambda function, which isn't pickleable.
        self.proxy_manager = {}
        self.config = {}
        self._pool_kw_lock = RLock()

        for attr, value in state.items():
            setattr(self, attr, value)

        self.init_poolmanager(self._pool_connections, self._pool_maxsize,
                              block=self._pool_block)

    def _update_poolmanager_ssl_kw(self, verify, cert):
        """Update the :class:`PoolManager <urllib3.poolmanager.PoolManager>`
        connection_pool_kw with the necessary SSL configuration. This method
        should not be called from user code, and is only exposed for use when
        subclassing the :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param verify: Whether we should actually verify the certificate;
                       optionally a path to a CA certificate bundle or
                       directory of CA certificates.
        :param cert: The path to the client certificate and key, if any.
                     This can either be the path to the certificate and
                     key concatenated in a single file, or as a tuple of
                     (cert_file, key_file).
        """
        if verify:

            cert_loc = None

            # Allow self-specified cert location.
            if verify is not True:
                cert_loc = verify

            if not cert_loc:
                cert_loc = DEFAULT_CA_BUNDLE_PATH

            if not cert_loc:
                raise Exception("Could not find a suitable SSL CA certificate bundle.")

            self.poolmanager.connection_pool_kw['cert_reqs'] = 'CERT_REQUIRED'

            if not os.path.isdir(cert_loc):
                self.poolmanager.connection_pool_kw['ca_certs'] = cert_loc
                self.poolmanager.connection_pool_kw['ca_cert_dir'] = None
            else:
                self.poolmanager.connection_pool_kw['ca_cert_dir'] = cert_loc
                self.poolmanager.connection_pool_kw['ca_certs'] = None
        else:
            self.poolmanager.connection_pool_kw['cert_reqs'] = 'CERT_NONE'
            self.poolmanager.connection_pool_kw['ca_certs'] = None
            self.poolmanager.connection_pool_kw['ca_cert_dir'] = None

        if cert:
            if not isinstance(cert, basestring):
                self.poolmanager.connection_pool_kw['cert_file'] = cert[0]
                self.poolmanager.connection_pool_kw['key_file'] = cert[1]
            else:
                self.poolmanager.connection_pool_kw['cert_file'] = cert

    def build_response(self, req, resp):
        """Builds a :class:`Response <requests.Response>` object from a urllib3
        response. This should not be called from user code, and is only exposed
        for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`

        :param req: The :class:`PreparedRequest <PreparedRequest>` used to generate the response.
        :param resp: The urllib3 response object.
        """
        response = Response()

        # Fallback to None if there's no status_code, for whatever reason.
        response.status_code = getattr(resp, 'status', None)

        # Make headers case-insensitive.
        response.headers = CaseInsensitiveDict(getattr(resp, 'headers', {}))

        # Set encoding.
        response.encoding = get_encoding_from_headers(response.headers)
        response.raw = resp
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode('utf-8')
        else:
            response.url = req.url

        # Add new cookies from the server.
        extract_cookies_to_jar(response.cookies, req, resp)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    def get_connection(self, url, proxies=None, verify=None, cert=None):
        """Returns a urllib3 connection for the given URL. This should not be
        called from user code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param url: The URL to connect to.
        :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        """
        with self._pool_kw_lock:
            if url.lower().startswith('https'):
                self._update_poolmanager_ssl_kw(verify, cert)

            # NOTE: This differs from upstream, which factored the proxy select code out into
            # utils and fixed #2722 at the same time. Since that function is missing in 2.6,
            # I've modified this to inline that function.
            proxies = proxies or {}
            urlparts = urlparse(url)
            if urlparts.hostname is None:
                proxy = proxies.get('all', proxies.get(urlparts.scheme))
            else:
                proxy_keys = [
                    'all://' + urlparts.hostname,
                    'all',
                    urlparts.scheme + '://' + urlparts.hostname,
                    urlparts.scheme,
                ]
                proxy = None
                for proxy_key in proxy_keys:
                    if proxy_key in proxies:
                        proxy = proxies[proxy_key]
                        break

            if proxy:
                proxy = prepend_scheme_if_needed(proxy, 'http')
                proxy_manager = self.proxy_manager_for(proxy)
                conn = proxy_manager.connection_from_url(url)
            else:
                # Only scheme should be lower case
                parsed = urlparse(url)
                url = parsed.geturl()
                conn = self.poolmanager.connection_from_url(url)

        return conn

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple
        :param verify: (optional) Whether to verify SSL certificates.
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        """
        conn = self.get_connection(request.url, proxies, verify, cert)

        url = self.request_url(request, proxies)
        self.add_headers(request)

        chunked = not (request.body is None or 'Content-Length' in request.headers)

        if isinstance(timeout, tuple):
            try:
                connect, read = timeout
                timeout = TimeoutSauce(connect=connect, read=read)
            except ValueError as e:
                # this may raise a string formatting error.
                err = ("Invalid timeout {0}. Pass a (connect, read) "
                       "timeout tuple, or a single float to set "
                       "both timeouts to the same value".format(timeout))
                raise ValueError(err)
        else:
            timeout = TimeoutSauce(connect=timeout, read=timeout)

        try:
            if not chunked:
                resp = conn.urlopen(
                    method=request.method,
                    url=url,
                    body=request.body,
                    headers=request.headers,
                    redirect=False,
                    assert_same_host=False,
                    preload_content=False,
                    decode_content=False,
                    retries=self.max_retries,
                    timeout=timeout
                )

            # Send the request.
            else:
                if hasattr(conn, 'proxy_pool'):
                    conn = conn.proxy_pool

                low_conn = conn._get_conn(timeout=None)

                try:
                    low_conn.putrequest(request.method,
                                        url,
                                        skip_accept_encoding=True)

                    for header, value in request.headers.items():
                        low_conn.putheader(header, value)

                    low_conn.endheaders()

                    for i in request.body:
                        low_conn.send(hex(len(i))[2:].encode('utf-8'))
                        low_conn.send(b'\r\n')
                        low_conn.send(i)
                        low_conn.send(b'\r\n')
                    low_conn.send(b'0\r\n\r\n')

                    # Receive the response from the server
                    try:
                        # For Python 2.7+ versions, use buffering of HTTP
                        # responses
                        r = low_conn.getresponse(buffering=True)
                    except TypeError:
                        # For compatibility with Python 2.6 versions and back
                        r = low_conn.getresponse()

                    resp = HTTPResponse.from_httplib(
                        r,
                        pool=conn,
                        connection=low_conn,
                        preload_content=False,
                        decode_content=False
                    )
                except:
                    # If we hit any problems here, clean up the connection.
                    # Then, reraise so that we can handle the actual exception.
                    low_conn.close()
                    raise

        except (ProtocolError, socket.error) as err:
            raise ConnectionError(err, request=request)

        except MaxRetryError as e:
            if isinstance(e.reason, ConnectTimeoutError):
                # NOTE: This differs from the upstream 2.x series; NewConnectionError
                # was introduced after 2.6 to fix issue #2811. RHEL6 and 7 have 2.6, so
                # the fix has been removed here in order to not have to pull in more
                # changes and to maintain compatibility. The end result is that a
                # ConnectTimeout will be raised even when the underlying error isn't a
                # timeout. See requests issues #2811, #2812.
                raise ConnectTimeout(e, request=request)

            if isinstance(e.reason, ResponseError):
                raise RetryError(e, request=request)

            if isinstance(e.reason, _ProxyError):
                raise ProxyError(e, request=request)

            raise ConnectionError(e, request=request)

        except ClosedPoolError as e:
            raise ConnectionError(e, request=request)

        except _ProxyError as e:
            raise ProxyError(e)

        except (_SSLError, _HTTPError) as e:
            if isinstance(e, _SSLError):
                raise SSLError(e, request=request)
            elif isinstance(e, ReadTimeoutError):
                raise ReadTimeout(e, request=request)
            else:
                raise

        return self.build_response(request, resp)
