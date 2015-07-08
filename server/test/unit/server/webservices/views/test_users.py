"""
This module contains tests for the pulp.server.webservices.views.users module.
"""
import json
import unittest

import mock

from base import (assert_auth_CREATE, assert_auth_DELETE, assert_auth_READ, assert_auth_UPDATE)
from pulp.server.exceptions import InvalidValue, MissingValue
from pulp.server.db import model
from pulp.server.webservices.views import serializers, util
from pulp.server.webservices.views.users import (UserResourceView, UserSearchView, UsersView)


class TestUserSearchView(unittest.TestCase):
    """
    Assert correct configuration of the UserSearchView class.
    """
    def test_class_attributes(self):
        """
        Assert that the class attributes are set correctly.
        """
        self.assertEqual(UserSearchView.response_builder,
                         util.generate_json_response_with_pulp_encoder)
        self.assertEqual(UserSearchView.model, model.User)
        self.assertEqual(UserSearchView.model.serializer, serializers.User)


class TestUsersView(unittest.TestCase):
    """
    Test userss view.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.users.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.users.model.User')
    def test_get_users(self, mock_model, mock_resp):
        """
        Test users retrieval.
        """
        request = mock.MagicMock()
        view = UsersView()
        response = view.get(request)
        mock_model.serializer.assert_called_once_with(mock_model.objects.return_value,
                                                      multiple=True)
        mock_resp.assert_called_once_with(mock_model.serializer.return_value.data)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
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

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
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

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.users.generate_redirect_response')
    @mock.patch('pulp.server.webservices.views.users.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.users.factory')
    @mock.patch('pulp.server.webservices.views.users.model.User')
    @mock.patch('pulp.server.webservices.views.users.user_controller')
    def test_create_user(self, mock_ctrl, mock_model, mock_factory, mock_resp, mock_redirect):
        """
        Test user creation.
        """
        request = mock.MagicMock()
        request.body = json.dumps({'login': 'test-user', 'name': 'test-user', 'password': '111'})
        mock_model.serializer.return_value.data = {'_id': 'copy to id', '_href': 'mock/path'}
        user = UsersView()
        response = user.post(request)

        mock_ctrl.create_user.assert_called_once_with('test-user', password='111', name='test-user')
        mock_model.serializer.assert_called_once_with(mock_ctrl.create_user.return_value)
        mock_auto_perm = mock_factory.permission_manager().grant_automatic_permissions_for_resource
        mock_auto_perm.assert_called_once_with('mock/path')
        mock_resp.assert_called_once_with({'id': 'copy to id', '_href': 'mock/path',
                                           '_id': 'copy to id'})
        mock_redirect.assert_called_once_with(mock_resp.return_value, 'mock/path')
        self.assertTrue(response is mock_redirect.return_value)


class TestUserResourceView(unittest.TestCase):
    """
    Test user resource view.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.users.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.users.model.User')
    def test_get_single_user(self, mock_model, mock_resp):
        """
        Test single user retrieval.
        """
        request = mock.MagicMock()
        user = UserResourceView()
        response = user.get(request, 'test-user')

        mock_model.objects.get_or_404.assert_called_once_with(login='test-user')
        mock_resp.assert_called_once_with(mock_model.serializer.return_value.data)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.users.reverse')
    @mock.patch('pulp.server.webservices.views.users.Permission.get_collection')
    @mock.patch('pulp.server.webservices.views.users.generate_json_response')
    @mock.patch('pulp.server.webservices.views.users.user_controller')
    def test_delete_single_user(self, mock_ctrl, mock_resp, mock_perm, mock_rev):
        """
        Test user deletion.
        """
        mock_perm().find_one.return_value = 'some'
        request = mock.MagicMock()
        user = UserResourceView()
        response = user.delete(request, 'test-user')

        mock_ctrl.delete_user.assert_called_once_with('test-user')
        mock_resp.assert_called_once_with()
        mock_perm().remove.assert_called_once_with({'resource': mock_rev.return_value})
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.users.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.users.model.User')
    @mock.patch('pulp.server.webservices.views.users.user_controller')
    def test_update_user(self, mock_ctrl, mock_model, mock_resp):
        """
        Test user update
        """
        request = mock.MagicMock()
        request.body = json.dumps({'delta': {'name': 'some-user'}})
        user = UserResourceView()
        response = user.put(request, 'test-user')

        mock_ctrl.update_user.assert_called_once_with('test-user', {'name': 'some-user'})
        mock_model.serializer.assert_called_once_with(mock_ctrl.update_user.return_value)
        mock_resp.assert_called_once_with(mock_model.serializer.return_value.data)
        self.assertTrue(response is mock_resp.return_value)
