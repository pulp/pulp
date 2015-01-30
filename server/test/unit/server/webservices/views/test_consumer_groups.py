import unittest

import mock
from django.http import HttpResponseBadRequest

from base import (assert_auth_CREATE, assert_auth_READ, assert_auth_UPDATE, assert_auth_DELETE,
                  assert_auth_EXECUTE)
from pulp.server.exceptions import OperationPostponed, MissingResource, InvalidValue
from pulp.server.webservices.views.consumer_groups import (ConsumerGroupAssociateActionView,
                                                           ConsumerGroupBindingView,
                                                           ConsumerGroupBindingsView,
                                                           ConsumerGroupContentActionView,
                                                           ConsumerGroupResourceView,
                                                           ConsumerGroupUnassociateActionView)


class TestconsumerGroupResourceView(unittest.TestCase):
    """
    Test consumer groups resource view.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.consumer_groups.generate_json_response')
    @mock.patch('pulp.server.webservices.views.consumer_groups.factory')
    def test_delete_consumer_group_resource(self, mock_factory, mock_resp):
        """
        Test consumer group delete resource.
        """
        mock_group_manager = mock.MagicMock()
        mock_factory.consumer_group_manager.return_value = mock_group_manager
        mock_group_manager.delete_consumer_group.return_value = None

        request = mock.MagicMock()
        consumer_group_resource = ConsumerGroupResourceView()
        response = consumer_group_resource.delete(request, 'test-group')

        mock_group_manager.delete_consumer_group.assert_called_once_with('test-group')

        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.consumer_groups.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumer_groups.ConsumerGroup.get_collection')
    def test_get_consumer_group_resource(self, mock_collection, mock_resp):
        """
        Test single consumer group retrieval.
        """
        consumer_mock = mock.MagicMock()
        consumer_mock.find_one.return_value = {'id': 'foo'}
        mock_collection.return_value = consumer_mock

        request = mock.MagicMock()
        consumer_group = ConsumerGroupResourceView()
        response = consumer_group.get(request, 'foo')

        expected_cont = {'id': 'foo', '_href': '/v2/consumer_groups/foo/'}

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumer_groups.ConsumerGroup.get_collection')
    def test_get_invalid_consumer_group_resource(self, mock_collection):
        """
        Test nonexistent consumer group retrieval.
        """
        mock_collection.return_value.find_one.return_value = None

        request = mock.MagicMock()
        consumer_group = ConsumerGroupResourceView()
        try:
            response = consumer_group.get(request, 'nonexistent_id')
        except MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised with nonexistent_group")

        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'consumer_group': 'nonexistent_id'})

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch(
        'pulp.server.webservices.views.consumer_groups.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumer_groups.factory')
    def test_update_consumer_group(self, mock_factory, mock_resp):
        """
        Test consumer group update.
        """
        resp = {'id': 'foo', 'display_name': 'bar'}
        expected_cont = {'id': 'foo', 'display_name': 'bar', '_href': '/v2/consumer_groups/foo/'}

        request = mock.MagicMock()
        request.body_as_json = {'display_name': 'bar'}
        mock_factory.consumer_group_manager.return_value.update_consumer_group.return_value = resp
        consumer_group = ConsumerGroupResourceView()
        response = consumer_group.put(request, 'foo')

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)


class TestConsumerGroupAssociateActionView(unittest.TestCase):
    """
    Tests consumer group membership.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch(
        'pulp.server.webservices.views.consumer_groups.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumer_groups.factory')
    def test_cons_group_association_view(self, mock_factory, mock_resp):
        """
        Test consumer group associate a consumer.
        """
        grp = {'id': 'my-group', 'consumer_ids': ['c1']}
        mock_factory.consumer_group_manager.return_value.associate.return_value = 'ok'
        mock_factory.consumer_group_query_manager.return_value.get_group.return_value = grp
        request = mock.MagicMock()
        request.body_as_json = {'criteria': {'filters': {'id': 'c1'}}}
        consumer_group_associate = ConsumerGroupAssociateActionView()
        response = consumer_group_associate.post(request, 'my-group')

        mock_resp.assert_called_once_with(['c1'])
        self.assertTrue(response is mock_resp.return_value)


