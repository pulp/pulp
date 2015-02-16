import json
import unittest

import mock

from base import (assert_auth_CREATE, assert_auth_DELETE, assert_auth_READ, assert_auth_UPDATE)
from pulp.server.exceptions import InvalidValue, MissingResource, MissingValue
from pulp.server.webservices.views import users
from pulp.server.webservices.views.users import (UserResourceView, UsersView)


class TestUsersView(unittest.TestCase):
    """
    Test userss view.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.users.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.users.factory')
    def test_get_users(self, mock_factory, mock_resp):
        """
        Test users retrieval.
        """
        users = [{'login': 'test-user', 'name': 'test-user', 'id': '12345'}]
        mock_factory.user_query_manager.return_value.find_all.return_value = users

        request = mock.MagicMock()
        users = UsersView()
        response = users.get(request)

        expected_cont = [{'_href': '/v2/users/test-user/', 'login': 'test-user',
                         'name': 'test-user'}]
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.users.generate_redirect_response')
    @mock.patch('pulp.server.webservices.views.users.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.users.factory')
    def test_create_user(self, mock_factory, mock_resp, mock_redirect):
        """
        Test user creation.
        """
        resp = {'login': 'test-user', 'name': 'test-user'}
        mock_factory.user_manager.return_value.create_user.return_value = resp

        request = mock.MagicMock()
        request.body = json.dumps({'login': 'test-user', 'name': 'test-user', 'password': '11111'})
        user = UsersView()
        response = user.post(request)

        expected_cont = {'_href': '/v2/users/test-user/', 'login': 'test-user',
                         'name': 'test-user'}
        mock_resp.assert_called_once_with(expected_cont)
        mock_redirect.assert_called_once_with(mock_resp.return_value, expected_cont['_href'])
        self.assertTrue(response is mock_redirect.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    def test_create_missing_login(self):
        """
        Test user creation with missing login.
        """
        request = mock.MagicMock()
        request.body = json.dumps({'name': 'test-user'})
        user = UsersView()
        try:
            response = user.post(request)
        except MissingValue, response:
            pass
        else:
            raise AssertionError("MissingValue should be raised with missing options")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['login'])

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    def test_create_invalid_param(self):
        """
        Test user creation with invalid param.
        """
        request = mock.MagicMock()
        request.body = json.dumps({'login': 'test-user', 'password': '11111',
                                   'invalid_param': 'invalid'})
        user = UsersView()
        try:
            response = user.post(request)
        except InvalidValue, response:
            pass
        else:
            raise AssertionError("InvalidValue should be raised with invalid options")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['invalid_param'])

    def test_add_link(self):
        """
        Test that the reverse works correctly.
        """
        user = {'login': 'user1'}
        link = users.add_link(user)
        href = {'_href': '/v2/users/user1/'}
        expected_cont = {'login': 'user1', '_href': '/v2/users/user1/'}
        self.assertEqual(link, href)
        self.assertEqual(user, expected_cont)


class TestUserResourceView(unittest.TestCase):
    """
    Test user resource view.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.users.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.users.factory')
    def test_get_single_user(self, mock_f, mock_resp):
        """
        Test single user retrieval.
        """
        user = {'login': 'test-user', 'name': 'test-user', 'id': '12345'}
        mock_f.user_query_manager.return_value.find_by_login.return_value = user

        request = mock.MagicMock()
        user = UserResourceView()
        response = user.get(request, 'test-user')

        expected_cont = {'login': 'test-user', 'name': 'test-user', '_href': '/v2/users/test-user/'}
        mock_resp.assert_called_once_with(expected_cont)
        mock_f.user_query_manager.return_value.find_by_login.assert_called_once_with('test-user')
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.users.factory')
    def test_get_invalid_user(self, mock_factory):
        """
        Test nonexistent user retrieval.
        """
        mock_factory.user_query_manager.return_value.find_by_login.return_value = None

        request = mock.MagicMock()
        user = UserResourceView()
        try:
            response = user.get(request, 'nonexistent_login')
        except MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised with nonexistent_user")

        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'resource_id': 'nonexistent_login'})

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.users.Permission.get_collection')
    @mock.patch('pulp.server.webservices.views.users.generate_json_response')
    @mock.patch('pulp.server.webservices.views.users.factory')
    def test_delete_single_user(self, mock_factory, mock_resp, mock_perm):
        """
        Test user deletion.
        """
        mock_factory.user_manager.return_value.delete_user.return_value = None
        mock_perm.return_value.find_one.return_value = 'some'

        request = mock.MagicMock()
        user = UserResourceView()
        response = user.delete(request, 'test-user')

        mock_factory.user_manager.return_value.delete_user.assert_called_once_with('test-user')
        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.users.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.users.factory')
    def test_update_user(self, mock_factory, mock_resp):
        """
        Test user update
        """
        resp = {'login': 'test-user', 'name': 'some-user', 'id': '12345'}
        mock_factory.user_manager.return_value.update_user.return_value = resp

        request = mock.MagicMock()
        request.body = json.dumps({'delta': {'name': 'some-user'}})
        user = UserResourceView()
        response = user.put(request, 'test-user')

        expected_cont = {'login': 'test-user', 'name': 'some-user'}

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)
