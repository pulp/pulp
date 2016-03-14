import os

from unittest import TestCase

from mock import Mock, patch

from pulp.server.content.web import views as content_views
from pulp.server.content.web.views import ContentView


MODULE = 'pulp.server.content.web.views'


class TestContentView(TestCase):

    def setUp(self):
        self.environ = {
            # These values must be present in all requests unless they are
            # allowed to be empty strings
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',  # Always present
            'PATH_INFO': '/var/www/pub/yum/http/repos/repos/pulp/pulp/demo_repos/zoo/',
            'QUERY_STRING': '',  # May or may not be present
            'SERVER_NAME': 'dev.example.com',
            'SERVER_PORT': '443',
            'SERVER_PROTOCOL': 'HTTP/1.1',

            # These represent client-supplied HTTP headers
            'HTTP_USER_AGENT': 'Average Joe/1.0 (Wayland; Fedora; Linux x86_64)',
            'HTTP_CONNECTION': 'keep-alive',
            'HTTP_DNT': '1',
            'HTTP_HOST': 'dev.example.com',
            'HTTP_ACCEPT': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'HTTP_ACCEPT_LANGUAGE': 'en-US,en;q=0.5',
            'HTTP_ACCEPT_ENCODING': 'gzip, deflate',

            # These 'wsgi' variables are required by the WSGI standard.
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'https',
            'wsgi.input': Mock(),  # File-like object representing the request body
            'wsgi.errors': Mock(),  # File-like object which errors can be written to.
            'wsgi.multithread': True,
            'wsgi.multiprocess': True,
            'wsgi.run_once': False,
        }

    @patch(MODULE + '.pulp_conf')
    @patch(MODULE + '.Key.load')
    def test_init(self, key_load, pulp_conf):
        key_path = '/tmp/rsa.key'
        conf = {
            'authentication': {
                'rsa_key': key_path
            }
        }

        pulp_conf.get.side_effect = lambda s, p: conf.get(s).get(p)

        # test
        ContentView()

        # validation
        key_load.assert_called_once_with(key_path)

    @patch(MODULE + '.Key.load', Mock())
    def test_urljoin(self):
        scheme = 'http'
        host = 'redhat.com'
        port = 123
        base = 'http://host'  # no trailing /
        path = '/my/path/'    # absolute path
        query = 'age=10'
        joined = ContentView.urljoin(scheme, host, port, base, path, query)
        self.assertEqual(joined, 'http://redhat.com:123http://host/my/path/?age=10')

    @patch('os.access')
    def test_x_send(self, access):
        path = '/my/path'
        access.return_value = True
        reply = ContentView.x_send(path)
        access.assert_called_once_with(path, os.R_OK)
        self.assertEqual(reply['X-SENDFILE'], path)
        self.assertEqual(reply['Content-Type'], 'application/octet-stream')

    @patch('os.access')
    def test_x_send_mime_type(self, access):
        path = '/my/path.rpm'
        access.return_value = True
        reply = ContentView.x_send(path)
        access.assert_called_once_with(path, os.R_OK)
        self.assertEqual(reply['X-SENDFILE'], path)
        self.assertEqual(reply['Content-Type'], 'application/x-rpm')

    @patch('os.access')
    @patch(MODULE + '.HttpResponseForbidden')
    def test_x_send_cannot_read(self, forbidden, access):
        path = '/my/path'
        access.return_value = False
        reply = ContentView.x_send(path)
        access.assert_called_once_with(path, os.R_OK)
        forbidden.assert_called_once_with()
        self.assertEqual(reply, forbidden.return_value)

    @patch(MODULE + '.URL')
    @patch(MODULE + '.pulp_conf')
    @patch(MODULE + '.HttpResponseRedirect')
    def test_redirect(self, redirect, pulp_conf, url):
        remote_ip = '172.10.08.20'
        scheme = 'https'
        host = 'localhost'
        port = 443
        path = '/var/pulp/content/zoo/lion'
        redirect_path = '/streamer'
        query = 'arch=x86'
        conf = {
            'authentication': {
                'rsa_key': '/tmp/key'
            },
            'lazy': {
                'enabled': 'true',
                'redirect_host': host,
                'redirect_port': port,
                'redirect_path': redirect_path,
            }
        }
        pulp_conf.get.side_effect = lambda s, p: conf.get(s).get(p)
        self.environ['QUERY_STRING'] = query
        self.environ['REMOTE_ADDR'] = remote_ip
        request = Mock(environ=self.environ, path_info=path)
        key = Mock()

        # test
        reply = ContentView.redirect(request, key)

        # validation
        url.assert_called_once_with(ContentView.urljoin(
            scheme, host, port, redirect_path, path, query))
        url.return_value.sign.assert_called_once_with(key, remote_ip=remote_ip)
        redirect.assert_called_once_with(str(url.return_value.sign.return_value))
        self.assertEqual(reply, redirect.return_value)

    @patch('os.path.lexists', Mock(return_value=True))
    @patch('os.path.realpath')
    @patch('os.path.exists')
    @patch(MODULE + '.allow_access')
    @patch(MODULE + '.ContentView.x_send')
    @patch(MODULE + '.Key.load', Mock())
    def test_get_x_send(self, x_send, allow_access, exists, realpath):
        allow_access.return_value = True
        exists.return_value = True
        realpath.side_effect = lambda p: '/var/lib/pulp/published/content'

        host = 'localhost'
        path = '/var/www/pub/content'

        request = Mock(path_info=path, environ=self.environ)
        request.get_host.return_value = host

        # test
        view = ContentView()
        reply = view.get(request)

        # validation
        allow_access.assert_called_once_with(request.environ, host)
        realpath.assert_called_once_with(path)
        x_send.assert_called_once_with('/var/lib/pulp/published/content')
        self.assertEqual(reply, x_send.return_value)

    @patch(MODULE + '.Key.load', Mock())
    @patch(MODULE + '.allow_access')
    @patch('os.path.realpath')
    def test_get_http(self, realpath, allow_access):
        realpath.side_effect = lambda p: '/some/content'
        host = 'localhost'
        path = '/some/content/'
        self.environ['wsgi.url_scheme'] = 'http'

        request = Mock(path_info=path, environ=self.environ)
        request.get_host.return_value = host

        # test
        view = ContentView()
        view.get(request)
        self.assertEqual(0, allow_access.call_count)

    @patch('os.path.lexists', Mock(return_value=True))
    @patch('os.path.realpath')
    @patch('os.path.exists')
    @patch(MODULE + '.pulp_conf.get', return_value='True')
    @patch(MODULE + '.allow_access')
    @patch(MODULE + '.ContentView.redirect')
    @patch(MODULE + '.Key.load', Mock())
    def test_get_redirected(self, redirect, allow_access, mock_conf_get, exists, realpath):
        allow_access.return_value = True
        exists.return_value = False
        realpath.side_effect = lambda p: '/var/lib/pulp/content/rpm'

        host = 'localhost'
        path = '/var/www/pub/content'

        request = Mock(path_info=path, environ=self.environ)
        request.get_host.return_value = host

        # test
        view = ContentView()
        reply = view.get(request)

        # validation
        allow_access.assert_called_once_with(request.environ, host)
        realpath.assert_called_once_with(path)
        exists.assert_has_call('/var/lib/pulp/content/rpm')
        self.assertTrue(exists.call_count > 0)
        redirect.assert_called_once_with(request, view.key)
        self.assertEqual(reply, redirect.return_value)

    @patch('os.path.lexists', Mock(return_value=False))
    @patch('os.path.realpath', Mock())
    @patch(MODULE + '.allow_access', Mock(return_value=True))
    @patch(MODULE + '.Key.load', Mock())
    @patch(MODULE + '.pulp_conf')
    def test_get_not_found(self, pulp_conf):
        host = 'localhost'
        path = '/var/lib/pulp/published/content'
        request = Mock(path_info=path, environ=self.environ)
        request.get_host.return_value = host
        conf = {
            'authentication': {
                'rsa_key': '/tmp/key'
            },
        }
        pulp_conf.get.side_effect = lambda s, p: conf.get(s).get(p)

        # test
        view = ContentView()
        self.assertRaises(content_views.Http404, view.get, request)

    @patch(MODULE + '.allow_access')
    @patch(MODULE + '.HttpResponseForbidden')
    @patch(MODULE + '.Key.load', Mock())
    def test_get_not_authorized(self, forbidden, allow_access):
        allow_access.return_value = False

        host = 'localhost'
        path = '/var/lib/pulp/published/content'

        request = Mock(path_info=path, environ=self.environ)
        request.get_host.return_value = host

        # test
        view = ContentView()
        reply = view.get(request)

        # validation
        allow_access.assert_called_once_with(request.environ, host)
        self.assertEqual(reply, forbidden.return_value)

    @patch(MODULE + '.allow_access')
    @patch(MODULE + '.HttpResponseForbidden')
    @patch(MODULE + '.Key.load', Mock())
    def test_get_outside_pub(self, forbidden, allow_access):
        allow_access.return_value = True

        host = 'localhost'
        path = '/etc/pki/tls/private/myprecious.key'

        request = Mock(path_info=path, environ=self.environ)
        request.get_host.return_value = host

        # test
        view = ContentView()
        reply = view.get(request)

        # validation
        allow_access.assert_called_once_with(request.environ, host)
        self.assertEqual(reply, forbidden.return_value)
