import unittest

import mock

from base import assert_auth_EXECUTE, assert_auth_READ
from pulp.server.exceptions import InvalidValue
from pulp.server.webservices.views.permissions import (GrantToRoleView, GrantToUserView,
                                                       PermissionView, RevokeFromRoleView,
                                                       RevokeFromUserView)


class TestPermissionsiew(unittest.TestCase):
    """
    Test permissions view.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.permissions.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.permissions.factory')
    def test_get_all_permissions(self, mock_f, mock_resp):
        """
        Test the permissions retrieval.
        """
        perm = [{'resource': '/v2/some/', 'id': '1234',
                'users': [{'username': 'test-user', 'permissions': [0]}]}]

        mock_f.permission_query_manager.return_value.find_all.return_value = perm
        mock_f.permission_manager.return_value.operation_value_to_name.return_value = 'READ'

        request = mock.MagicMock()
        request.GET = {}

        permission = PermissionView()
        response = permission.get(request)
        expected_cont = [{'id': '1234', 'resource': '/v2/some/', 'users': {'test-user': ['READ']}}]

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.permissions.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.permissions.factory')
    def test_get_resource_permission(self, mock_f, mock_resp):
        """
        Test specific resource permissions retrieval.
        """
        perm = {'resource': '/v2/some/', 'id': '1234',
                'users': [{'username': 'test-user', 'permissions': [0]}]}

        mock_f.permission_query_manager.return_value.find_by_resource.return_value = perm
        mock_f.permission_manager.return_value.operation_value_to_name.return_value = 'READ'

        request = mock.MagicMock()
        request.GET = {'resource': '/v2/some/'}

        permission = PermissionView()
        response = permission.get(request)
        expected_cont = [{'id': '1234', 'resource': '/v2/some/', 'users': {'test-user': ['READ']}}]

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)


class TestGrantToUserView(unittest.TestCase):
    """
    Test grant permission to user.
    """
    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.permissions.generate_json_response')
    @mock.patch('pulp.server.webservices.views.permissions.factory')
    def test_grant_to_user(self, mock_factory, mock_resp):
        """
        Test grant permissions to user.
        """
        request = mock.MagicMock()
        request.body_as_json = {'operations': ['READ'], 'login': 'test', 'resource': '/v2/some/'}
        mock_factory.permission_manager.return_value.grant.return_value = None
        mock_factory.permission_manager.return_value.operation_names_to_values.return_value = [0]
        grant = GrantToUserView()
        response = grant.post(request)

        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)
        mock_factory.permission_manager.return_value.grant.assert_called_once_with(
            '/v2/some/', 'test', [0])

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    def test_grant_to_user_invalid_param(self):
        """
        Test grant permissions to user with invalid params.
        """
        request = mock.MagicMock()
        request.body_as_json = {'operations': ['READ'], 'resource': '/v2/some/'}
        grant = GrantToUserView()
        try:
            grant.post(request)
        except InvalidValue, response:
            pass
        else:
            raise AssertionError("InvalidValue should be raised with invalid params")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['login'])


class TestRevokeFromUserView(unittest.TestCase):
    """
    Test revoke permission from user.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.permissions.generate_json_response')
    @mock.patch('pulp.server.webservices.views.permissions.factory')
    def test_revoke_from_user(self, mock_factory, mock_resp):
        """
        Test revoke permissions from user.
        """
        request = mock.MagicMock()
        request.body_as_json = {'operations': ['READ'], 'login': 'test', 'resource': '/v2/some/'}
        mock_factory.permission_manager.return_value.revoke.return_value = None
        mock_factory.permission_manager.return_value.operation_names_to_values.return_value = [0]
        revoke = RevokeFromUserView()
        response = revoke.post(request)

        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)
        mock_factory.permission_manager.return_value.revoke.assert_called_once_with(
            '/v2/some/', 'test', [0])


class TestGrantToRoleView(unittest.TestCase):
    """
    Test grant permission to role.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.permissions.generate_json_response')
    @mock.patch('pulp.server.webservices.views.permissions.factory')
    def test_grant_to_role(self, mock_factory, mock_resp):
        """
        Test grant permissions to role.
        """
        request = mock.MagicMock()
        request.body_as_json = {'operations': ['READ'], 'role_id': 'test', 'resource': '/v2/some/'}
        mock_factory.role_manager.return_value.add_permissions_to_role.return_value = None
        mock_factory.permission_manager.return_value.operation_names_to_values.return_value = [0]
        grant = GrantToRoleView()
        response = grant.post(request)

        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)
        mock_factory.role_manager.return_value.add_permissions_to_role.assert_called_once_with(
            'test', '/v2/some/', [0])


class TestRevokeFromRoleView(unittest.TestCase):
    """
    Test revoke permission from role.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.permissions.generate_json_response')
    @mock.patch('pulp.server.webservices.views.permissions.factory')
    def test_revoke_from_role(self, mock_factory, mock_resp):
        """
        Test revoke permissions from role.
        """
        request = mock.MagicMock()
        request.body_as_json = {'operations': ['READ'], 'role_id': 'test', 'resource': '/v2/some/'}
        mock_factory.role_manager.return_value.remove_permissions_from_role.return_value = None
        mock_factory.permission_manager.return_value.operation_names_to_values.return_value = [0]
        revoke = RevokeFromRoleView()
        response = revoke.post(request)

        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)
        mock_factory.role_manager.return_value.remove_permissions_from_role.assert_called_once_with(
            'test', '/v2/some/', [0])
