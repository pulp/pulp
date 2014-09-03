"""
This module contains tests for the pulp.bindings.server module.
"""
import locale
import logging
import unittest

from M2Crypto import SSL
import mock

from pulp.bindings import exceptions, server


class TestHTTPSServerWrapper(unittest.TestCase):
    """
    This class contains tests for the HTTPSServerWrapper class.
    """
    @mock.patch('pulp.bindings.server.httpslib.HTTPSConnection.request')
    def test_request_handles_untrusted_server_cert(self, request):
        """
        Test the request() method when the server is using a certificate that is not signed by a
        trusted certificate authority.
        """
        conn = server.PulpConnection('host')
        wrapper = server.HTTPSServerWrapper(conn)
        # Let's raise the SSLError with the right string to count as a certificate problem
        request.side_effect = SSL.SSLError('oh nos certificate verify failed can you believe it?')

        self.assertRaises(exceptions.CertificateVerificationException, wrapper.request, 'GET',
                          '/awesome/api/', '')

    @mock.patch('pulp.bindings.server.httpslib.HTTPSConnection.getresponse')
    @mock.patch('pulp.bindings.server.httpslib.HTTPSConnection.request')
    @mock.patch('pulp.bindings.server.SSL.Context.load_verify_locations')
    @mock.patch('pulp.bindings.server.SSL.Context.set_verify')
    def test_request_verify_ssl_false(self, set_verify, load_verify_locations, request,
                                           getresponse):
        """
        Test the request() method when the connection's verify_ssl setting is False.
        """
        conn = server.PulpConnection('host', validate_ssl_ca=False)
        wrapper = server.HTTPSServerWrapper(conn)

        class FakeResponse(object):
            """
            This class is used to fake the response from httpslib.
            """
            def read(self):
                return '{}'

            status = 200

        getresponse.return_value = FakeResponse()

        status, body = wrapper.request('GET', '/awesome/api/', '')

        self.assertEqual(status, 200)
        self.assertEqual(body, {})
        # These should not have been called
        self.assertEqual(set_verify.call_count, 0)
        self.assertEqual(load_verify_locations.call_count, 0)

    @mock.patch('pulp.bindings.server.SSL.Context.load_verify_locations')
    @mock.patch('pulp.bindings.server.SSL.Context.set_verify')
    def test_request_with_ca_cant_read(self, set_verify, load_verify_locations):
        """
        Test the request() method when the connection's ca_path setting points to a path that isn't
        a directory or a file.
        """
        ca_path='/does/not/exist/'
        conn = server.PulpConnection('host', ca_path=ca_path)
        wrapper = server.HTTPSServerWrapper(conn)

        try:
            wrapper.request('GET', '/awesome/api/', '')
            self.fail('An exception should have been raised, and it was not.')
        except exceptions.MissingCAPathException as e:
            self.assertEqual(e.args[0], ca_path)
        except:
            self.fail('The wrong exception type was raised!')

    @mock.patch('os.path.isdir', return_value=True)
    @mock.patch('pulp.bindings.server.httpslib.HTTPSConnection.getresponse')
    @mock.patch('pulp.bindings.server.httpslib.HTTPSConnection.request')
    @mock.patch('pulp.bindings.server.SSL.Context.load_verify_locations')
    @mock.patch('pulp.bindings.server.SSL.Context.set_verify')
    def test_request_with_ca_path_to_dir(self, set_verify, load_verify_locations, request,
                                         getresponse, isdir):
        """
        Test the request() method when the connection's ca_path setting points to a directory.
        """
        ca_path = '/path/to/an/existing/dir/'
        conn = server.PulpConnection('host', validate_ssl_ca=True, ca_path=ca_path)
        wrapper = server.HTTPSServerWrapper(conn)

        class FakeResponse(object):
            """
            This class is used to fake the response from httpslib.
            """
            def read(self):
                return '{}'

            status = 200

        getresponse.return_value = FakeResponse()

        status, body = wrapper.request('GET', '/awesome/api/', '')

        self.assertEqual(status, 200)
        self.assertEqual(body, {})
        # Make sure the SSL settings are correct
        set_verify.assert_called_once_with(SSL.verify_peer, depth=100)
        load_verify_locations.assert_called_once_with(capath=ca_path)

    @mock.patch('os.path.isfile', return_value=True)
    @mock.patch('pulp.bindings.server.httpslib.HTTPSConnection.getresponse')
    @mock.patch('pulp.bindings.server.httpslib.HTTPSConnection.request')
    @mock.patch('pulp.bindings.server.SSL.Context.load_verify_locations')
    @mock.patch('pulp.bindings.server.SSL.Context.set_verify')
    def test_request_with_ca_path_to_file(self, set_verify, load_verify_locations, request,
                                          getresponse, isfile):
        """
        Test the request() method when the connection's ca_path setting points to a file.
        """
        ca_path = '/path/to/an/existing.file'
        conn = server.PulpConnection('host', validate_ssl_ca=True, ca_path=ca_path)
        wrapper = server.HTTPSServerWrapper(conn)

        class FakeResponse(object):
            """
            This class is used to fake the response from httpslib.
            """
            def read(self):
                return '{"it": "worked!"}'

            status = 200

        getresponse.return_value = FakeResponse()

        status, body = wrapper.request('GET', '/awesome/api/', '')

        self.assertEqual(status, 200)
        self.assertEqual(body, {'it': 'worked!'})
        # Make sure the SSL settings are correct
        set_verify.assert_called_once_with(SSL.verify_peer, depth=100)
        load_verify_locations.assert_called_once_with(cafile=ca_path)


