import os

from unittest import TestCase

from mock import Mock, patch

from pulp.server.content.web import views as content_views
from pulp.server.content.web.views import ContentView


MODULE = 'pulp.server.content.web.views'


class TestContentView(TestCase):

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
        scheme = 'http'
        host = 'localhost'
        port = 80
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
        environ = {
            'REQUEST_SCHEME': scheme,
            'SERVER_NAME': host,
            'SERVER_PORT': port,
            'REDIRECT_URL': redirect_path,
            'QUERY_STRING': query,
            'REMOTE_ADDR': remote_ip
        }
        request = Mock(environ=environ, path_info=path)
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

        request = Mock(path_info=path)
        request.get_host.return_value = host

        # test
        view = ContentView()
        reply = view.get(request)

        # validation
        allow_access.assert_called_once_with(request.environ, host)
        realpath.assert_called_once_with(path)
        exists.assert_called_once_with('/var/lib/pulp/published/content')
        x_send.assert_called_once_with('/var/lib/pulp/published/content')
        self.assertEqual(reply, x_send.return_value)

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

        request = Mock(path_info=path)
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
        request = Mock(path_info=path)
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

        request = Mock(path_info=path)
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

        request = Mock(path_info=path)
        request.get_host.return_value = host

        # test
        view = ContentView()
        reply = view.get(request)

        # validation
        allow_access.assert_called_once_with(request.environ, host)
        self.assertEqual(reply, forbidden.return_value)
