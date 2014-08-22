"""
This module contains tests for the pulp.server.webservices.controllers.decorators module.
"""
import mock

from .... import base
from pulp.server.exceptions import PulpCodedAuthenticationException
from pulp.server.webservices.controllers import decorators


class TestAuthenticationMethods(base.PulpWebserviceTests):
    """
    This class tests the authentication methods
    """

    @mock.patch('pulp.server.webservices.http.request_info', autospec=True, return_value='notauser')
    def test_check_preauthenticate_failed(self, mock_request_info):
        self.assertRaises(PulpCodedAuthenticationException, decorators.check_preauthenticated)
        mock_request_info.assert_called_once_with('REMOTE_USER')

    @mock.patch('pulp.server.managers.factory.authentication_manager', autospec=True)
    @mock.patch('pulp.server.webservices.http.username_password', autospec=True)
    def test_password_authentication_failed(self, mock_user_pass, mock_auth_manager):
        # Setup a mock check to ensure failure
        mock_user_pass.return_value = ('notauser', 'notapass')
        mock_auth_manager.return_value.check_username_password.return_value = None

        # Test
        self.assertRaises(PulpCodedAuthenticationException, decorators.password_authentication)
        mock_auth_manager.return_value.check_username_password.assert_called_once_with('notauser', 'notapass')

    @mock.patch('pulp.server.webservices.http.ssl_client_cert', autospec=True, return_value='cert')
    @mock.patch('pulp.server.webservices.http.http_authorization', autospec=True, return_value=None)
    @mock.patch('pulp.server.webservices.http.request_info', autospec=True, return_value=None)
    def test_oauth_auth_failed_no_user(self, mock_request_info, mock_http_auth, mock_client_cert):
        """
        Test that when no username or http authorization credentials are provided, an exception
        is raised.
        """
        self.assertRaises(PulpCodedAuthenticationException, decorators.oauth_authentication)
        mock_request_info.assert_called_once_with('HTTP_PULP_USER')
        mock_http_auth.assert_called_once_with()
        mock_client_cert.assert_called_once_with()

    @mock.patch('pulp.server.webservices.http.request_url', autospec=True, return_value='url')
    @mock.patch('pulp.server.webservices.http.ssl_client_cert', autospec=True, return_value='cert')
    @mock.patch('pulp.server.webservices.http.http_authorization', autospec=True, return_value='notnone')
    @mock.patch('pulp.server.webservices.http.request_info', autospec=True, return_value='notnone')
    @mock.patch('pulp.server.managers.factory.authentication_manager', autospec=True)
    def test_oauth_auth_failed(self, mock_auth_manager, *unused_mocks):
        """
        Test that when authentication failed, an exception is raised
        """
        mock_auth_manager.return_value.check_oauth.return_value = (None, None)

        self.assertRaises(PulpCodedAuthenticationException, decorators.oauth_authentication)
        mock_auth_manager.return_value.check_oauth.assert_called_once_with('notnone', 'notnone', 'url',
                                                                           'notnone', 'notnone')
