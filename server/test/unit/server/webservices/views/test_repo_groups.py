import json
import unittest

import mock

from .base import (assert_auth_CREATE, assert_auth_DELETE, assert_auth_EXECUTE, assert_auth_READ,
                   assert_auth_UPDATE)
from pulp.common import error_codes
from pulp.server import exceptions as pulp_exceptions
from pulp.server.webservices.views.repo_groups import (
    RepoGroupAssociateView, RepoGroupDistributorResourceView, RepoGroupDistributorsView,
    RepoGroupPublishView, RepoGroupResourceView, RepoGroupsView, RepoGroupUnassociateView
)


class TestRepoGroupsView(unittest.TestCase):
    """
    Tests for RepoGroupsView.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repo_groups.reverse')
    @mock.patch('pulp.server.webservices.views.repo_groups.RepoGroupModel.get_collection')
    @mock.patch(
        'pulp.server.webservices.views.repo_groups.generate_json_response_with_pulp_encoder')
    def test_get_repo_groups(self, mock_resp, mock_collection, mock_reverse):
        """
        View should return a list of dicts, one for each repo group.
        """
        mock_collection.return_value.find.return_value = [{'id': 'group_1'}, {'id': 'group_2'}]
        mock_request = mock.MagicMock()
        mock_reverse.return_value = '/mock/path/'

        repo_groups_view = RepoGroupsView()
        response = repo_groups_view.get(mock_request)

        expected_content = [{'id': 'group_1', '_href': '/mock/path/'},
                            {'id': 'group_2', '_href': '/mock/path/'}]
        mock_resp.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch(
        'pulp.server.webservices.views.repo_groups.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repo_groups.generate_redirect_response')
    @mock.patch('pulp.server.webservices.views.repo_groups.reverse')
    @mock.patch('pulp.server.webservices.views.repo_groups.managers_factory')
    def test_post_repo_groups_only_id(self, mock_factory, mock_reverse, mock_redir, mock_resp):
        """
        Create a repo group using the minimal body.
        """
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'id': 'mock_group'})
        mock_reverse.return_value = '/mock/path/'
        mock_rg_manager = mock_factory.repo_group_manager.return_value
        mock_rg_manager.create_and_configure_repo_group.return_value = {'id': 'mock_created_group'}

        repo_groups_view = RepoGroupsView()
        response = repo_groups_view.post(mock_request)

        expected_content = {'id': 'mock_created_group', '_href': '/mock/path/', 'distributors': []}
        mock_resp.assert_called_once_with(expected_content)
        mock_redir.assert_called_once_with(mock_resp.return_value, expected_content['_href'])
        self.assertTrue(response is mock_redir.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch(
        'pulp.server.webservices.views.repo_groups.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repo_groups.generate_redirect_response')
    @mock.patch('pulp.server.webservices.views.repo_groups.reverse')
    @mock.patch('pulp.server.webservices.views.repo_groups.managers_factory')
    def test_post_repo_groups_full_data_set(self, mock_factory, mock_rev, mock_redir, mock_resp):
        """
        Create a repo group using all allowed fields.
        """
        mock_group = {'id': 'mock_group', 'display_name': 'mock_display',
                      'description': 'mock_desc', 'repo_ids': ['mock_repo_id'],
                      'notes': 'mock_notes', 'distributors': ['mock_dist']}
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps(mock_group)
        mock_rev.return_value = '/mock/path/'
        mock_rg_manager = mock_factory.repo_group_manager.return_value
        expected_data = {'id': 'mock_created_group'}
        mock_rg_manager.create_and_configure_repo_group.return_value = expected_data

        repo_groups_view = RepoGroupsView()
        response = repo_groups_view.post(mock_request)

        expected_data['_href'] = mock_rev()
        mock_resp.assert_called_once_with(expected_data)
        mock_redir.assert_called_once_with(mock_resp.return_value, expected_data['_href'])
        self.assertTrue(response is mock_redir.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    def test_post_repo_groups_extra_data(self):
        """
        Create a repo group with an invalid field.
        """
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'id': 'mock_group', 'extra_field': 'extra_data'})

        repo_groups_view = RepoGroupsView()
        try:
            repo_groups_view.post(mock_request)
        except pulp_exceptions.InvalidValue, response:
            pass
        else:
            raise AssertionError("InvalidValue should be raised if extra value passed")

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0015)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    def test_post_repo_groups_missing_id(self):
        """
        Create a repo group without an id specified.
        """
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'not_id': 'mock_group'})

        repo_groups_view = RepoGroupsView()
        try:
            repo_groups_view.post(mock_request)
        except pulp_exceptions.MissingValue, response:
            pass
        else:
            raise AssertionError("MissingValue should be raised if 'id' is not passed")

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0016)
        self.assertEqual(response.data_dict(), {'missing_property_names': ['id']})


class TestRepoGroupResourceView(unittest.TestCase):
    """
    Tests for RepoGroupResourceView.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repo_groups.reverse')
    @mock.patch(
        'pulp.server.webservices.views.repo_groups.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repo_groups.RepoGroupModel')
    def test_get_repo_group_resource(self, mock_model, mock_resp, mock_rev):
        """
        Get a repo group that exists.
        """
        mock_model.get_collection.return_value.find_one.return_value = {'id': 'mock_group'}
        mock_request = mock.MagicMock()
        mock_rev.return_value = '/mock/path/'

        repo_groups_resource = RepoGroupResourceView()
        response = repo_groups_resource.get(mock_request, 'mock_id')

        expected_content = {'id': 'mock_group', '_href': '/mock/path/'}
        mock_resp.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repo_groups.RepoGroupModel')
    def test_get_repo_group_resource_not_found(self, mock_model):
        """
        Get a repo group that does not exist.
        """
        mock_model.get_collection.return_value.find_one.return_value = None
        mock_request = mock.MagicMock()

        repo_groups_resource = RepoGroupResourceView()
        try:
            repo_groups_resource.get(mock_request, 'mock_id')
        except pulp_exceptions.MissingResource, response:
            pass
        else:
            raise AssertionError("MissingValue should be raised if 'id' is not found.")

        self.assertEqual(response.http_status_code, 404)
        self.assertTrue(response.error_code is error_codes.PLP0009)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.repo_groups.generate_json_response')
    @mock.patch('pulp.server.webservices.views.repo_groups.managers_factory')
    def test_delete_repo_group_resource(self, mock_factory, mock_resp):
        """
        Delete a repo group.
        """
        mock_manager = mock_factory.repo_group_manager.return_value
        mock_request = mock.MagicMock()

        repo_group_resource = RepoGroupResourceView()
        response = repo_group_resource.delete(mock_request, 'mock_id')

        mock_resp.assert_called_once_with(None)
        mock_manager.delete_repo_group.assert_called_once_with('mock_id')
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repo_groups.reverse')
    @mock.patch(
        'pulp.server.webservices.views.repo_groups.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repo_groups.managers_factory')
    def test_update_repo_group_resource(self, mock_factory, mock_resp, mock_rev):
        """
        Update a repo group.
        """
        mock_req = mock.MagicMock()
        mock_req.body = json.dumps({'mock': 'body'})
        mock_rev.return_value = '/mock/path/'
        mock_manager = mock_factory.repo_group_manager.return_value
        mock_manager.update_repo_group.return_value = {'mock': 'group', 'id': 'test'}

        repo_group_resource = RepoGroupResourceView()
        response = repo_group_resource.put(mock_req, 'mock_id')

        mock_resp.assert_called_once_with({'mock': 'group', '_href': '/mock/path/', 'id': 'test'})
        mock_manager.update_repo_group.assert_called_once_with('mock_id', mock='body')
        self.assertTrue(response is mock_resp.return_value)


