import json
import unittest

import mock
from django.http import HttpResponseBadRequest

from base import assert_auth_CREATE, assert_auth_DELETE, assert_auth_READ, assert_auth_UPDATE
from pulp.server.exceptions import (InvalidValue, MissingResource, MissingValue,
                                    OperationPostponed, UnsupportedValue)
from pulp.server.managers.consumer import bind
from pulp.server.managers.consumer import profile
from pulp.server.managers.consumer import query
from pulp.server.webservices.views import consumers
from pulp.server.webservices.views import util
from pulp.server.webservices.views.consumers import (ConsumersView, ConsumerBindingsView,
                                                     ConsumerRepoBindingView,
                                                     ConsumerBindingResourceView,
                                                     ConsumerBindingSearchView,
                                                     ConsumerContentActionView,
                                                     ConsumerContentApplicabilityView,
                                                     ConsumerContentApplicRegenerationView,
                                                     ConsumerHistoryView, ConsumerProfilesView,
                                                     ConsumerProfileResourceView,
                                                     ConsumerProfileSearchView,
                                                     ConsumerResourceView,
                                                     ConsumerResourceContentApplicRegenerationView,
                                                     ConsumerSearchView,
                                                     UnitInstallSchedulesView,
                                                     UnitInstallScheduleResourceView)


class Test_expand_consumers(unittest.TestCase):
    """
    Test that using query params will expand proper consumer info.
    """
    @mock.patch('pulp.server.webservices.views.consumers.serial_binding')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_bind_manager')
    def test_expand_consumers(self, mock_factory, mock_serial):
        """
        Test for consumer info expansion with details/bindings
        """
        consumers_list = [{'id': 'c1'}]
        bindings = [{'consumer_id': 'c1', 'repo_id': 'repo1', 'distributor_id': 'dist1'}]
        mock_factory.return_value.find_by_criteria.return_value = bindings
        mock_serial.serialize.return_value = {'consumer_id': 'c1', 'repo_id': 'repo1',
                                              'distributor_id': 'dist1',
                                              '_href': '/some/c1/some_bind/'}

        cons = consumers.expand_consumers(True, False, consumers_list)
        expected_cons = [{'id': 'c1', 'bindings': [{'consumer_id': 'c1', 'repo_id': 'repo1',
                         'distributor_id': 'dist1', '_href': '/some/c1/some_bind/'}]}]
        self.assertEqual(cons, expected_cons)


