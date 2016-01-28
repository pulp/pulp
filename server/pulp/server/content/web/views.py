import os

from django.http import \
    HttpResponse, HttpResponseRedirect, HttpResponseNotFound, HttpResponseForbidden
from django.views.generic import View

from pulp.common.config import parse_bool
from pulp.repoauth.wsgi import allow_access
from pulp.server.lazy import URL, Key
from pulp.server.config import config as pulp_conf


class ContentView(View):
    """
    The content delivery view provides content.

    :ivar key: The public RSA key used for URL signing.
    :type key: M2Crypto.RSA.RSA
    """

    @staticmethod
    def urljoin(scheme, host, port, base, path, query):
        """
        Join a base URL and path component.

        :param scheme: The URL scheme component.
        :type scheme: str
        :param host: The URL host component.
        :type host: str
        :param port: The URL port component.
        :type port: int
        :param base: A base URL.
        :type base: str
        :param path: A URL path component.
        :type path: str
        :param query: A URL query component.
        :type query: str
        :return: The joined URL.
        :rtype: str
        """
        if not base.endswith('/'):
            base += '/'
        path = path.lstrip('/')
        if scheme:
            scheme = '{p}://'.format(p=scheme)
        if port:
            port = ':{n}'.format(n=port)
        if query:
            query = '?{q}'.format(q=query)
        url = [
            scheme,
            host,
            str(port),
            base,
            path,
            query
        ]
        return ''.join(url)

    @staticmethod
    def x_send(path):
        """
        Add the X-SENDFILE header to the returned reply causing Apache to send the file content.

        :param path: The fully qualified *real* path to the requested content.
        :type path: str
        :return: An HTTP response.
        :rtype: django.http.HttpResponse
        """
        if os.access(path, os.R_OK):
            reply = HttpResponse()
            reply['X-SENDFILE'] = path
        else:
            reply = HttpResponseForbidden()
        return reply

    @staticmethod
    def redirect(request, key):
        """
        Redirected GET request.

        :param request: The WSGI request object.
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param key: A private RSA key.
        :type key: RSA.RSA
        :return: A redirect or not-found reply.
        :rtype: django.http.HttpResponse
        """
        path = os.path.realpath(request.path_info)
        scheme = request.environ['REQUEST_SCHEME']
        host = request.environ['SERVER_NAME']
        port = request.environ['SERVER_PORT']
        query = request.environ['QUERY_STRING']
        remote_ip = request.environ['REMOTE_ADDR']

        redirect_host = pulp_conf.get('lazy', 'redirect_host')
        redirect_port = pulp_conf.get('lazy', 'redirect_port')
        redirect_path = pulp_conf.get('lazy', 'redirect_path')

        redirect = ContentView.urljoin(
            scheme,
            redirect_host or host,
            redirect_port or port,
            redirect_path,
            path,
            query)

        url = URL(redirect)
        signed = url.sign(key, remote_ip=remote_ip)
        return HttpResponseRedirect(str(signed))

    def __init__(self, **kwargs):
        super(ContentView, self).__init__(**kwargs)
        self.key = Key.load(pulp_conf.get('authentication', 'rsa_key'))

    def get(self, request):
        """
        Process the GET content request.

        :param request: The WSGI request object.
        :type request: django.core.handlers.wsgi.WSGIRequest
        :return: An appropriate HTTP reply
        :rtype: django.http.HttpResponse
        """
        host = request.get_host()
        path = os.path.realpath(request.path_info)
        lazy_enabled = parse_bool(pulp_conf.get('lazy', 'enabled'))

        # Authorization
        if not allow_access(request.environ, host):
            # Not Authorized
            return HttpResponseForbidden()

        # Immediately 404 if the symbolic link doesn't even exist
        if not os.path.lexists(request.path_info):
            return HttpResponseNotFound(request.path_info)

        # Already downloaded
        if os.path.exists(path):
            return self.x_send(path)

        # Redirect if lazy is on
        if lazy_enabled:
            return self.redirect(request, self.key)

        # NotFound
        return HttpResponseNotFound(request.path_info)