class TestRepoGroupAssociateView(unittest.TestCase):
    """
    Tests for RepoGroupAssociateView.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.repo_groups.generate_json_response')
    @mock.patch('pulp.server.webservices.views.repo_groups.RepoGroupModel')
    @mock.patch('pulp.server.webservices.views.repo_groups.Criteria')
    @mock.patch('pulp.server.webservices.views.repo_groups.managers_factory')
    def test_post_repo_group_associate(self, mock_factory, mock_criteria, mock_model, mock_resp):
        """
        Associate a repo to a repo_group.
        """
        mock_request = mock.MagicMock()
        mock_request.body = '{}'
        mock_manager = mock_factory.repo_group_manager.return_value
        criteria = mock_criteria.from_client_input.return_value
        mock_collection = mock_model.get_collection.return_value
        mock_group = mock_collection.find_one.return_value

        repo_group_associate = RepoGroupAssociateView()
        response = repo_group_associate.post(mock_request, 'mock_id')

        mock_manager.associate.assert_called_once_with('mock_id', criteria)
        mock_resp.assert_called_once_with(mock_group['repo_ids'])
        self.assertTrue(response is mock_resp.return_value)


class TestRepoGroupUnassociateView(unittest.TestCase):
    """
    Tests for RepoGroupUnassociateView.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.repo_groups.generate_json_response')
    @mock.patch('pulp.server.webservices.views.repo_groups.RepoGroupModel')
    @mock.patch('pulp.server.webservices.views.repo_groups.Criteria')
    @mock.patch('pulp.server.webservices.views.repo_groups.managers_factory')
    def test_post_repo_group_unassociate(self, mock_factory, mock_criteria, mock_model, mock_resp):
        """
        Unassociate a repo from a repo_group.
        """
        mock_request = mock.MagicMock()
        mock_request.body = '{}'
        mock_manager = mock_factory.repo_group_manager.return_value
        criteria = mock_criteria.from_client_input.return_value
        mock_collection = mock_model.get_collection.return_value
        mock_group = mock_collection.find_one.return_value

        repo_group_unassociate = RepoGroupUnassociateView()
        response = repo_group_unassociate.post(mock_request, 'mock_id')

        mock_manager.unassociate.assert_called_once_with('mock_id', criteria)
        mock_resp.assert_called_once_with(mock_group['repo_ids'])
        self.assertTrue(response is mock_resp.return_value)


