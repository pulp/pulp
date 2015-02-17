import json
import unittest

import mock

from base import assert_auth_CREATE, assert_auth_DELETE, assert_auth_READ, assert_auth_UPDATE
from pulp.server.exceptions import InvalidValue, MissingResource
from pulp.server.webservices.views.roles import (RoleResourceView, RoleUserView, RoleUsersView,
                                                 RolesView)


class TestRolesView(unittest.TestCase):
    """
    Test roles view.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.roles.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.roles.factory')
    def test_get_all_roles(self, mock_f, mock_resp):
        """
        Test the roles retrieval.
        """
        resp = [{'id': 'test_role', 'users': [{'login': 'test'}],
                'permissions': [{'resource': '/', 'permission': [0]}]}]
        users = [{'login': 'test'}]
        mock_f.role_query_manager.return_value.find_all.return_value = resp
        mock_f.user_query_manager.return_value.find_users_belonging_to_role.return_value = users
        mock_f.permission_manager.return_value.operation_value_to_name.return_value = 'READ'

        request = mock.MagicMock()
        roles = RolesView()
        response = roles.get(request)
        expected_cont = [{'id': 'test_role', 'permissions': {'/': ['READ']}, 'users': ['test'],
                         '_href': '/v2/roles/test_role/'}]

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.roles.generate_redirect_response')
    @mock.patch('pulp.server.webservices.views.roles.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.roles.factory')
    def test_create_role(self, mock_factory, mock_resp, mock_redirect):
        """
        Test role creation.
        """
        resp = {'id': 'foo', 'display_name': 'bar'}
        expected_cont = {'id': 'foo', 'display_name': 'bar', '_href': '/v2/roles/foo/'}

        request = mock.MagicMock()
        request.body = json.dumps({'role_id': 'foo', 'display_name': 'bar'})
        mock_factory.role_manager.return_value.create_role.return_value = resp
        create_role = RolesView()
        response = create_role.post(request)

        mock_resp.assert_called_once_with(expected_cont)
        mock_redirect.assert_called_once_with(mock_resp.return_value, expected_cont['_href'])
        self.assertTrue(response is mock_redirect.return_value)


class TestRoleResourceView(unittest.TestCase):
    """
    Test role resource view.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.roles.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.roles.factory')
    def test_get_single_role(self, mock_f, mock_resp):
        """
        Test single role retrieval.
        """
        resp = {'id': 'test_role', 'users': [{'login': 'test'}],
                'permissions': [{'resource': '/', 'permission': [0]}]}
        users = [{'login': 'test'}]
        mock_f.role_query_manager.return_value.find_by_id.return_value = resp
        mock_f.user_query_manager.return_value.find_users_belonging_to_role.return_value = users
        mock_f.permission_manager.return_value.operation_value_to_name.return_value = 'READ'

        request = mock.MagicMock()
        role = RoleResourceView()
        response = role.get(request, 'test_role')
        expected_cont = {'id': 'test_role', 'permissions': {'/': ['READ']}, 'users': ['test'],
                         '_href': '/v2/roles/test_role/'}

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.roles.factory')
    def test_get_nonexistent_role(self, mock_factory):
        """
        Test invalid role retrieval.
        """
        mock_factory.role_query_manager.return_value.find_by_id.return_value = None

        request = mock.MagicMock()
        role = RoleResourceView()

        try:
            response = role.get(request, 'nonexistent_id')
        except MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised with nonexistent_role")

        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'resource_id': 'nonexistent_id'})

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.roles.generate_json_response')
    @mock.patch('pulp.server.webservices.views.roles.factory')
    def test_role_deletion(self, mock_factory, mock_resp):
        """
        Test role deletion.
        """
        mock_factory.role_manager.return_value.delete_role.return_value = None

        request = mock.MagicMock()
        role_resource = RoleResourceView()
        response = role_resource.delete(request, 'test-role')

        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)
        mock_factory.role_manager.return_value.delete_role.assert_called_once_with('test-role')

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.roles.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.roles.factory')
    def test_update_role(self, mock_factory, mock_resp):
        """
        Test role update.
        """
        resp = {'id': 'foo', 'display_name': 'bar'}
        expected_cont = {'id': 'foo', 'display_name': 'bar', '_href': '/v2/roles/foo/'}

        request = mock.MagicMock()
        request.body = json.dumps({'display_name': 'bar'})
        mock_factory.role_manager.return_value.update_role.return_value = resp
        role_resource = RoleResourceView()
        response = role_resource.put(request, 'foo')

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)


class TestRoleUsersView(unittest.TestCase):
    """
    Test users membership within a role.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.roles.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.roles.factory')
    def test_list_users_beloging_to_role(self, mock_fact, mock_resp):
        """
        Test list Users belonging to a role.
        """
        resp = {'login': 'foo', 'name': 'bar'}
        expected_cont = {'login': 'foo', 'name': 'bar'}

        mock_fact.user_query_manager.return_value.find_users_belonging_to_role.return_value = resp
        request = mock.MagicMock()
        role_users = RoleUsersView()
        response = role_users.get(request, 'test-role')

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.roles.generate_json_response')
    @mock.patch('pulp.server.webservices.views.roles.factory')
    def test_add_user_to_role(self, mock_factory, mock_resp):
        """
        Test add user to a role.
        """
        mock_factory.role_manager.return_value.add_user_to_role.return_value = None

        request = mock.MagicMock()
        request.body = json.dumps({'login': 'test-user'})
        role_users = RoleUsersView()
        response = role_users.post(request, 'test-role')

        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_UPDATE())
    def test_add_invalid_user_to_role(self):
        """
        Test add invalid user to a role.
        """
        request = mock.MagicMock()
        request.body = json.dumps({'login': None})
        role_users = RoleUsersView()

        try:
            response = role_users.post(request, 'test-role')
        except InvalidValue, response:
            pass
        else:
            raise AssertionError("InvalidValue should be raised with invalid options")

        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], [None])


class TestRoleUserView(unittest.TestCase):
    """
    Test single user membership within a role.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.roles.generate_json_response')
    @mock.patch('pulp.server.webservices.views.roles.factory')
    def test_remove_user_from_role(self, mock_factory, mock_resp):
        """
        Test remove user from  a role.
        """
        mock_factory.role_manager.return_value.remove_user_from_role.return_value = None

        request = mock.MagicMock()
        role_user = RoleUserView()
        response = role_user.delete(request, 'test-role', 'test-user')

        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)
