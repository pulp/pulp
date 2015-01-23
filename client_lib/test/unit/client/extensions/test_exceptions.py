"""
This module contains tests for the pulp.client.extensions.exceptions module.
"""
from _socket import gaierror
import os
from socket import error as socket_error

from M2Crypto.SSL.Checker import WrongHost
import mock

import pulp.bindings.exceptions as exceptions
from pulp.client.extensions.core import TAG_FAILURE, TAG_PARAGRAPH
import pulp.client.extensions.exceptions as handler
from pulp.client.arg_utils import InvalidConfig
from pulp.devel.unit import base


CERT_FILENAME = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                             '..', '..', '..', 'data', 'test_client_exception_handler', 'cert.pem')


class ExceptionsLoaderTest(base.PulpClientTests):
    """
    All tests in this class use the exception handler configured in the
    PulpV2ClientTest base class as the test object.

    The tests on each individual handle method will do a weak but sufficient
    check to ensure the correct message is output.
    """

    def test_handle_exception(self):
        """
        Tests the high level call that branches based on exception type for all types.
        """

        # For each exception type, check that the proper code is returned and
        # that a failure message has been output. For simplicity in those tests,
        # reset the tags after each run.

        code = self.exception_handler.handle_exception(exceptions.BadRequestException({}))
        self.assertEqual(code, handler.CODE_BAD_REQUEST)
        self.assertEqual(3, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(exceptions.ConflictException({}))
        self.assertEqual(code, handler.CODE_CONFLICT)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(exceptions.ConnectionException({}))
        self.assertEqual(code, handler.CODE_CONNECTION_EXCEPTION)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(exceptions.NotFoundException({'resources' : {'repo_id' : 'foo'}}))
        self.assertEqual(code, handler.CODE_NOT_FOUND)
        self.assertEqual(2, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(exceptions.PermissionsException({}))
        self.assertEqual(code, handler.CODE_PERMISSIONS_EXCEPTION)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(exceptions.PulpServerException({}))
        self.assertEqual(code, handler.CODE_PULP_SERVER_EXCEPTION)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(InvalidConfig('Test Message'))
        self.assertEqual(code, handler.CODE_INVALID_CONFIG)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(WrongHost('expected', 'actual'))
        self.assertEqual(code, handler.CODE_WRONG_HOST)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(exceptions.ApacheServerException('Test Message'))
        self.assertEqual(code, handler.CODE_APACHE_SERVER_EXCEPTION)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(gaierror())
        self.assertEqual(code, handler.CODE_UNKNOWN_HOST)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(socket_error())
        self.assertEqual(code, handler.CODE_SOCKET_ERROR)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(exceptions.ClientCertificateExpiredException(
            CERT_FILENAME))
        self.assertEqual(code, handler.CODE_PERMISSIONS_EXCEPTION)
        self.assertEqual([TAG_FAILURE, TAG_PARAGRAPH], self.prompt.get_write_tags())
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(Exception({}))
        self.assertEqual(code, handler.CODE_UNEXPECTED)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

    def test_bad_request_invalid_values(self):
        """
        Tests the invalid values classification of bad request exceptions.
        """

        # Test
        e = exceptions.BadRequestException({'property_names' : ['foo']})
        code = self.exception_handler.handle_bad_request(e)

        # Verify
        self.assertEqual(code, handler.CODE_BAD_REQUEST)
        self.assertTrue('properties were invalid' in self.recorder.lines[0])
        self.assertTrue('foo' in self.recorder.lines[0])

    def test_bad_request_missing_properties(self):
        """
        Tests the missing properties classification of bad request exceptions.
        """

        # Test
        e = exceptions.BadRequestException({'missing_property_names' : ['foo']})
        code = self.exception_handler.handle_bad_request(e)

        # Verify
        self.assertEqual(code, handler.CODE_BAD_REQUEST)
        self.assertTrue('not provided' in self.recorder.lines[0])
        self.assertTrue('foo' in self.recorder.lines[0])

    def test_bad_request_with_error(self):
        """
        Tests the errors classification of bad request exceptions.
        """
        self.exception_handler._display_coded_error = mock.MagicMock()
        e = exceptions.BadRequestException({'error': {'description': 'test_error'}})

        code = self.exception_handler.handle_bad_request(e)

        self.assertEqual(code, handler.CODE_BAD_REQUEST)
        self.exception_handler._display_coded_error.assert_called_once_with(
            {'description': 'test_error'}
        )

    def test__display_coded_error_single_error(self):
        """
        Test that render_failure_message is called when a coded error is passed in.
        """
        self.prompt.render_failure_message = mock.MagicMock()
        e = exceptions.BadRequestException({'error': {'description': 'test_error'}})

        self.exception_handler._display_coded_error(e.extra_data.get('error'))

        self.prompt.render_failure_message.assert_called_once_with('test_error')

    def test__display_coded_error_recursive_errors(self):
        """
        Test that sub errors will be rendered.
        """
        self.prompt.render_failure_message = mock.MagicMock()
        inner_e = {'description': 'inner_error'}
        outer_e = {'description': 'outer_error', 'sub_errors': [inner_e]}

        self.exception_handler._display_coded_error(outer_e)

        self.prompt.render_failure_message.has_calls(
            mock.call('outer_error'), mock.call('inner_error')
        )

    def test_bad_request_other(self):
        """
        Tests a bad request with no classification.
        """

        # Test
        e = exceptions.BadRequestException({})
        code = self.exception_handler.handle_bad_request(e)

        # Verify
        self.assertEqual(code, handler.CODE_BAD_REQUEST)
        self.assertTrue('incorrect' in self.recorder.lines[0])

    def test_not_found(self):

        # Test
        e = exceptions.NotFoundException({'resources' : {'repo_id' : 'foo'}})
        code = self.exception_handler.handle_not_found(e)

        # Verify
        self.assertEqual(code, handler.CODE_NOT_FOUND)
        self.assertTrue('foo' in self.recorder.lines[2])

    def test_conflict_resource(self):
        """
        Tests the conflict classification that represents a duplicate resource.
        """

        # Test
        e = exceptions.ConflictException({'resource_id' : 'foo'})
        code = self.exception_handler.handle_conflict(e)

        # Verify
        self.assertEqual(code, handler.CODE_CONFLICT)
        self.assertTrue('resource' in self.recorder.lines[0])
        self.assertTrue('foo' in self.recorder.lines[0])

    def test_conflict_operation(self):
        """
        Tests the conflict classification that represents a conflicting operation.
        """

        # Test
        reasons = [ {'resource_id' : 'foo', 'resource_type' : 'bar', 'operation' : 'baz'}]
        e = exceptions.ConflictException({'reasons' : reasons})
        code = self.exception_handler.handle_conflict(e)

        # Verify
        self.assertEqual(code, handler.CODE_CONFLICT)
        self.assertTrue('operation' in self.recorder.lines[0])
        self.assertTrue('foo' in self.recorder.lines[0])
        self.assertTrue('bar' in self.recorder.lines[0])
        self.assertTrue('baz' in self.recorder.lines[0])

    def test_conflict_other(self):
        """
        Tests a conflict that does not contain classificationd data.
        """

        # Test
        e = exceptions.ConflictException({})
        code = self.exception_handler.handle_conflict(e)

        # Verify
        self.assertEqual(code, handler.CODE_CONFLICT)
        self.assertTrue('unexpected', self.recorder.lines[0])

    def test_server_error(self):
        """
        Tests a general server error.
        """

        # Test
        e = exceptions.PulpServerException({})
        code = self.exception_handler.handle_server_error(e)

        # Verify
        self.assertEqual(code, handler.CODE_PULP_SERVER_EXCEPTION)
        self.assertTrue('internal error' in self.recorder.lines[0])

    def test_connection_error(self):
        """
        Tests a client-side connection error.
        """

        # Test
        e = exceptions.ConnectionException()
        code = self.exception_handler.handle_connection_error(e)

        # Verify
        self.assertEqual(code, handler.CODE_CONNECTION_EXCEPTION)
        self.assertTrue('contact the server' in self.recorder.lines[0])

    def test_permissions(self):
        """
        Tests a client-side permissions error.
        """

        # Test
        response_body = {'auth_error_code': 'authentication_failed'}
        e = exceptions.PermissionsException(response_body)
        code = self.exception_handler.handle_permission(e)

        # Verify
        self.assertEqual(code, handler.CODE_PERMISSIONS_EXCEPTION)
        self.assertTrue('specified user' in self.recorder.lines[0])

    def test_invalid_config(self):
        """
        Tests a client-side argument parsing error.
        """

        # Test
        e = InvalidConfig('Expected')
        code = self.exception_handler.handle_invalid_config(e)

        # Verify
        self.assertEqual(code, handler.CODE_INVALID_CONFIG)
        self.assertEqual('Expected', self.recorder.lines[0].strip())
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])

    def test_wrong_host(self):
        """
        Tests a client-side wrong host error.
        """

        # Test
        expected = 'localhost'
        actual = 'pulp-server'
        e = WrongHost(expected, actual)
        code = self.exception_handler.handle_wrong_host(e)

        # Verify
        self.assertEqual(code, handler.CODE_WRONG_HOST)
        self.assertTrue(expected in self.recorder.lines[0])
        self.assertTrue(actual in self.recorder.lines[0])
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])

    def test_apache_server_error(self):
        """
        Tests handling the case where Apache raised an exception.
        """

        # Test
        msg = 'Test Message'
        e = exceptions.ApacheServerException(msg)
        code = self.exception_handler.handle_apache_error(e)

        # Verify
        self.assertEqual(code, handler.CODE_APACHE_SERVER_EXCEPTION)
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])

    def test_handle_expired_client_cert(self):
        """
        Tests handling client-side SSL verification issues.
        """

        # Test
        e = exceptions.ClientCertificateExpiredException(CERT_FILENAME)
        code = self.exception_handler.handle_expired_client_cert(e)

        # Verify
        self.assertEqual(code, handler.CODE_PERMISSIONS_EXCEPTION)
        self.assertEqual([TAG_FAILURE, TAG_PARAGRAPH], self.prompt.get_write_tags())
        self.assertTrue('May  9 12:39:37 2013 GMT' in self.recorder.lines[2])

    def atest_handle_ssl_validation_error(self):
        """
        Tests handling untrusted SSL certificate issues.
        """
        e = exceptions.CertificateVerificationException(CERT_FILENAME)

        code = self.exception_handler.handle_expired_client_cert(e)

        self.assertEqual(code, handler.CODE_APACHE_SERVER_EXCEPTION)
        self.assertEqual([TAG_FAILURE, TAG_PARAGRAPH], self.prompt.get_write_tags())
        self.assertTrue("The server's SSL certificate is untrusted" in self.recorder.lines[0])

    def test_unknown_host(self):
        """
        Tests the case where the client is configured with a host that cannot
        be resolved.
        """

        # Test
        e = gaierror()
        code = self.exception_handler.handle_unknown_host(e)

        # Verify
        self.assertEqual(code, handler.CODE_UNKNOWN_HOST)
        self.assertTrue(self.config['server']['host'] in self.recorder.lines[0])
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])

    def test_unexpected(self):
        """
        Tests the handling of any non-client defined exception class.
        """

        # Test
        e = Exception()
        code = self.exception_handler.handle_unexpected(e)

        # Verify
        self.assertEqual(code, handler.CODE_UNEXPECTED)
        self.assertTrue('unexpected' in self.recorder.lines[0])

    def test_socket_error(self):
        # Test
        e = socket_error()
        code = self.exception_handler.handle_socket_error(e)

        # Verify
        self.assertEqual(code, handler.CODE_SOCKET_ERROR)
        self.assertTrue('refused' not in self.recorder.lines[0])
        self.assertEqual([TAG_FAILURE], self.prompt.get_write_tags())

    def test_socket_error_connection_refused(self):
        # Test
        e = socket_error(111)
        code = self.exception_handler.handle_socket_error(e)

        # Verify
        self.assertEqual(code, handler.CODE_SOCKET_ERROR)
        self.assertTrue('refused' in self.recorder.lines[0])
        self.assertEqual([TAG_FAILURE], self.prompt.get_write_tags())

    def test_certificate_expiration(self):
        # Test
        date = self.exception_handler._certificate_expiration_date(CERT_FILENAME)

        # Verify
        self.assertEqual(date, 'May  9 12:39:37 2013 GMT')