class TestRepoGroupDistributorsView(unittest.TestCase):
    """
    Tests for RepoGroupDistributorsView.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repo_groups.reverse')
    @mock.patch(
        'pulp.server.webservices.views.repo_groups.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repo_groups.managers_factory')
    def test_get_repo_group_distributors(self, mock_factory, mock_resp, mock_reverse):
        """
        Get all distributors for a repo group.
        """
        mock_request = mock.MagicMock()
        mock_dist_manager = mock_factory.repo_group_distributor_manager.return_value
        mock_dist_manager.find_distributors.return_value = [{'id': 'dist1'}, {'id': 'dist2'}]
        mock_reverse.return_value = '/mock/path/'

        repo_group_distributors = RepoGroupDistributorsView()
        response = repo_group_distributors.get(mock_request, 'mock_group_id')

        expected_content = [{'id': 'dist1', '_href': '/mock/path/'},
                            {'id': 'dist2', '_href': '/mock/path/'}]
        mock_resp.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)
        mock_dist_manager.find_distributors.assert_called_once_with('mock_group_id')

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.repo_groups.reverse')
    @mock.patch('pulp.server.webservices.views.repo_groups.generate_redirect_response')
    @mock.patch(
        'pulp.server.webservices.views.repo_groups.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repo_groups.managers_factory')
    def test_post_repo_group_distributors(self, mock_factory, mock_resp, mock_redir, mock_reverse):
        """
        Create a new repo group distributor.
        """
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({
            'distributor_type_id': 'mock_type',
            'distributor_config': 'mock_conf',
            'distributor_id': 'mock_id',
        })
        mock_dist_manager = mock_factory.repo_group_distributor_manager.return_value
        mock_dist_manager.add_distributor.return_value = {'id': 'dist1'}
        mock_reverse.return_value = '/mock/path/'

        repo_group_distributors = RepoGroupDistributorsView()
        response = repo_group_distributors.post(mock_request, 'mock_group_id')

        expected_content = {'id': 'dist1', '_href': '/mock/path/'}
        mock_resp.assert_called_once_with(expected_content)
        mock_redir.assert_called_once_with(mock_resp.return_value, mock_reverse.return_value)
        self.assertTrue(response is mock_redir.return_value)
        mock_dist_manager.add_distributor.assert_called_once_with(
            'mock_group_id', 'mock_type', 'mock_conf', 'mock_id'
        )


class TestRepoGroupDistributorResourceView(unittest.TestCase):
    """
    Tests for RepoGroupDistributorResourceView.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repo_groups.reverse')
    @mock.patch(
        'pulp.server.webservices.views.repo_groups.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repo_groups.managers_factory')
    def test_get_repo_group_distributor(self, mock_factory, mock_resp, mock_rev):
        """
        Get a single repo_groups distributor.
        """
        mock_request = mock.MagicMock()
        mock_rev.return_value = '/mock/path/'
        mock_dist_manager = mock_factory.repo_group_distributor_manager.return_value
        mock_dist_manager.get_distributor.return_value = {'id': 'dist1'}

        repo_group_distributor_resource = RepoGroupDistributorResourceView()
        response = repo_group_distributor_resource.get(mock_request, 'group_id', 'dist_id')

        expected_content = {'id': 'dist1', '_href': '/mock/path/'}
        mock_resp.assert_called_once_with(expected_content)
        mock_dist_manager.get_distributor.assert_called_once_with('group_id', 'dist_id')
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.repo_groups.reverse')
    @mock.patch('pulp.server.webservices.views.repo_groups.generate_json_response')
    @mock.patch('pulp.server.webservices.views.repo_groups.managers_factory')
    def test_delete_repo_group_distributor(self, mock_factory, mock_resp, mock_rev):
        """
        Delete a repo group distributor.
        """
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'force': True})
        mock_dist_manager = mock_factory.repo_group_distributor_manager.return_value

        repo_group_distributor_resource = RepoGroupDistributorResourceView()
        response = repo_group_distributor_resource.delete(mock_request, 'group_id', 'dist_id')

        mock_resp.assert_called_once_with(None)
        mock_dist_manager.remove_distributor.assert_called_once_with(
            'group_id', 'dist_id', force=True)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repo_groups.reverse')
    @mock.patch(
        'pulp.server.webservices.views.repo_groups.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repo_groups.managers_factory')
    def test_put_repo_group_distributor(self, mock_factory, mock_resp, mock_rev):
        """
        Modifiy a distributor with required argument.
        """
        mock_request = mock.MagicMock()
        mock_rev.return_value = '/mock/path/'
        mock_request.body = json.dumps({'distributor_config': 'mock_conf'})
        mock_dist_manager = mock_factory.repo_group_distributor_manager.return_value
        mock_dist_manager.update_distributor_config.return_value = {'updated': 'distributor'}

        repo_group_distributor_resource = RepoGroupDistributorResourceView()
        response = repo_group_distributor_resource.put(mock_request, 'group_id', 'dist_id')

        expected_content = {'updated': 'distributor', '_href': '/mock/path/'}
        mock_resp.assert_called_once_with(expected_content)
        mock_dist_manager.update_distributor_config.assert_called_once_with(
            'group_id', 'dist_id', 'mock_conf')
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repo_groups.generate_json_response')
    @mock.patch('pulp.server.webservices.views.repo_groups.managers_factory')
    def test_put_repo_group_distributor_no_config_specified(self, mock_factory, mock_resp):
        """
        Modifiy a distributor without specifying the distributor_config.
        """
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'no_dist_config': 'mock_conf'})

        repo_group_distributor_resource = RepoGroupDistributorResourceView()

        try:
            repo_group_distributor_resource.put(mock_request, 'group_id', 'dist_id')
        except pulp_exceptions.MissingValue, response:
            pass
        else:
            raise AssertionError("MissingValue should be raised if distributor_config is"
                                 "not passed")

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0016)
        self.assertEqual(response.data_dict(), {'missing_property_names': ['distributor_config']})