class TestConsumersView(unittest.TestCase):
    """
    Test consumers view.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.expand_consumers')
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_query_manager')
    def test_get_all_consumers(self, mock_factory, mock_resp, mock_expand):
        """
        Test the consumers retrieval.
        """
        consumer_mock = mock.MagicMock()
        resp = [{'id': 'foo', 'display_name': 'bar'}]
        consumer_mock.find_all.return_value = resp
        mock_factory.return_value = consumer_mock
        mock_expand.return_value = resp

        request = mock.MagicMock()
        request.GET = {}
        consumers = ConsumersView()
        response = consumers.get(request)

        expected_cont = [{'id': 'foo', 'display_name': 'bar', '_href': '/v2/consumers/foo/'}]
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.serial_binding')
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_get_all_consumers_details_true(self, mock_factory, mock_resp, mock_serial):
        """
        Test the consumers retrieval and include details.
        """
        consumer_mock = mock.MagicMock()
        resp = [{'id': 'foo', 'display_name': 'bar'}]
        consumer_mock.find_all.return_value = resp
        mock_factory.consumer_query_manager.return_value = consumer_mock
        mock_serial.serialize.return_value = []
        mock_factory.consumer_bind_manager.return_value.find_by_criteria.return_value = []

        request = mock.MagicMock()
        request.GET = {'details': 'true'}
        consumers = ConsumersView()
        response = consumers.get(request)

        expected_cont = [{'id': 'foo', 'display_name': 'bar', '_href': '/v2/consumers/foo/',
                         'bindings': []}]
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_get_all_consumers_details_false(self, mock_factory, mock_resp):
        """
        Test the consumers retrieval and exclude details
        """
        consumer_mock = mock.MagicMock()
        resp = [{'id': 'foo', 'display_name': 'bar'}]
        consumer_mock.find_all.return_value = resp
        mock_factory.consumer_query_manager.return_value = consumer_mock

        request = mock.MagicMock()
        request.GET = {'details': 'false'}
        consumers = ConsumersView()
        response = consumers.get(request)

        expected_cont = [{'id': 'foo', 'display_name': 'bar', '_href': '/v2/consumers/foo/'}]
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.serial_binding')
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_get_all_consumers_bindings_true(self, mock_factory, mock_resp, mock_serial):
        """
        Test the consumers retrieval and include bindings
        """
        consumer_mock = mock.MagicMock()
        resp = [{'id': 'foo', 'display_name': 'bar'}]
        consumer_mock.find_all.return_value = resp
        mock_factory.consumer_query_manager.return_value = consumer_mock
        mock_serial.serialize.return_value = []
        mock_factory.consumer_bind_manager.return_value.find_by_criteria.return_value = []

        request = mock.MagicMock()
        request.GET = {'bindings': 'true'}
        consumers = ConsumersView()
        response = consumers.get(request)

        expected_cont = [{'id': 'foo', 'display_name': 'bar', '_href': '/v2/consumers/foo/',
                         'bindings': []}]
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_get_all_consumers_bindings_false(self, mock_factory, mock_resp):
        """
        Test the consumers retrieval and exclude bindings
        """
        consumer_mock = mock.MagicMock()
        resp = [{'id': 'foo', 'display_name': 'bar'}]
        consumer_mock.find_all.return_value = resp
        mock_factory.consumer_query_manager.return_value = consumer_mock

        request = mock.MagicMock()
        request.GET = {'bindings': 'false'}
        consumers = ConsumersView()
        response = consumers.get(request)

        expected_cont = [{'id': 'foo', 'display_name': 'bar', '_href': '/v2/consumers/foo/'}]
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_get_all_consumers_bindings_not_boolean(self, mock_factory, mock_resp):
        """
        Test the consumers retrieval with invalid boolean query param
        """
        consumer_mock = mock.MagicMock()
        resp = [{'id': 'foo', 'display_name': 'bar'}]
        consumer_mock.find_all.return_value = resp
        mock_factory.consumer_query_manager.return_value = consumer_mock

        request = mock.MagicMock()
        request.GET = {'bindings': 'not_boolean'}
        consumers = ConsumersView()
        response = consumers.get(request)

        expected_cont = [{'id': 'foo', 'display_name': 'bar', '_href': '/v2/consumers/foo/'}]
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.generate_redirect_response')
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    def test_create_consumer(self, mock_factory, mock_resp, mock_redirect):
        """
        Test consumer creation.
        """
        cons = {'id': 'foo', 'display_name': 'bar'}
        cert = '12345'
        expected_cont = {'consumer': {'id': 'foo', 'display_name': 'bar',
                         '_href': '/v2/consumers/foo/'}, 'certificate': '12345'}

        request = mock.MagicMock()
        request.body = json.dumps({'id': 'foo', 'display_name': 'bar'})
        mock_factory.return_value.register.return_value = cons, cert
        consumers = ConsumersView()
        response = consumers.post(request)
        mock_resp.assert_called_once_with(expected_cont)
        mock_redirect.assert_called_once_with(mock_resp.return_value,
                                              expected_cont['consumer']['_href'])
        self.assertTrue(response is mock_redirect.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    def test_create_consumer_missing_param(self):
        """
        Test consumer creation with missing required id.
        """
        request = mock.MagicMock()
        request.body = json.dumps({'display_name': 'bar'})
        consumers = ConsumersView()
        try:
            response = consumers.post(request)
        except MissingValue, response:
            pass
        else:
            raise AssertionError("MissingValue should be raised with missing options")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['id'])


class TestConsumerResourceView(unittest.TestCase):
    """
    Test consumer resource view.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.consumers.generate_json_response')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_delete_consumer_resource(self, mock_factory, mock_resp):
        """
        Test consumer delete resource.
        """
        mock_consumer_manager = mock.MagicMock()
        mock_factory.consumer_manager.return_value = mock_consumer_manager
        mock_consumer_manager.unregister.return_value = None

        request = mock.MagicMock()
        consumer_resource = ConsumerResourceView()
        response = consumer_resource.delete(request, 'test-consumer')

        mock_consumer_manager.unregister.assert_called_once_with('test-consumer')

        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    def test_get_consumer_resource(self, mock_collection, mock_resp):
        """
        Test single consumer retrieval.
        """
        mock_collection.return_value.get_consumer.return_value = {'id': 'foo'}

        request = mock.MagicMock()
        request.GET = {}
        consumer_resource = ConsumerResourceView()
        response = consumer_resource.get(request, 'foo')

        expected_cont = {'id': 'foo', '_href': '/v2/consumers/foo/'}

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.serial_binding')
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_get_consumer_resource_with_details(self, mock_factory, mock_resp, mock_serial):
        """
        Test single consumer retrieval with query param details true
        """
        mock_factory.consumer_manager.return_value.get_consumer.return_value = {'id': 'foo'}
        mock_serial.serialize.return_value = []
        mock_factory.consumer_bind_manager.return_value.find_by_criteria.return_value = []

        request = mock.MagicMock()
        request.GET = {'details': 'true'}
        consumer_resource = ConsumerResourceView()
        response = consumer_resource.get(request, 'foo')

        expected_cont = {'id': 'foo', '_href': '/v2/consumers/foo/', 'bindings': []}

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.serial_binding')
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_get_consumer_resource_with_bindings(self, mock_factory, mock_resp, mock_serial):
        """
        Test single consumer retrieval with query param bindings true
        """
        mock_factory.consumer_manager.return_value.get_consumer.return_value = {'id': 'foo'}
        mock_serial.serialize.return_value = []
        mock_factory.consumer_bind_manager.return_value.find_by_criteria.return_value = []

        request = mock.MagicMock()
        request.GET = {'bindings': 'true'}
        consumer_resource = ConsumerResourceView()
        response = consumer_resource.get(request, 'foo')

        expected_cont = {'id': 'foo', '_href': '/v2/consumers/foo/', 'bindings': []}

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    def test_get_consumer_resource_with_details_false(self, mock_collection, mock_resp):
        """
        Test single consumer retrieval with query param details false
        """
        mock_collection.return_value.get_consumer.return_value = {'id': 'foo'}

        request = mock.MagicMock()
        request.GET = {'details': 'false'}
        consumer_resource = ConsumerResourceView()
        response = consumer_resource.get(request, 'foo')

        expected_cont = {'id': 'foo', '_href': '/v2/consumers/foo/'}

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    def test_get_consumer_resource_with_bindings_false(self, mock_collection, mock_resp):
        """
        Test single consumer retrieval with query param bindings false
        """
        mock_collection.return_value.get_consumer.return_value = {'id': 'foo'}

        request = mock.MagicMock()
        request.GET = {'bingings': 'false'}
        consumer_resource = ConsumerResourceView()
        response = consumer_resource.get(request, 'foo')

        expected_cont = {'id': 'foo', '_href': '/v2/consumers/foo/'}

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_update_consumer(self, mock_factory, mock_resp):
        """
        Test consumer update.
        """
        resp = {'id': 'foo', 'display_name': 'bar'}
        expected_cont = {'id': 'foo', 'display_name': 'bar', '_href': '/v2/consumers/foo/'}

        request = mock.MagicMock()
        request.body = json.dumps({'delta': {'display_name': 'bar'}})
        mock_factory.consumer_manager.return_value.update.return_value = resp
        consumer_resource = ConsumerResourceView()
        response = consumer_resource.put(request, 'foo')

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)


class TestConsumerSearchView(unittest.TestCase):
    """
    Test the ConsumerSearchView.
    """
    def test_class_attributes(self):
        """
        Ensure that the ConsumerSearchView has the correct class attributes.
        """
        self.assertEqual(ConsumerSearchView.response_builder,
                         util.generate_json_response_with_pulp_encoder)
        self.assertEqual(ConsumerSearchView.optional_bool_fields, ('details', 'bindings'))
        self.assertTrue(isinstance(ConsumerSearchView.manager, query.ConsumerQueryManager))

    @mock.patch('pulp.server.webservices.views.consumers.add_link')
    @mock.patch('pulp.server.webservices.views.consumers.expand_consumers')
    def test_get_results(self, mock_expand, mock_add_link):
        """
        Test that results are expanded and serialized.
        """
        query = mock.MagicMock()
        search_method = mock.MagicMock()
        mock_expand.return_value = ['result_1', 'result_2']
        options = {'mock': 'options'}

        consumer_search = ConsumerSearchView()
        serialized_results = consumer_search.get_results(query, search_method, options)
        mock_expand.assert_called_once_with(False, False, list(search_method.return_value))
        mock_add_link.assert_has_calls([mock.call('result_1'), mock.call('result_2')])
        self.assertEqual(serialized_results, mock_expand.return_value)


