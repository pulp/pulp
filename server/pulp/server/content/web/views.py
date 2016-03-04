from gettext import gettext as _
import logging
import mimetypes
import os

from django.http import \
    HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import render_to_response
from django.views.generic import View

from pulp.repoauth.wsgi import allow_access
from pulp.server.lazy import URL, Key
from pulp.server.config import config as pulp_conf


logger = logging.getLogger(__name__)

# Make sure all requested paths fall under these directories.
PUBLISH_DIR = '/var/lib/pulp/published'
CONTENT_DIR = '/var/lib/pulp/content'


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
            content_type = mimetypes.guess_type(path)[0]
            # If the content type can't be detected by mimetypes, send it as arbitrary
            # binary data. See https://tools.ietf.org/html/rfc2046#section-4.5.1 for
            # more information.
            if content_type is None:
                content_type = 'application/octet-stream'
            reply = HttpResponse(content_type=content_type)
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
        scheme = request.environ['wsgi.url_scheme']
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

        # Check authorization if http isn't being used. This environ variable must
        # be available in all implementations so it is not dependant on Apache httpd:
        # https://www.python.org/dev/peps/pep-0333/#environ-variables
        if request.environ['wsgi.url_scheme'] != 'http':
            if not allow_access(request.environ, host):
                # Not Authorized
                logger.info(_('Denying {host} access to {path} because one or more'
                              ' authenticators failed.').format(host=host, path=path))
                return HttpResponseForbidden()

        if not path.startswith(PUBLISH_DIR) and not path.startswith(CONTENT_DIR):
            # Someone is requesting something they shouldn't.
            logger.debug(_('Denying {host} request to {path} as it does not resolve to'
                           'a Pulp content path.').format(host=host, path=path))
            return HttpResponseForbidden()

        # Immediately 404 if the symbolic link doesn't even exist
        if not os.path.lexists(request.path_info):
            logger.debug(_('Symbolic link to {path} does not exist.').format(path=path))
            raise Http404

        if os.path.isdir(path):
            logger.debug(_('Rendering directory index for {path}.').format(path=path))
            return self.directory_index(path)

        # Already downloaded
        if os.path.exists(path):
            logger.debug(_('Serving {path} with mod_xsendfile.').format(path=path))
            return self.x_send(path)

        logger.debug(_('Redirecting request for {path}.').format(path=path))
        return self.redirect(request, self.key)

    @staticmethod
    def directory_index(path):
        """
        Render the given path to a directory index.

        :param path: Absolute path to the directory to list.
        :type  path: str

        :return: HttpResponse
        """
        listing = os.listdir(path)
        context = {
            'dirs': sorted([f for f in listing if os.path.isdir(os.path.join(path, f))]),
            'files': sorted([f for f in listing if os.path.isfile(os.path.join(path, f))]),
        }
        return render_to_response('directory_index.html', context)
