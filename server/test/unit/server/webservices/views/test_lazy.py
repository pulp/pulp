from unittest import TestCase

from mock import Mock, patch

from pulp.server.lazy.alias import AliasTable
from pulp.server.webservices.views.lazy import RedirectView


MODULE = 'pulp.server.webservices.views.lazy'


class TestRedirectView(TestCase):

    @patch(MODULE + '.pulp_conf')
    @patch(MODULE + '.Key.load')
    @patch(MODULE + '.AliasTable.load')
    def test_init(self, alias_load, key_load, pulp_conf):
        key_path = '/tmp/rsa.key'
        conf = {
            'authentication': {
                'rsa_key': key_path
            }
        }

        pulp_conf.get.side_effect = lambda s, p: conf.get(s).get(p)

        # test
        view = RedirectView()

        # validation
        self.assertTrue(isinstance(view.alias, AliasTable))
        alias_load.assert_called_once_with()
        key_load.assert_called_once_with(key_path)

    @patch(MODULE + '.Key.load', Mock())
    @patch(MODULE + '.AliasTable.load', Mock())
    def test_urljoin(self):
        scheme = 'http'
        host = 'redhat.com'
        port = '123'
        base = 'http://host'  # no trailing /
        path = '/my/path/'    # absolute path
        query = 'age=10'
        joined = RedirectView.urljoin(scheme, host, port, base, path, query)
        self.assertEqual(joined, 'http://redhat.com:123http://host/my/path/?age=10')

    @patch(MODULE + '.URL')
    @patch(MODULE + '.pulp_conf')
    @patch(MODULE + '.HttpResponseRedirect')
    @patch(MODULE + '.Key.load', Mock())
    @patch(MODULE + '.AliasTable.load', Mock())
    def test_get(self, http_redirect, pulp_conf, url):
        scheme = 'http'
        host = 'localhost'
        port = '80'
        path = '/streamer'
        query = 'arch=x86'
        conf = {
            'authentication': {
                'rsa_key': '/tmp/key'
            },
            'lazy': {
                'enabled': 'true',
                'redirect_host': host,
                'redirect_port': port,
                'redirect_path': path,
            }
        }
        pulp_conf.get.side_effect = lambda s, p: conf.get(s).get(p)
        environ = {
            'REQUEST_SCHEME': scheme,
            'SERVER_NAME': host,
            'SERVER_PORT': port,
            'REDIRECT_URL': path,
            'REDIRECT_QUERY_STRING': query
        }
        request = Mock(environ=environ)

        table = Mock()
        table.translate.return_value = '/tmp/test/published'

        # test
        view = RedirectView()
        view.alias = table
        reply = view.get(request)

        # validation
        url.assert_called_once_with(view.urljoin(
            scheme, host, port, path, table.translate.return_value, query))
        url.return_value.sign.assert_called_once_with(view.key)
        http_redirect.assert_called_once_with(str(url.return_value.sign.return_value))
        self.assertEqual(reply, http_redirect.return_value)

    @patch(MODULE + '.URL')
    @patch(MODULE + '.pulp_conf')
    @patch(MODULE + '.HttpResponseNotFound')
    @patch(MODULE + '.Key.load', Mock())
    @patch(MODULE + '.AliasTable.load', Mock())
    def test_get_lazy_not_enabled(self, http_not_found, pulp_conf, url):
        scheme = 'http'
        host = 'localhost'
        port = '80'
        path = '/streamer'
        query = 'arch=x86'
        conf = {
            'authentication': {
                'rsa_key': '/tmp/key'
            },
            'lazy': {
                'enabled': 'false',
                'redirect_host': host,
                'redirect_port': port,
                'redirect_path': path,
            }
        }
        pulp_conf.get.side_effect = lambda s, p: conf.get(s).get(p)
        environ = {
            'REQUEST_SCHEME': scheme,
            'SERVER_NAME': host,
            'SERVER_PORT': port,
            'REDIRECT_URL': path,
            'REDIRECT_QUERY_STRING': query
        }
        request = Mock(environ=environ)

        # test
        view = RedirectView()
        reply = view.get(request)

        # validation
        self.assertFalse(url.called)
        http_not_found.assert_called_once_with(path)
        self.assertEqual(reply, http_not_found.return_value)

    @patch(MODULE + '.HttpResponseNotFound')
    @patch(MODULE + '.Key.load', Mock())
    @patch(MODULE + '.AliasTable.load', Mock())
    def test_get_no_redirect(self, http_not_found):
        reply = RedirectView().get(Mock(environ={}))
        http_not_found.assert_called_once_with()
        self.assertEqual(reply, http_not_found.return_value)
