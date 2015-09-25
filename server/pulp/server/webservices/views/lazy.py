from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.views.generic import View

from pulp.common.config import parse_bool
from pulp.server.lazy.alias import AliasTable
from pulp.server.lazy.url import URL, Key
from pulp.server.config import config as pulp_conf


class RedirectView(View):
    """
    The content redirect view redirects unsatisfied content
    requests to the lazy streamer.

    :ivar alias: An apache alias table.
    :type alias: AliasTable
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
        while path.startswith('/'):
            path = path[1:]
        if scheme:
            scheme = '{p}://'.format(p=scheme)
        if port:
            port = ':{n}'.format(n=port)
        if query:
            query = '?{q}'.format(q=query)
        url = [
            scheme,
            host,
            port,
            base,
            path,
            query
        ]
        return ''.join(url)

    def __init__(self, **kwargs):
        super(RedirectView, self).__init__(**kwargs)
        self.key = Key.load(pulp_conf.get('authentication', 'rsa_key'))
        self.alias = AliasTable()
        self.alias.load()

    def get(self, request):
        """
        Redirected GET request.

        :param request: The WSGI request object.
        :type request: django.core.handlers.wsgi.WSGIRequest
        :return: A redirect or not-found response.
        :rtype: django.http.HttpResponse
        """
        path = request.environ['REDIRECT_URL']
        query = request.environ.get('REDIRECT_QUERY_STRING', '')
        scheme = request.environ['REQUEST_SCHEME']
        host = request.environ['SERVER_NAME']
        port = request.environ['SERVER_PORT']
        enabled = parse_bool(pulp_conf.get('lazy', 'enabled'))
        redirect_host = pulp_conf.get('lazy', 'redirect_host')
        redirect_port = pulp_conf.get('lazy', 'redirect_port')
        redirect_path = pulp_conf.get('lazy', 'redirect_path')
        if enabled:
            redirect = self.urljoin(
                scheme,
                redirect_host or host,
                redirect_port or port,
                redirect_path,
                self.alias.translate(path),
                query)
            url = URL(redirect)
            signed = url.sign(self.key)
            return HttpResponseRedirect(str(signed))
        else:
            return HttpResponseNotFound(path)