class TestConsumerGroupUnassociateActionView(unittest.TestCase):
    """
    Tests consumer group membership.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch(
        'pulp.server.webservices.views.consumer_groups.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumer_groups.factory')
    def test_cons_group_unassociation_view(self, mock_factory, mock_resp):
        """
        Test consumer group unassociate a consumer.
        """
        grp = {'id': 'my-group', 'consumer_ids': []}
        mock_factory.consumer_group_manager.return_value.unassociate.return_value = 'ok'
        mock_factory.consumer_group_query_manager.return_value.get_group.return_value = grp
        request = mock.MagicMock()
        request.body_as_json = {'criteria': {'filters': {'id': 'c1'}}}
        consumer_group_unassociate = ConsumerGroupUnassociateActionView()
        response = consumer_group_unassociate.post(request, 'my-group')

        mock_resp.assert_called_once_with([])
        self.assertTrue(response is mock_resp.return_value)


class TestConsumerGroupBindingsView(unittest.TestCase):
    """
    Represents consumer group binding.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumer_groups.factory')
    def test_verify_group_resources_repo(self, mock_factory):
        """
        Test verify group resources with repo missing.
        """
        mock_factory.consumer_group_query_manager.return_value.get_group.return_value = 'test-group'
        mock_factory.repo_query_manager.return_value.find_by_id.return_value = None
        mock_factory.repo_distributor_manager.return_value.get_distributor.return_value = 'yyy'
        request = mock.MagicMock()
        request.body_as_json = {'repo_id': 'xxx', 'distributor_id': 'yyy'}
        bind_view = ConsumerGroupBindingsView()
        try:
            response = bind_view.post(request, 'test-group')
        except InvalidValue, response:
            pass
        else:
            raise AssertionError("InvalidValue should be raised with nonexistent resources")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['repo_id'])

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumer_groups.factory')
    def test_verify_group_resources_distributor(self, mock_f):
        """
        Test verify group resources with distributor missing.
        """
        mock_f.consumer_group_query_manager.return_value.get_group.return_value = 'test'
        mock_f.repo_query_manager.return_value.find_by_id.return_value = 'xxx'
        mock_f.repo_distributor_manager.return_value.get_distributor.side_effect = MissingResource
        request = mock.MagicMock()
        request.body_as_json = {'repo_id': 'xxx', 'distributor_id': 'yyy'}
        bind_view = ConsumerGroupBindingsView()
        try:
            response = bind_view.post(request, 'test-group')
        except InvalidValue, response:
            pass
        else:
            raise AssertionError("InvalidValue should be raised with nonexistent resources")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['distributor_id'])

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumer_groups.factory')
    def test_verify_group_resources_group(self, mock_f):
        """
        Test verify group resources with group id missing.
        """
        mock_f.consumer_group_query_manager.return_value.get_group.side_effect = MissingResource
        mock_f.repo_query_manager.return_value.find_by_id.return_value = 'xxx'
        mock_f.repo_distributor_manager.return_value.get_distributor.return_value = 'yyy'
        request = mock.MagicMock()
        request.body_as_json = {'repo_id': 'xxx', 'distributor_id': 'yyy'}
        bind_view = ConsumerGroupBindingsView()
        try:
            response = bind_view.post(request, 'test-group')
        except MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised with nonexistent resources")
        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'group_id': 'test-group'})

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumer_groups.bind')
    @mock.patch('pulp.server.webservices.views.consumer_groups.verify_group_resources')
    def test_create_binding(self, mock_resources, mock_bind):
        """
        Test bind consumer group to a repo.
        """
        mock_resources.return_value = {}
        request = mock.MagicMock()
        request.body_as_json = {'repo_id': 'xxx', 'distributor_id': 'yyy'}
        bind_view = ConsumerGroupBindingsView()
        self.assertRaises(OperationPostponed, bind_view.post, request, 'test-group')
        bind_args_tuple = ('test-group', 'xxx', 'yyy', True, None, {})
        mock_bind.apply_async.assert_called_once_with(bind_args_tuple)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumer_groups.verify_group_resources')
    def test_create_binding_with_missing_group_id(self, mock_resources):
        """
        Test bind consumer group to a repo when group id missing.
        """
        mock_resources.return_value = {'group_id': 'nonexistent_id'}
        request = mock.MagicMock()
        bind_view = ConsumerGroupBindingsView()
        try:
            response = bind_view.post(request, 'nonexistent_id')
        except MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised with nonexistent_group")
        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'group_id': 'nonexistent_id'})

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumer_groups.verify_group_resources')
    def test_create_binding_with_missing_repo_id(self, mock_resources):
        """
        Test bind consumer group to a repo when repo id is missing.
        """
        mock_resources.return_value = {'repo_id': 'nonexistent_id'}
        request = mock.MagicMock()
        bind_view = ConsumerGroupBindingsView()
        try:
            response = bind_view.post(request, 'test-group')
        except InvalidValue, response:
            pass
        else:
            raise AssertionError("InvalidValue  should be raised with nonexistent_repo")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['repo_id'])

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumer_groups.verify_group_resources')
    def test_create_binding_with_invalid_param(self, mock_resources):
        """
        Test bind consumer group to a repo witn invalid parameters.
        """
        mock_resources.return_value = {'invalid_param': 'foo'}
        request = mock.MagicMock()
        bind_view = ConsumerGroupBindingsView()
        try:
            response = bind_view.post(request, 'test-group')
        except InvalidValue, response:
            pass
        else:
            raise AssertionError("Invalidvalue should be raised with invalid options")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['invalid_param'])