class TestConsumerBindingSearchView(unittest.TestCase):
    """
    Test the ConsumerBindingSearchView.
    """
    def test_class_attributes(self):
        """
        Ensure that the ConsumerBindingSearchView has the correct class attributes.
        """
        self.assertEqual(ConsumerBindingSearchView.response_builder,
                         util.generate_json_response_with_pulp_encoder)
        self.assertTrue(isinstance(ConsumerBindingSearchView.manager, bind.BindManager))


class TestConsumerRepoBindingView(unittest.TestCase):
    """
    Test the retrieval of bindings between consumer and repository.
    """
    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.serial_binding')
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    @mock.patch('pulp.server.webservices.views.consumers.model.Repository.objects')
    def test_get_consumer_bindings_by_repoid(self, mock_repo_qs, mock_factory, mock_resp,
                                             mock_serial):
        """
        Test all bindings retrieval by repo-id
        """
        mock_factory.consumer_manager.return_value.get_consumer.return_value = {'id': 'foo'}
        bindings = [{'repo_id': 'some-repo', 'consumer_id': 'foo'}]
        mock_factory.consumer_bind_manager.return_value.find_by_consumer.return_value = bindings
        mock_repo_qs.get_repo_or_missing_resource.return_value = 'some-repo'
        serial_resp = {'consumer_id': 'foo', 'repo_id': 'some-repo',
                       '_href': '/v2/consumers/foo/bindings/some-repo/'}
        mock_serial.serialize.return_value = serial_resp

        request = mock.MagicMock()
        consumer_binding = ConsumerRepoBindingView()
        response = consumer_binding.get(request, 'foo', 'some-repo')

        expected_cont = [{'consumer_id': 'foo',
                          '_href': '/v2/consumers/foo/bindings/some-repo/',
                          'repo_id': 'some-repo'}]

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)


class TestConsumerBindingsView(unittest.TestCase):
    """
    Represents consumers binding.
    """
    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.serial_binding')
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_get_consumer_bindings(self, mock_factory, mock_resp, mock_serial):
        """
        Test all bindings retrieval
        """
        mock_factory.consumer_manager.return_value.get_consumer.return_value = {'id': 'foo'}
        bindings = [{'repo_id': 'some-repo', 'consumer_id': 'foo'}]
        mock_factory.consumer_bind_manager.return_value.find_by_consumer.return_value = bindings
        serial_resp = {'consumer_id': 'foo', 'repo_id': 'some-repo',
                       '_href': '/v2/consumers/foo/bindings/some-repo/dist1/'}
        mock_serial.serialize.return_value = serial_resp

        request = mock.MagicMock()
        consumer_bindings = ConsumerBindingsView()
        response = consumer_bindings.get(request, 'foo')

        expected_cont = [{'consumer_id': 'foo', 'repo_id': 'some-repo',
                          '_href': '/v2/consumers/foo/bindings/some-repo/dist1/'}]

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_get_consumer_bindings_invalid_consumer(self, mock_factory):
        """
        Test all bindings retrieval invalid consumer
        """
        mock_factory.consumer_manager.return_value.get_consumer.side_effect = MissingResource()

        request = mock.MagicMock()
        consumer_bindings = ConsumerBindingsView()

        try:
            response = consumer_bindings.get(request, 'nonexistent_id')
        except MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised with nonexistent consumer_id")
        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'consumer_id': 'nonexistent_id'})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.consumer_controller.bind')
    def test_create_binding_async(self, mock_bind):
        """
        Test bind consumer to a repo async task.
        """
        request = mock.MagicMock()
        request.body = json.dumps({'repo_id': 'xxx', 'distributor_id': 'yyy'})
        consumer_bindings = ConsumerBindingsView()
        self.assertRaises(OperationPostponed, consumer_bindings.post, request, 'test-consumer')
        mock_bind.assert_called_once_with('test-consumer', 'xxx', 'yyy', True, {}, {})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.consumer_controller.bind')
    def test_create_binding_sync(self, mock_bind, mock_resp):
        """
        Test bind consumer to a repo sync task(notify_agent is false)
        """
        mock_bind.return_value.spawned_tasks = False
        mock_bind.return_value.serialize.return_value = {'mock': 'bind'}

        request = mock.MagicMock()
        request.body = json.dumps({'repo_id': 'xxx', 'distributor_id': 'yyy',
                                   'notify_agent': 'false'})
        consumer_bindings = ConsumerBindingsView()

        response = consumer_bindings.post(request, 'foo')

        expected_cont = {'mock': 'bind'}
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

        mock_bind.assert_called_once_with('foo', 'xxx', 'yyy', 'false', {}, {})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    def test_create_binding_with_invalid_binding_config(self):
        """
        Test bind consumer to a repo witn invalid binding_config
        """
        request = mock.MagicMock()
        request.body = json.dumps({'binding_config': []})
        consumer_bindings = ConsumerBindingsView()
        try:
            response = consumer_bindings.post(request, 'test-consumer')
        except InvalidValue, response:
            pass
        else:
            raise AssertionError("InvalidValue should be raised with wrong type binding config")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['binding_config'])


