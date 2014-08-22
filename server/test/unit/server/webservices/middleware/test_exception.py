"""
This module contains tests for the pulp.server.webservices.middleware.exception module.
"""
import unittest

import mock

from pulp.common import error_codes
from pulp.server.webservices.middleware.exception import ExceptionHandlerMiddleware
from pulp.server.exceptions import PulpCodedAuthenticationException


class TestExceptionHandlerMiddleware(unittest.TestCase):
    """
    Contains tests for pulp.server.webservices.middleware.exception.ExceptionHandlerMiddleware
    """
    def setUp(self):
        self.mock_app = mock.Mock()
        self.mock_app.return_value = 'mock_return'
        self.handler = ExceptionHandlerMiddleware(self.mock_app, debug=False)

    def test_no_exception_raised(self):
        """
        Test that when no exception is raised, the app response is returned.
        """
        self.assertEquals(self.mock_app.return_value, self.handler('arg1', 'arg2'))
        self.mock_app.assert_called_once_with('arg1', 'arg2')

    @mock.patch('json.dumps', autospec=True)
    @mock.patch('pulp.server.webservices.serialization.error.http_error_obj', autospec=True, return_value={})
    def test_pulp_exception_no_debug(self, mock_error_obj, mock_dumps):
        """
        Tests that when the debug flag is False, Pulp exceptions result in logging to info
        rather than logging to error with the traceback.
        """
        # Setup
        self.mock_app.side_effect = PulpCodedAuthenticationException(error_code=error_codes.PLP0025)

        # Test
        self.handler('environ', mock.Mock())
        # Assert the http_error_obj is called with the exception's http status code
        self.assertEquals(1, mock_error_obj.call_count)
        self.assertEquals(self.mock_app.side_effect.http_status_code, mock_error_obj.call_args[0][0])
        # Assert that the response has the expected keys and values
        response = mock_dumps.call_args[0][0]
        self.assertEquals(response['error'], self.mock_app.side_effect.to_dict())
        self.assertFalse('exception' in response)
        self.assertFalse('traceback' in response)


    @mock.patch('traceback.format_tb', autospec=True)
    @mock.patch('traceback.format_exception_only', autospec=True)
    @mock.patch('json.dumps', autospec=True)
    @mock.patch('pulp.server.webservices.serialization.error.http_error_obj', autospec=True, return_value={})
    def test_pulp_exception_with_debug(self, mock_error_obj, mock_dumps, mock_format_exception, mock_format_tb):
        """
        Tests that when the debug flag is True, Pulp exceptions result logging the exception
        and including the exception and traceback in the response.
        """
        # Setup
        handler = ExceptionHandlerMiddleware(self.mock_app, debug=True)
        self.mock_app.side_effect = PulpCodedAuthenticationException(error_code=error_codes.PLP0025)
        mock_format_exception.return_value = 'Formatted exception'
        mock_format_tb.return_value = 'tb'

        # Test
        handler('environ', mock.Mock())
        # Assert the http_error_obj is called with the exception's status code
        self.assertEquals(1, mock_error_obj.call_count)
        self.assertEquals(self.mock_app.side_effect.http_status_code, mock_error_obj.call_args[0][0])
        # Assert that the response has the expected keys and values
        response = mock_dumps.call_args[0][0]
        self.assertEquals(response['exception'], 'Formatted exception')
        self.assertEquals(response['traceback'], 'tb')

    @mock.patch('traceback.format_tb', autospec=True)
    @mock.patch('traceback.format_exception_only', autospec=True)
    @mock.patch('json.dumps', autospec=True)
    @mock.patch('pulp.server.webservices.serialization.error.http_error_obj', autospec=True, return_value={})
    def test_unhandled_exception(self, mock_error_obj, mock_dumps, mock_format_exception, mock_format_tb):
        """
        Tests that non-Pulp exceptions result in logging the exception and including the
        exception and traceback in the response.
        """
        # Setup
        self.mock_app.side_effect = OSError()
        mock_format_exception.return_value = 'Formatted exception'
        mock_format_tb.return_value = 'tb'

        # Test
        self.handler('environ', mock.Mock())
        # Assert the http_error_obj is called with the a 500 code
        self.assertEquals(1, mock_error_obj.call_count)
        self.assertEquals(500, mock_error_obj.call_args[0][0])
        # Assert that the response has the expected keys and values
        response = mock_dumps.call_args[0][0]
        self.assertEquals(response['exception'], 'Formatted exception')
        self.assertEquals(response['traceback'], 'tb')