class TestPulpConnection(unittest.TestCase):
    """
    This class contains tests for the PulpConnection object.
    """
    def test___init___defaults(self):
        """
        Test __init__() with default parameters.
        """
        host = 'host'

        connection = server.PulpConnection(host)

        self.assertEqual(connection.host, host)
        self.assertEqual(connection.port, 443)
        self.assertEqual(connection.path_prefix, '/pulp/api')
        self.assertEqual(connection.timeout, 120)
        self.assertTrue(isinstance(connection.log, logging.Logger))
        self.assertEqual(connection.log.name, 'pulp.bindings.server')
        self.assertEqual(connection.api_responses_logger, None)
        self.assertEqual(connection.username, None)
        self.assertEqual(connection.password, None)
        self.assertEqual(connection.cert_filename, None)
        self.assertEqual(connection.oauth_key, None)
        self.assertEqual(connection.oauth_secret, None)
        self.assertEqual(connection.oauth_user, 'admin')

        # Make sure the headers are right
        expected_locale = locale.getdefaultlocale()[0]
        if expected_locale:
            expected_locale = expected_locale.lower().replace('_', '-')
        else:
            expected_locale = 'en-us'
        expected_headers = {'Accept': 'application/json', 'Accept-Language': expected_locale,
                            'Content-Type': 'application/json'}
        self.assertEqual(connection.headers, expected_headers)
        self.assertTrue(isinstance(connection.server_wrapper, server.HTTPSServerWrapper))
        self.assertEqual(connection.server_wrapper.pulp_connection, connection)
        self.assertEqual(connection.validate_ssl_ca, True)
        self.assertEqual(connection.ca_path, server.DEFAULT_CA_PATH)

    def test___init___ca_path_set(self):
        """
        Test __init__() with the ca_path argument explicitly set.
        """
        ca_path = '/some/path'

        connection = server.PulpConnection('host', ca_path=ca_path)

        self.assertEqual(connection.ca_path, ca_path)

    def test___init___verify_ssl_false(self):
        """
        Test __init__() with validate_ssl set to False.
        """
        connection = server.PulpConnection('host', validate_ssl_ca=False)

        self.assertEqual(connection.validate_ssl_ca, False)

    def test___init___verify_ssl_true(self):
        """
        Test __init__() with validate_ssl set to True.
        """
        connection = server.PulpConnection('host', validate_ssl_ca=True)

        self.assertEqual(connection.validate_ssl_ca, True)
