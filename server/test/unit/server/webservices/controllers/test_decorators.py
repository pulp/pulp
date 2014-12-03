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

    def func(self):
        """
        This method is used in tests involving the decorator. It does absolutely nothing.
        """
        pass

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

    @mock.patch('pulp.server.webservices.http.resource_path', autospec=True)
    @mock.patch('pulp.server.managers.factory.principal_manager', autospec=True)
    @mock.patch('pulp.server.webservices.controllers.decorators.check_preauthenticated')
    @mock.patch('pulp.server.managers.auth.user.query.UserQueryManager.is_superuser',
                return_value=False)
    @mock.patch('pulp.server.managers.auth.user.query.UserQueryManager.is_authorized',
                return_value=False)
    def test_auth_decorator_not_super(self, mock_is_authed, *unused_mocks):
        """
        Test that if the user is not a super user and the operation requires super user,
        an exception is raised. This test mocks out the authentication portion of the decorator.
        """
        decorated_func = decorators.auth_required(0, True)(self.func)
        self.assertRaises(PulpCodedAuthenticationException, decorated_func, None)
        self.assertEqual(0, mock_is_authed.call_count)

    @mock.patch('pulp.server.webservices.http.resource_path', autospec=True)
    @mock.patch('pulp.server.managers.factory.principal_manager', autospec=True)
    @mock.patch('pulp.server.webservices.controllers.decorators.consumer_cert_authentication',
                return_value='gob')
    @mock.patch('pulp.server.webservices.controllers.decorators.user_cert_authentication',
                return_value=None)
    @mock.patch('pulp.server.webservices.controllers.decorators.password_authentication',
                return_value=None)
    @mock.patch('pulp.server.webservices.controllers.decorators.check_preauthenticated',
                return_value=None)
    @mock.patch('pulp.server.webservices.controllers.decorators.is_consumer_authorized',
                return_value=False)
    def test_auth_decorator_consumer_not_authorized(self, mock_is_authorized, *unused_mocks):
        """
        Test that if the consumer isn't authorized for a particular action, an exception is
        raised.
        """
        decorated_func = decorators.auth_required(0, False)(self.func)
        self.assertRaises(PulpCodedAuthenticationException, decorated_func, None)
        self.assertEqual(1, mock_is_authorized.call_count)

    @mock.patch('pulp.server.webservices.http.resource_path', autospec=True)
    @mock.patch('pulp.server.managers.factory.principal_manager', autospec=True)
    @mock.patch('pulp.server.webservices.controllers.decorators.check_preauthenticated')
    @mock.patch('pulp.server.managers.auth.user.query.UserQueryManager.is_authorized',
                return_value=False)
    def test_auth_decorator_not_authorized(self, mock_is_authorized, *unused_mocks):
        """
        Test that if an admin user isn't authorized for a particular action, an exception
        is raised.
        """
        decorated_func = decorators.auth_required(0, False)(self.func)
        self.assertRaises(PulpCodedAuthenticationException, decorated_func, None)
        self.assertEqual(1, mock_is_authorized.call_count)