class TestConsumerBindingResourceView(unittest.TestCase):
    """
    Represents consumers binding resource.
    """
    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.serial_binding')
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_bind_manager')
    def test_get_consumer_binding_resource(self, mock_factory, mock_resp, mock_serial):
        """
        Test retrieve single binding
        """
        bind_resp = {'repo_id': 'some-repo', 'consumer_id': 'foo'}
        mock_factory.return_value.get_bind.return_value = bind_resp
        serial_resp = {'consumer_id': 'foo', 'repo_id': 'some-repo',
                       '_href': '/v2/consumers/foo/bindings/some-repo/dist1/'}
        mock_serial.serialize.return_value = serial_resp

        request = mock.MagicMock()
        consumer_binding = ConsumerBindingResourceView()
        response = consumer_binding.get(request, 'foo', 'some-repo', 'dist1')

        expected_cont = {'consumer_id': 'foo', 'repo_id': 'some-repo',
                         '_href': '/v2/consumers/foo/bindings/some-repo/dist1/'}

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.consumers.consumer_controller.unbind')
    def test_delete_binding_async_no_force(self, mock_unbind):
        """
        Test consumer binding removal async no force
        """
        mock_unbind.return_value.spawned_tasks = True
        request = mock.MagicMock()
        request.body = json.dumps({})
        unbind_view = ConsumerBindingResourceView()
        self.assertRaises(OperationPostponed, unbind_view.delete, request,
                          "consumer_id", "repo_id", "distributor_id")
        mock_unbind.assert_called_once_with("consumer_id", "repo_id", "distributor_id", {})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.consumers.consumer_controller.force_unbind')
    def test_delete_binding_async_yes_force(self, mock_unbind):
        """
        Test consumer binding removal async with force.
        """
        request = mock.MagicMock()
        request.body = json.dumps({'force': True})
        unbind_view = ConsumerBindingResourceView()
        self.assertRaises(OperationPostponed, unbind_view.delete, request,
                          "consumer_id", "repo_id", "distributor_id")
        mock_unbind.assert_called_once_with("consumer_id", "repo_id", "distributor_id", {})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.consumer_controller.unbind')
    def test_delete_binding_sync_no_force(self, mock_unbind, mock_resp):
        """
        Test consumer binding removal sync no force
        """
        mock_unbind.return_value.spawned_tasks = False
        mock_unbind.return_value.serialize.return_value = {'mock': 'unbind'}

        request = mock.MagicMock()
        request.body = json.dumps({})
        unbind_view = ConsumerBindingResourceView()

        response = unbind_view.delete(request, 'foo', 'some-repo', 'dist1')

        expected_cont = {'mock': 'unbind'}
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

        mock_unbind.assert_called_once_with('foo', 'some-repo', 'dist1', {})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.consumer_controller.force_unbind')
    def test_delete_binding_sync_yes_force(self, mock_unbind, mock_resp):
        """
        Test consumer binding removal sync with force
        """
        mock_unbind.return_value.spawned_tasks = False
        mock_unbind.return_value.serialize.return_value = {'mock': 'force-unbind'}

        request = mock.MagicMock()
        request.body = json.dumps({'force': True})
        unbind_view = ConsumerBindingResourceView()

        response = unbind_view.delete(request, 'foo', 'some-repo', 'dist1')

        expected_cont = {'mock': 'force-unbind'}
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)
        mock_unbind.assert_called_once_with('foo', 'some-repo', 'dist1', {})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    def test_delete_binding_invalid_force_type(self):
        """
        Test consumer binding removal with invalid type force
        """
        request = mock.MagicMock()
        request.body = json.dumps({'force': []})
        unbind_view = ConsumerBindingResourceView()
        try:
            response = unbind_view.delete(request, 'foo', 'some-repo', 'dist1')
        except InvalidValue, response:
            pass
        else:
            raise AssertionError("InvalidValue should be raised with wrong type force param")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['force'])

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    def test_delete_binding_invalid_options_type(self):
        """
        Test consumer binding removal with invalid type options
        """
        request = mock.MagicMock()
        request.body = json.dumps({'options': []})
        unbind_view = ConsumerBindingResourceView()
        try:
            response = unbind_view.delete(request, 'foo', 'some-repo', 'dist1')
        except InvalidValue, response:
            pass
        else:
            raise AssertionError("InvalidValue should be raised with wrong type options param")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['options'])


