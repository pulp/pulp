import os
from pulp.server.content.web import wsgi


def application(environ, start_response):
    """
    WSGI application which shows repoview if it exists.

    :param environ: WSGI environment
    :type  environ: dict
    :param start_response: callable that starts HTTP response
    :type  start_response: callable
    :return: message body
    :rtype: iterable
    """
    index_html_relative_path = 'repoview/index.html'
    index_html_absolute_path = os.path.join(environ['PATH_INFO'], index_html_relative_path)
    if os.path.exists(index_html_absolute_path):
        scheme = environ['wsgi.url_scheme']
        port = ''
        is_custom_http_port = scheme == 'http' and environ['SERVER_PORT'] != 80
        is_custom_https_port = scheme == 'https' and environ['SERVER_PORT'] != 443
        if is_custom_http_port or is_custom_https_port:
            port = ':' + environ['SERVER_PORT']
        hostname = environ.get('HTTP_HOST', environ['SERVER_NAME'])
        index_html_path = os.path.join(environ['REQUEST_URI'], index_html_relative_path)
        index_html_url = '%(scheme)s://%(hostname)s%(port)s%(index_html_path)s' % \
            {'scheme': scheme, 'port': port, 'hostname': hostname,
             'index_html_path': index_html_path}
        start_response('302 Moved Temporarily', [('Location', index_html_url)])
        return []
    return wsgi.application(environ, start_response)
