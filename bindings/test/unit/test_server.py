import unittest

import mock
from M2Crypto import httpslib, SSL

from pulp.bindings.server import PulpConnection, HTTPSServerWrapper


class TestServerBindings(unittest.TestCase):
    def test_ssl_validate_config_defaults(self):
        pulp_connection = PulpConnection('test_host')
        self.assertEqual(pulp_connection.validate_ssl_ca, True)
        self.assertEqual(pulp_connection.system_ca_dir, '/etc/pki/tls/certs')

    def test_customized_ssl_validate_config(self):
        pulp_connection = PulpConnection('test_host', validate_ssl_ca=False, system_ca_dir='/test/dir')
        self.assertEqual(pulp_connection.validate_ssl_ca, False)
        self.assertEqual(pulp_connection.system_ca_dir, '/test/dir')

    @mock.patch.object(httpslib.HTTPSConnection, 'request')
    @mock.patch.object(httpslib.HTTPSConnection, 'getresponse')
    @mock.patch.object(SSL.Context, 'load_verify_locations')
    @mock.patch.object(SSL.Context, 'set_verify')
    def test_https_wrapper_with_ssl_validation(self, mock_set_verify, mock_load_verify_locations,
                                               *mocks):
        pulp_connection = PulpConnection('test_host', username='username', password='password')
        https_server_wrapper = HTTPSServerWrapper(pulp_connection)
        https_server_wrapper.request('DELETE', 'https://some/url', {})
        mock_set_verify.assert_called_once_with(SSL.verify_peer, 1)
        mock_load_verify_locations.assert_called_once_with(capath=pulp_connection.system_ca_dir)

    @mock.patch.object(httpslib.HTTPSConnection, 'request')
    @mock.patch.object(httpslib.HTTPSConnection, 'getresponse')
    @mock.patch.object(SSL.Context, 'load_verify_locations')
    @mock.patch.object(SSL.Context, 'set_verify')
    def test_https_wrapper_no_ssl_validation(self, mock_set_verify, mock_load_verify_locations,
                                             *mocks):
        pulp_connection = PulpConnection('test_host', username='username', password='password',
                                         validate_ssl_ca=False)
        https_server_wrapper = HTTPSServerWrapper(pulp_connection)
        https_server_wrapper.request('DELETE', 'https://some/url', {})
        self.assertFalse(mock_set_verify.called)
        self.assertFalse(mock_load_verify_locations.called)