class TestConsumerContentActionView(unittest.TestCase):
    """
    Test Consumer content manipulation.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    def test_consumer_bad_request_content(self):
        """
        Test consumer invalid content action.
        """
        request = mock.MagicMock()
        request.body = json.dumps({})
        consumer_content = ConsumerContentActionView()
        response = consumer_content.post(request, 'my-consumer', 'no_such_action')
        self.assertTrue(isinstance(response, HttpResponseBadRequest))
        self.assertEqual(response.status_code, 400)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    def test_consumer_content_install_missing_cons(self, mock_consumer):
        """
        Test consumer content installation with missing consumer
        """
        mock_consumer.return_value.get_consumer.side_effect = MissingResource()
        request = mock.MagicMock()
        request.body = json.dumps({"units": [], "options": {}})
        consumer_content = ConsumerContentActionView()
        try:
            response = consumer_content.post(request, 'my-consumer', 'install')
        except MissingResource, response:
            pass
        else:
            raise AssertionError('MissingResource should be raised with missing consumer')
        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'consumer_id': 'my-consumer'})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    def test_consumer_content_install_missing_units(self, mock_consumer):
        """
        Test consumer content installation with missing units param
        """
        mock_consumer.return_value.get_consumer.return_value = 'my-consumer'
        request = mock.MagicMock()
        request.body = json.dumps({'options': {}})
        consumer_content = ConsumerContentActionView()
        try:
            response = consumer_content.post(request, 'my-consumer', 'install')
        except MissingValue, response:
            pass
        else:
            raise AssertionError('MissingValue should be raised with missing units param')
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['units'])

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    def test_consumer_content_install_missing_options(self, mock_consumer):
        """
        Test consumer content installation with missing options param
        """
        mock_consumer.return_value.get_consumer.return_value = 'my-consumer'
        request = mock.MagicMock()
        request.body = json.dumps({'units': []})
        consumer_content = ConsumerContentActionView()
        try:
            response = consumer_content.post(request, 'my-consumer', 'install')
        except MissingValue, response:
            pass
        else:
            raise AssertionError('MissingValue should be raised with missing options param')
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['options'])

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_agent_manager')
    def test_consumer_content_install(self, mock_factory, mock_consumer):
        """
        Test consumer content installation.
        """
        mock_factory.return_value.install_content.return_value.task_id = '1234'
        mock_consumer.return_value.get_consumer.return_value = 'my_consumer'
        request = mock.MagicMock()
        request.body = json.dumps({"units": [], "options": {}})
        consumer_content = ConsumerContentActionView()
        self.assertRaises(OperationPostponed, consumer_content.post, request,
                          'my-consumer', 'install')
        mock_factory.return_value.install_content.assert_called_once_with(
            'my-consumer', [], {})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_agent_manager')
    def test_consumer_content_update(self, mock_factory, mock_consumer):
        """
        Test consumer content update.
        """
        mock_consumer.return_value.get_consumer.return_value = 'test-consumer'
        mock_factory.return_value.update_content.return_value.task_id = '1234'
        request = mock.MagicMock()
        request.body = json.dumps({"units": [], "options": {}})
        consumer_content = ConsumerContentActionView()
        self.assertRaises(OperationPostponed, consumer_content.post, request,
                          'my-consumer', 'update')
        mock_factory.return_value.update_content.assert_called_once_with(
            'my-consumer', [], {})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_agent_manager')
    def test_consumer_content_uninstall(self, mock_factory, mock_consumer):
        """
        Test consumer content uninstall.
        """
        mock_consumer.return_value.get_consumer.return_value = 'test-consumer'
        mock_factory.return_value.uninstall_content.return_value.task_id = '1234'
        request = mock.MagicMock()
        request.body = json.dumps({"units": [], "options": {}})
        consumer_content = ConsumerContentActionView()
        self.assertRaises(OperationPostponed, consumer_content.post, request,
                          'my-consumer', 'uninstall')
        mock_factory.return_value.uninstall_content.assert_called_once_with(
            'my-consumer', [], {})


class TestConsumerHistoryView(unittest.TestCase):
    """
    Test Consumer history view
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_history_manager')
    def test_consumer_history(self, mock_history, mock_consumer, mock_resp):
        """
        Test consumer history
        """
        mock_consumer.return_value.get_consumer.return_value = 'test-consumer'
        mock_history.return_value.query.return_value = {'mock': 'some-history'}
        request = mock.MagicMock()
        consumer_history = ConsumerHistoryView()
        request.GET = {}
        response = consumer_history.get(request, 'test-consumer')

        mock_history.return_value.query.assert_called_once_with(sort='descending', event_type=None,
                                                                end_date=None, start_date=None,
                                                                consumer_id='test-consumer',
                                                                limit=None)
        mock_resp.assert_called_once_with({'mock': 'some-history'})
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_history_manager')
    def test_consumer_history_with_filters(self, mock_history, mock_consumer, mock_resp):
        """
        Test consumer history using filters
        """
        mock_consumer.return_value.get_consumer.return_value = 'test-consumer'
        mock_history.return_value.query.return_value = {'mock': 'some-history'}
        request = mock.MagicMock()
        consumer_history = ConsumerHistoryView()
        request.GET = {'limit': '2', 'event_type': 'registered'}
        response = consumer_history.get(request, 'test-consumer')

        mock_history.return_value.query.assert_called_once_with(sort='descending', limit=2,
                                                                event_type='registered',
                                                                end_date=None, start_date=None,
                                                                consumer_id='test-consumer')
        mock_resp.assert_called_once_with({'mock': 'some-history'})
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_history_manager')
    def test_consumer_no_history(self, mock_history, mock_consumer, mock_resp):
        """
        Test consumer no history
        """
        mock_consumer.return_value.get_consumer.return_value = 'test-consumer'
        mock_history.return_value.query.return_value = []
        request = mock.MagicMock()
        consumer_history = ConsumerHistoryView()
        request.GET = {}
        response = consumer_history.get(request, 'test-consumer')

        mock_history.return_value.query.assert_called_once_with(sort='descending', limit=None,
                                                                event_type=None,
                                                                end_date=None, start_date=None,
                                                                consumer_id='test-consumer')
        mock_resp.assert_called_once_with([])
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    def test_consumer_history_with_nonint_limit(self, mock_consumer):
        """
        Pass an invalid (non-integer) limit parameter.
        """
        mock_consumer.return_value.get_consumer.return_value = 'test-consumer'
        mock_request = mock.MagicMock()
        mock_request.GET = {'limit': 'not an int'}

        consumer_history = ConsumerHistoryView()
        try:
            consumer_history.get(mock_request, 'test-consumer')
        except InvalidValue, response:
            pass
        else:
            raise AssertionError('InvalidValue should be raised if limit is not an integer')

        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['limit'])


class TestConsumerProfilesView(unittest.TestCase):
    """
    Represents consumers profiles
    """
    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_profile_manager')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_manager')
    def test_get_consumer_profiles(self, mock_consumer, mock_profile, mock_resp):
        """
        Test retrieve consumer profiles
        """
        mock_consumer.return_value.get_consumer.return_value = 'test-consumer'
        resp = [{'some_profile': [], 'consumer_id': 'test-consumer', 'content_type': 'rpm'}]
        mock_profile.return_value.get_profiles.return_value = resp

        request = mock.MagicMock()
        consumer_profiles = ConsumerProfilesView()
        response = consumer_profiles.get(request, 'test-consumer')

        expected_cont = [{'consumer_id': 'test-consumer', 'some_profile': [],
                          '_href': '/v2/consumers/test-consumer/profiles/rpm/',
                          'content_type': 'rpm'}]

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.generate_redirect_response')
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_profile_manager')
    def test_create_consumer_profile(self, mock_profile, mock_resp, mock_redirect):
        """
        Test create consumer profile
        """
        resp = {'some_profile': [], 'consumer_id': 'test-consumer', 'content_type': 'rpm'}
        mock_profile.return_value.create.return_value = resp

        request = mock.MagicMock()
        request.body = json.dumps({'content_type': 'rpm', 'profile': []})
        consumer_profiles = ConsumerProfilesView()
        response = consumer_profiles.post(request, 'test-consumer')

        expected_cont = {'consumer_id': 'test-consumer', 'some_profile': [],
                         '_href': '/v2/consumers/test-consumer/profiles/rpm/',
                         'content_type': 'rpm'}

        mock_resp.assert_called_once_with(expected_cont)
        mock_redirect.assert_called_once_with(mock_resp.return_value, expected_cont['_href'])
        self.assertTrue(response is mock_redirect.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_profile_manager')
    def test_create_consumer_profile_missing_param(self, mock_profile):
        """
        Test create consumer profile with missing param
        """
        resp = {'some_profile': [], 'consumer_id': 'test-consumer', 'content_type': 'rpm'}
        mock_profile.return_value.create.return_value = resp

        request = mock.MagicMock()
        request.body = json.dumps({'profile': []})
        consumer_profiles = ConsumerProfilesView()
        try:
            response = consumer_profiles.post(request, 'test-consumer')
        except MissingValue, response:
            pass
        else:
            raise AssertionError("MissingValue should be raised with missing param")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['content_type'])