class TestConsumerGroupBindingView(unittest.TestCase):
    """
    Represents a specific consumer group binding.
    """
    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.consumer_groups.unbind')
    @mock.patch('pulp.server.webservices.views.consumer_groups.verify_group_resources')
    def test_delete_binding(self, mock_resources, mock_unbind):
        """
        Test consumer group binding removal.
        """
        mock_resources.return_value = {}
        request = mock.MagicMock()
        unbind_view = ConsumerGroupBindingView()
        self.assertRaises(OperationPostponed, unbind_view.delete, request,
                          "consumer_group_id", "repo_id", "distributor_id")
        unbind_args_tuple = ("consumer_group_id", "repo_id", "distributor_id", {})
        mock_unbind.apply_async.assert_called_once_with(unbind_args_tuple)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.consumer_groups.verify_group_resources')
    def test_delete_non_existent_binding(self, mock_resources):
        """
        Test consumer group nonexistent binding removal.
        """
        mock_resources.return_value = {'repo_id': 'no_such_repo'}
        request = mock.MagicMock()
        unbind_view = ConsumerGroupBindingView()
        try:
            response = unbind_view.delete(request, 'test-group', 'no_such_repo', 'dist_id')
        except MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised with missing options")
        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'repo_id': 'no_such_repo'})


class TestConsumerGroupContentActionView(unittest.TestCase):
    """
    Test Consumer group content manipulation.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    def test_consumer_group_bad_request_content(self):
        """
        Test consumer group invalid content action.
        """
        request = mock.MagicMock()
        consumer_group_content = ConsumerGroupContentActionView()
        response = consumer_group_content.post(request, 'my-group', 'no_such_action')
        self.assertTrue(isinstance(response, HttpResponseBadRequest))
        self.assertEqual(response.status_code, 400)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumer_groups.factory')
    def test_consumer_group_content_install(self, mock_factory):
        """
        Test consumer group content installation.
        """
        mock_factory.consumer_group_manager.return_value.install_content.return_value = 'ok'
        request = mock.MagicMock()
        request.body_as_json = {"units": [], "options": {}}
        consumer_group_content = ConsumerGroupContentActionView()
        self.assertRaises(OperationPostponed, consumer_group_content.post, request,
                          'my-group', 'install')
        mock_factory.consumer_group_manager().install_content.assert_called_once_with(
            'my-group', [], {})

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumer_groups.factory')
    def test_consumer_group_content_update(self, mock_factory):
        """
        Test consumer group content update.
        """
        mock_factory.consumer_group_manager.return_value.update_content.return_value = 'ok'
        request = mock.MagicMock()
        request.body_as_json = {"units": [], "options": {}}
        consumer_group_content = ConsumerGroupContentActionView()
        self.assertRaises(OperationPostponed, consumer_group_content.post, request,
                          'my-group', 'update')
        mock_factory.consumer_group_manager().update_content.assert_called_once_with(
            'my-group', [], {})

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumer_groups.factory')
    def test_consumer_group_content_uninstall(self, mock_factory):
        """
        Test consumer group content uninstall.
        """
        mock_factory.consumer_group_manager.return_value.uninstall_content.return_value = 'ok'
        request = mock.MagicMock()
        request.body_as_json = {"units": [], "options": {}}
        consumer_group_content = ConsumerGroupContentActionView()
        self.assertRaises(OperationPostponed, consumer_group_content.post, request,
                          'my-group', 'uninstall')
        mock_factory.consumer_group_manager().uninstall_content.assert_called_once_with(
            'my-group', [], {})
