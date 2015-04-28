import json
import unittest

import mock
from django.http import HttpResponse

from base import assert_auth_READ
from pulp.server.webservices.views.root_actions import LoginView


class TestLoginView(unittest.TestCase):
    """
    Tests for login view.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.root_actions.factory')
    def test_login(self, mock_factory):
        """
        Test login that should return key and cert.
        """
        mock_user = mock.MagicMock()
        mock_user.get_principal.return_value = 'mock_principle'
        mock_factory.principal_manager.return_value = mock_user

        mock_cert = mock.MagicMock()
        key_cert = {'key': 'key1', 'certificate': 'certificate1'}
        mock_cert.make_admin_user_cert.return_value = (key_cert['key'], key_cert['certificate'])
        mock_factory.cert_generation_manager.return_value = mock_cert

        request = mock.MagicMock()
        login_view = LoginView()
        response = login_view.post(request)

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))
        content = json.loads(response.content)
        self.assertEqual(content, key_cert)