class TestConsumerProfileSearchView(unittest.TestCase):
    """
    Test the ConsumerProfileSearchView.
    """
    def test_class_attributes(self):
        """
        Ensure that the ConsumerProfileSearchView has the correct class attributes.
        """
        self.assertEqual(ConsumerProfileSearchView.response_builder,
                         util.generate_json_response_with_pulp_encoder)
        self.assertTrue(isinstance(ConsumerProfileSearchView.manager, profile.ProfileManager))


class TestConsumerProfileResourceView(unittest.TestCase):
    """
    Represents consumers profile resource
    """
    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_profile_manager')
    def test_get_consumer_profile(self, mock_profile, mock_resp):
        """
        Test retrieve consumer profile
        """
        resp = {'some_profile': [], 'consumer_id': 'test-consumer', 'content_type': 'rpm'}
        mock_profile.return_value.get_profile.return_value = resp

        request = mock.MagicMock()
        consumer_profile = ConsumerProfileResourceView()
        response = consumer_profile.get(request, 'test-consumer', 'rpm')

        expected_cont = {'consumer_id': 'test-consumer', 'some_profile': [],
                         '_href': '/v2/consumers/test-consumer/profiles/rpm/',
                         'content_type': 'rpm'}

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_profile_manager')
    def test_update_consumer_profile(self, mock_profile, mock_resp):
        """
        Test update consumer profile
        """
        resp = {'some_profile': ['new_info'], 'consumer_id': 'test-consumer', 'content_type': 'rpm'}
        mock_profile.return_value.update.return_value = resp

        request = mock.MagicMock()
        request.body = json.dumps({'some_profile': ['new_info']})
        consumer_profile = ConsumerProfileResourceView()
        response = consumer_profile.put(request, 'test-consumer', 'rpm')

        expected_cont = {'consumer_id': 'test-consumer', 'some_profile': ['new_info'],
                         '_href': '/v2/consumers/test-consumer/profiles/rpm/',
                         'content_type': 'rpm'}

        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_profile_manager')
    def test_delete_consumer_profile(self, mock_profile, mock_resp):
        """
        Test delete consumer profile
        """
        mock_profile.return_value.delete.return_value = None

        request = mock.MagicMock()
        consumer_profile = ConsumerProfileResourceView()
        response = consumer_profile.delete(request, 'test-consumer', 'rpm')

        mock_profile.return_value.delete.assert_called_once_with('test-consumer', 'rpm')
        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)


class TestConsumerQueryContentApplicabilityView(unittest.TestCase):
    """
    Represents consumers content applicability
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.ConsumerContentApplicabilityView')
    def test_query_consumer_content_applic_bad_request(self, mock_criteria_types):
        """
        Test query consumer content applic. bad request
        """
        mock_criteria_types._get_consumer_criteria.side_effect = InvalidValue

        request = mock.MagicMock()
        request.body = json.dumps({'content_types': ['type1']})
        consumer_applic = ConsumerContentApplicabilityView()
        response = consumer_applic.post(request)
        self.assertTrue(isinstance(response, HttpResponseBadRequest))
        self.assertEqual(response.status_code, 400)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.retrieve_consumer_applicability')
    @mock.patch('pulp.server.webservices.views.consumers.ConsumerContentApplicabilityView')
    def test_query_consumer_content_applic(self, mock_criteria_types, mock_applic, mock_resp):
        """
        Test query consumer content applicability
        """
        resp = [{'consumers': ['c1', 'c2'],
                 'applicability': {'content_type_1': ['unit_1', 'unit_3']}}]
        mock_criteria_types._get_consumer_criteria.return_value = {'mock': 'some-criteria'}
        mock_criteria_types._get_content_types.return_value = {'mock': 'some-content-types'}
        mock_applic.return_value = resp

        request = mock.MagicMock()
        request.body = json.dumps({'criteria': {'filters': {}}, 'content_types': ['type1']})
        consumer_applic = ConsumerContentApplicabilityView()
        response = consumer_applic.post(request)

        mock_resp.assert_called_once_with(resp)
        self.assertTrue(response is mock_resp.return_value)

    def test_get_consumer_criteria_no_criteria(self):
        """
        Test get consumer criteria.
        """
        request = mock.MagicMock()
        request.body_as_json = {}
        consumer_applic = ConsumerContentApplicabilityView()
        try:
            response = ConsumerContentApplicabilityView._get_consumer_criteria(
                consumer_applic, request)
        except InvalidValue, response:
            pass
        else:
            raise AssertionError("InvalidValue should be raised with missing param")
        self.assertEqual(response.http_status_code, 400)
        m = "The input to this method must be a JSON object with a 'criteria' key."
        self.assertEqual(response.error_data['property_names'], [m])

    def test_get_consumer_criteria_no_content_types(self):
        """
        Test get content types
        """
        request = mock.MagicMock()
        request.body_as_json = {'content_types': 'not_list'}
        consumer_applic = ConsumerContentApplicabilityView()
        try:
            response = ConsumerContentApplicabilityView._get_content_types(
                consumer_applic, request)
        except InvalidValue, response:
            pass
        else:
            raise AssertionError("InvalidValue should be raised with missing param")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'],
                         ['content_types must index an array.'])


class TestConsumerContentApplicabilityView(unittest.TestCase):
    """
    Represents consumers content applicability regeneration
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    def test_post_consumer_content_applic_regen_no_criteria(self):
        """
        Test create consumer content applic. regen with no criteria
        """
        request = mock.MagicMock()
        request.body = json.dumps({})
        consumer_applic_regen = ConsumerContentApplicRegenerationView()
        try:
            response = consumer_applic_regen.post(request)
        except MissingValue, response:
            pass
        else:
            raise AssertionError("MissingValue should be raised with missing param")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['consumer_criteria'])

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    def test_post_consumer_content_applic_regen_invalid_criteria(self):
        """
        Test create consumer content applic. regen with invalid criteria
        """
        request = mock.MagicMock()
        request.body = json.dumps({'consumer_criteria': []})
        consumer_applic_regen = ConsumerContentApplicRegenerationView()
        try:
            response = consumer_applic_regen.post(request)
        except InvalidValue, response:
            pass
        else:
            raise AssertionError("InvalidValue should be raised with missing param")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['consumer_criteria'])

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.tags')
    @mock.patch('pulp.server.webservices.views.consumers.Criteria.from_client_input')
    @mock.patch('pulp.server.webservices.views.consumers.regenerate_applicability_for_consumers')
    def test_post_consumer_content_applic_regen(self, mock_applic, mock_criteria, mock_tags):
        """
        Test create consumer content applic. regen
        """
        mock_task_tags = [mock_tags.action_tag.return_value]
        mock_criteria.return_value.as_dict.return_value = {'mock': 'some-criteria'}
        request = mock.MagicMock()
        request.body = json.dumps({'consumer_criteria': {}})
        consumer_applic_regen = ConsumerContentApplicRegenerationView()
        try:
            consumer_applic_regen.post(request)
        except OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raised for asynchronous delete.')
        self.assertEqual(response.http_status_code, 202)

        mock_applic.apply_async_with_reservation.assert_called_with(
            mock_tags.RESOURCE_REPOSITORY_PROFILE_APPLICABILITY_TYPE, mock_tags.RESOURCE_ANY_ID,
            ({'mock': 'some-criteria'},), tags=mock_task_tags)