class TestRepoGroupPublishView(unittest.TestCase):
    """
    Tests for RepoGroupPublishView.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.repo_groups.tags')
    @mock.patch('pulp.server.webservices.views.repo_groups.repo_group_publish')
    @mock.patch('pulp.server.webservices.views.repo_groups.managers_factory')
    def test_post_repo_group_publish(self, mock_manager, mock_repo_group_publish, mock_tags):
        """
        Publish a repo group with all available params.
        """
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'id': 'dist_id', 'override_config': 'mock_overrides'})
        mock_task_tags = [
            mock_tags.resource_tag(mock_tags.RESOURCE_REPOSITORY_GROUP_TYPE, 'group_id'),
            mock_tags.resource_tag(mock_tags.RESOURCE_REPOSITORY_GROUP_DISTRIBUTOR_TYPE, 'dist'),
            mock_tags.action_tag('publish')
        ]
        repo_group_publish = RepoGroupPublishView()
        try:
            repo_group_publish.post(mock_request, 'group_id')
        except pulp_exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError("OperationPostponed should be raised.")

        self.assertEqual(response.http_status_code, 202)
        mock_repo_group_publish.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_GROUP_TYPE,
            'group_id',
            args=['group_id', 'dist_id'],
            kwargs={'publish_config_override': 'mock_overrides'},
            tags=mock_task_tags
        )

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    def test_post_repo_group_publish_missing_distributor_id(self):
        """
        Test publishing a repo group without distributor_id in the params.
        """
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'not_dist_id': 'mock'})

        repo_group_publish = RepoGroupPublishView()

        try:
            repo_group_publish.post(mock_request, 'group_id')
        except pulp_exceptions.MissingValue, response:
            pass
        else:
            raise AssertionError("MissingValue should be raised if distributor_config is"
                                 "not passed")

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0016)
        self.assertEqual(response.data_dict(), {'missing_property_names': ['id']})