class TestConsumerResourceContentApplicabilityView(unittest.TestCase):
    """
    Represents consumer content applicability regeneration
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_query_manager')
    def test_post_consumer_resource_content_applic_regen_no_consumer(self, mock_consumer):
        """
        Test create consumer content applic. regen with invalid consumer
        """
        mock_consumer.return_value.find_by_id.return_value = None
        request = mock.MagicMock()
        request.body = json.dumps({})
        consumer_applic_regen = ConsumerResourceContentApplicRegenerationView()
        try:
            response = consumer_applic_regen.post(request, 'c1')
        except MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised with missing param")
        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'consumer_id': 'c1'})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.tags')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_query_manager')
    @mock.patch('pulp.server.webservices.views.consumers.Criteria')
    @mock.patch('pulp.server.webservices.views.consumers.regenerate_applicability_for_consumers')
    def test_post_consumer_resource_content_applic_regen(self, mock_applic, mock_criteria,
                                                         mock_consumer, mock_tags):
        """
        Test create consumer resource content applic. regen
        """
        mock_consumer.return_value.find_by_id.return_value = 'c1'
        mock_task_tags = [mock_tags.action_tag.return_value]
        mock_criteria.return_value.as_dict.return_value = {'mock': 'some-criteria'}
        request = mock.MagicMock()
        request.body = json.dumps({})
        consumer_applic_regen = ConsumerResourceContentApplicRegenerationView()
        try:
            consumer_applic_regen.post(request, 'c1')
        except OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raised for asynchronous delete.')
        self.assertEqual(response.http_status_code, 202)

        mock_applic.apply_async_with_reservation.assert_called_with(
            mock_tags.RESOURCE_CONSUMER_TYPE, 'c1',
            ({'mock': 'some-criteria'},), tags=mock_task_tags)


class TestConsumerUnitActionSchedulesView(unittest.TestCase):
    """
    Test consumer schedule actions
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_get_schedules(self, mock_factory, mock_resp):
        """
        Test consumer's schedules retrieval
        """
        mock_consumer_manager = mock.MagicMock()
        mock_factory.consumer_manager.return_value = mock_consumer_manager
        mock_consumer_manager.get_consumer.return_value = 'c1'
        mock_display = mock.MagicMock()
        resp = {'_id': 'my-schedule', 'schedule': 'P1D', 'kwargs': {'options': {}, 'units': []}}
        mock_display.for_display.return_value = resp
        mock_factory.consumer_schedule_manager.return_value.get.return_value = [mock_display]

        request = mock.MagicMock()
        consumer_schedule = UnitInstallSchedulesView()
        response = consumer_schedule.get(request, 'c1')

        mock_factory.consumer_schedule_manager.return_value.get.assert_called_once_with(
            'c1', 'scheduled_unit_install')

        expected_content = [{'_id': 'my-schedule', 'kwargs': {'options': {}, 'units': []},
                             '_href': '/v2/consumers/c1/schedules/content/install/my-schedule/',
                             'options': {}, 'units': [], 'schedule': 'P1D'}]
        mock_resp.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_get_schedules_missing_consumer(self, mock_factory):
        """
        Test consumer's schedules retrieval missing consumer
        """
        mock_consumer_manager = mock.MagicMock()
        mock_factory.consumer_manager.return_value = mock_consumer_manager
        mock_consumer_manager.get_consumer.side_effect = MissingResource()
        request = mock.MagicMock()
        consumer_schedule = UnitInstallSchedulesView()
        try:
            response = consumer_schedule.get(request, 'test-consumer')
        except MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised with missing consumer")
        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'consumer_id': 'test-consumer'})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.generate_redirect_response')
    @mock.patch('pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_create_schedules(self, mock_factory, mock_resp, mock_redirect):
        """
        Test consumer's schedules creation
        """
        mock_consumer_manager = mock.MagicMock()
        mock_factory.consumer_manager.return_value = mock_consumer_manager
        mock_consumer_manager.get_consumer.return_value = 'c1'
        mock_consumer_schedule_manager = mock.MagicMock()
        mock_factory.consumer_schedule_manager.return_value = mock_consumer_schedule_manager
        resp = {'_id': 'some-schedule', 'kwargs': {'options': {}, 'units': []}}
        mock_consumer_schedule_manager.create_schedule.return_value.for_display.return_value = resp

        request = mock.MagicMock()
        request.body = json.dumps({'schedule': 'some-schedule'})
        consumer_schedule = UnitInstallSchedulesView()
        response = consumer_schedule.post(request, 'c1')

        mock_consumer_schedule_manager.create_schedule.assert_called_once_with(
            'scheduled_unit_install', 'c1', None, {}, 'some-schedule', None, True)

        expected_cont = {'_id': 'some-schedule', 'kwargs': {'options': {}, 'units': []},
                         'options': {}, 'units': [],
                         '_href': '/v2/consumers/c1/schedules/content/install/some-schedule/'}
        mock_resp.assert_called_once_with(expected_cont)
        mock_redirect.assert_called_once_with(mock_resp.return_value, expected_cont['_href'])
        self.assertTrue(response is mock_redirect.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_schedule_manager')
    def test_create_schedules_unsupported_params(self, mock_consumer):
        """
        Test consumer's schedules creation with unsupported param
        """
        request = mock.MagicMock()
        request.body = json.dumps({'schedule': 'some-schedule', 'unsupported_param': '1234'})
        consumer_schedule = UnitInstallSchedulesView()
        try:
            response = consumer_schedule.post(request, 'test-consumer')
        except UnsupportedValue, response:
            pass
        else:
            raise AssertionError("UnsupportedValue should be raised with unsupported keys")
        self.assertEqual(response.http_status_code, 400)
        self.assertEqual(response.error_data['property_names'], ['unsupported_param'])


class TestConsumerUnitActionScheduleResourceView(unittest.TestCase):
    """
    Test consumer schedule actions
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_get_schedule(self, mock_factory, mock_resp):
        """
        Test consumer's schedules resource retrieval
        """
        mock_id = mock.MagicMock()
        resp = {'_id': 'some-schedule', 'schedule': 'P1D', 'kwargs': {'options': {}, 'units': []}}
        mock_id.for_display.return_value = resp
        mock_id.id = 'some-schedule'
        mock_factory.consumer_schedule_manager.return_value.get.return_value = [mock_id]

        request = mock.MagicMock()
        consumer_schedule = UnitInstallScheduleResourceView()
        response = consumer_schedule.get(request, 'c1', 'some-schedule')

        mock_factory.consumer_schedule_manager.return_value.get.assert_called_once_with(
            'c1', 'scheduled_unit_install')

        expected_cont = {'_id': 'some-schedule', 'kwargs': {'options': {}, 'units': []},
                         '_href': '/v2/consumers/c1/schedules/content/install/some-schedule/',
                         'options': {}, 'units': [], 'schedule': 'P1D'}
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory')
    def test_get_invalid_schedule(self, mock_factory, mock_resp):
        """
        Test consumer's invalid schedule resource retrieval
        """
        mock_factory.consumer_schedule_manager.return_value.get.return_value = []

        request = mock.MagicMock()
        consumer_schedule = UnitInstallScheduleResourceView()
        try:
            response = consumer_schedule.get(request, 'test-consumer', 'some-schedule')
        except MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised with missing param")
        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'consumer_id': 'test-consumer',
                                                            'schedule_id': 'some-schedule'})
        mock_factory.consumer_schedule_manager.return_value.get.assert_called_once_with(
            'test-consumer', 'scheduled_unit_install')

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.consumers.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_schedule_manager')
    def test_update_schedule(self, mock_factory, mock_resp):
        """
        Test consumer's schedules resource update
        """
        resp = {'_id': 'some-schedule', 'schedule': 'P1D', 'kwargs': {'options': {}, 'units': []}}
        mock_update_schedule = mock.MagicMock()
        mock_factory.return_value.update_schedule = mock_update_schedule
        mock_update_schedule.return_value.for_display.return_value = resp

        request = mock.MagicMock()
        request.body = json.dumps({'failure_threshold': '3', 'schedule': 'P1D'})
        consumer_schedule = UnitInstallScheduleResourceView()
        response = consumer_schedule.put(request, 'c1', 'some-schedule')

        mock_update_schedule.assert_called_once_with('c1', 'some-schedule', None, None,
                                                     {'failure_threshold': '3',
                                                      'iso_schedule': 'P1D'})

        expected_cont = {'_id': 'some-schedule', 'kwargs': {'options': {}, 'units': []},
                         '_href': '/v2/consumers/c1/schedules/content/install/some-schedule/',
                         'options': {}, 'units': [], 'schedule': 'P1D'}
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.consumers.generate_json_response')
    @mock.patch('pulp.server.webservices.views.consumers.factory.consumer_schedule_manager')
    def test_delete_schedule(self, mock_schedule, mock_resp):
        """
        Test consumer's schedules resource delete
        """
        request = mock.MagicMock()
        consumer_schedule = UnitInstallScheduleResourceView()
        response = consumer_schedule.delete(request, 'test-consumer', 'some-schedule')

        mock_schedule.return_value.delete_schedule.assert_called_once_with(
            'test-consumer', 'some-schedule')

        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)


class TestConsumerAddLinks(unittest.TestCase):

    def test_add_link(self):
        """
        Test that the reverse for consumer works correctly.
        """
        consumer = {'id': 'my_consumer'}
        link = consumers.add_link(consumer)
        href = {'_href': '/v2/consumers/my_consumer/'}
        expected_cont = {'id': 'my_consumer', '_href': '/v2/consumers/my_consumer/'}
        self.assertEqual(link, href)
        self.assertEqual(consumer, expected_cont)

    def test_add_link_profile(self):
        """
        Test that the reverse for consumer profile works correctly.
        """
        consumer_profile = {'consumer_id': 'my_consumer', 'content_type': 'rpm'}
        link = consumers.add_link_profile(consumer_profile)
        href = {'_href': '/v2/consumers/my_consumer/profiles/rpm/'}
        expected_cont = {'consumer_id': 'my_consumer', 'content_type': 'rpm',
                         '_href': '/v2/consumers/my_consumer/profiles/rpm/'}
        self.assertEqual(link, href)
        self.assertEqual(consumer_profile, expected_cont)

    def test_add_link_schedule(self):
        """
        Test that the reverse for consumer schedule works correctly.
        """
        consumer_id = 'c1'
        action_type = 'scheduled_unit_install'
        schedule = {'_id': 'schedule-id'}
        link = consumers.add_link_schedule(schedule, action_type, consumer_id)
        href = {'_href': '/v2/consumers/c1/schedules/content/install/schedule-id/'}
        expected_cont = {'_id': 'schedule-id',
                         '_href': '/v2/consumers/c1/schedules/content/install/schedule-id/'}
        self.assertEqual(link, href)
        self.assertEqual(schedule, expected_cont)

    def test_scheduled_unit_management_obj_structure(self):
        """
        Modify scheduled unit management object.
        """
        scheduled_call = {'kwargs': {'options': {}, 'units': []}}
        expected_structure = {'kwargs': {'options': {}, 'units': []}, 'options': {}, 'units': []}
        response = consumers.scheduled_unit_management_obj(scheduled_call)
        self.assertEqual(response, expected_structure)
