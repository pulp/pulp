"""
This module contains tests for the pulp.server.webservices.views.search module.
"""
import unittest

import mock
from django import http

from base import assert_auth_READ
from pulp.server import exceptions
from pulp.server.webservices.views import search


class TestSearchView(unittest.TestCase):
    """
    Test the SearchView class.
    """
    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.search.criteria.Criteria.from_client_input')
    def test_get_with_fields(self, from_client_input):
        """
        Test the GET search handler with fields in the request.
        """
        class FakeSearchView(search.SearchView):
            model = mock.MagicMock()

        request = mock.MagicMock()
        # Simulate an empty POST body
        request.GET = {'field': ['name', 'id'], 'filters': ['{"name":"admin"}']}
        view = FakeSearchView()
        FakeSearchView.model.objects.find_by_criteria.return_value = ['big money', 'bigger money']

        with mock.patch.object(FakeSearchView, '_generate_response',
                               side_effect=FakeSearchView._generate_response) as _generate_response:
            results = view.get(request)

        self.assertEqual(type(results), http.HttpResponse)
        self.assertEqual(results.content, '["big money", "bigger money"]')
        self.assertEqual(results.status_code, 200)
        # This is actually a bug, but the intention of this Django port was to behave exactly like
        # The webpy handlers did, bugs included. When #312 is fixed, the tests below should fail,
        # because the get() handler should have deserialized the filters instead of leaving them as
        # strings. Please modify these assertions to have the correct behavior.
        # https://pulp.plan.io/issues/312
        _generate_response.assert_called_once_with(
            {'fields': ['name', 'id'], 'filters': ['{"name":"admin"}']})
        from_client_input.assert_called_once_with(
            {'fields': ['name', 'id'], 'filters': ['{"name":"admin"}']})

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.search.criteria.Criteria.from_client_input')
    def test_get_without_fields(self, from_client_input):
        """
        Test the GET search handler without any fields specified in the request.
        """
        class FakeSearchView(search.SearchView):
            model = mock.MagicMock()

        request = mock.MagicMock()
        # Simulate an empty POST body
        request.GET = {'filters': ['{"name":"admin"}']}
        view = FakeSearchView()
        FakeSearchView.model.objects.find_by_criteria.return_value = ['big money', 'bigger money']

        with mock.patch.object(FakeSearchView, '_generate_response',
                               side_effect=FakeSearchView._generate_response) as _generate_response:
            results = view.get(request)

        self.assertEqual(type(results), http.HttpResponse)
        self.assertEqual(results.content, '["big money", "bigger money"]')
        self.assertEqual(results.status_code, 200)
        # This is actually a bug, but the intention of this Django port was to behave exactly like
        # The webpy handlers did, bugs included. When #312 is fixed, the tests below should fail,
        # because the get() handler should have deserialized the filters instead of leaving them as
        # strings. Please modify these assertions to have the correct behavior.
        # https://pulp.plan.io/issues/312
        _generate_response.assert_called_once_with({'filters': ['{"name":"admin"}']})
        from_client_input.assert_called_once_with({'filters': ['{"name":"admin"}']})

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    def test_post(self):
        """
        Test the POST search under normal conditions.
        """
        class FakeSearchView(search.SearchView):
            model = mock.MagicMock()

        request = mock.MagicMock()
        # Simulate an empty POST body
        request.body = '{"criteria": {"filters": {"money": {"$gt": 1000000}}}}'
        view = FakeSearchView()
        FakeSearchView.model.objects.find_by_criteria.return_value = ['big money', 'bigger money']

        with mock.patch.object(FakeSearchView, '_generate_response',
                               side_effect=FakeSearchView._generate_response) as _generate_response:
            results = view.post(request)

        self.assertEqual(type(results), http.HttpResponse)
        self.assertEqual(results.content, '["big money", "bigger money"]')
        self.assertEqual(results.status_code, 200)
        _generate_response.assert_called_once_with({'filters': {'money': {'$gt': 1000000}}})

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    def test_post_missing_criteria(self):
        """
        Test that POST search when the user has not passed the required criteria.
        """
        request = mock.MagicMock()
        # Simulate an empty POST body
        request.body = "{}"
        view = search.SearchView()

        try:
            view.post(request)
            self.fail('A MissingValue Exception should have been raised.')
        except exceptions.MissingValue, e:
            self.assertEqual(e.property_names, ['criteria'])

    def test__generate_response_no_fields(self):
        """
        Test that _generate_response() works correctly when the query does not contain fields.
        """
        class FakeSearchView(search.SearchView):
            model = mock.MagicMock()

        query = {'filters': {'money': {'$gt': 1000000}}}
        FakeSearchView.model.objects.find_by_criteria.return_value = ['big money', 'bigger money']

        results = FakeSearchView._generate_response(query)

        self.assertEqual(type(results), http.HttpResponse)
        self.assertEqual(results.content, '["big money", "bigger money"]')
        self.assertEqual(results.status_code, 200)
        self.assertEqual(
            FakeSearchView.model.objects.find_by_criteria.mock_calls[0][1][0]['fields'], None)
        self.assertEqual(
            FakeSearchView.model.objects.find_by_criteria.mock_calls[0][1][0]['filters'],
            {'money': {'$gt': 1000000}})

    def test__generate_response_with_custom_response_builder(self):
        """
        Test the _generate_response() method for the case where the SearchView is configured to
        use a custom response_builder function.
        """
        class FakeSearchView(search.SearchView):
            response_builder = mock.MagicMock(return_value=42)
            model = mock.MagicMock()

        query = {'filters': {'money': {'$gt': 1000000}}}
        FakeSearchView.model.objects.find_by_criteria.return_value = ['big money', 'bigger money']

        results = FakeSearchView._generate_response(query)

        self.assertEqual(results, 42)
        self.assertEqual(
            FakeSearchView.model.objects.find_by_criteria.mock_calls[0][1][0]['fields'], None)
        self.assertEqual(
            FakeSearchView.model.objects.find_by_criteria.mock_calls[0][1][0]['filters'],
            {'money': {'$gt': 1000000}})
        FakeSearchView.response_builder.assert_called_once_with(['big money', 'bigger money'])

    def test__generate_response_with_dumb_model(self):
        """
        Test the _generate_response() method for the case where the SearchView is configured to
        search an old-style model.
        """
        class FakeSearchView(search.SearchView):
            manager = mock.MagicMock()

        query = {'filters': {'money': {'$gt': 1000000}}}
        FakeSearchView.manager.find_by_criteria.return_value = ['big money', 'bigger money']

        results = FakeSearchView._generate_response(query)

        self.assertEqual(type(results), http.HttpResponse)
        self.assertEqual(results.content, '["big money", "bigger money"]')
        self.assertEqual(results.status_code, 200)
        self.assertEqual(
            FakeSearchView.manager.find_by_criteria.mock_calls[0][1][0]['fields'], None)
        self.assertEqual(
            FakeSearchView.manager.find_by_criteria.mock_calls[0][1][0]['filters'],
            {'money': {'$gt': 1000000}})

    def test__generate_response_with_fields_with_id(self):
        """
        Test that _generate_response() works correctly when the query contains fields that include
        the id.
        """
        class FakeSearchView(search.SearchView):
            model = mock.MagicMock()

        query = {'filters': {'money': {'$gt': 1000000}}, 'fields': ['cash', 'id']}
        FakeSearchView.model.objects.find_by_criteria.return_value = ['big money', 'bigger money']

        results = FakeSearchView._generate_response(query)

        self.assertEqual(type(results), http.HttpResponse)
        self.assertEqual(results.content, '["big money", "bigger money"]')
        self.assertEqual(results.status_code, 200)
        self.assertEqual(
            FakeSearchView.model.objects.find_by_criteria.mock_calls[0][1][0]['fields'],
            ['cash', 'id'])
        self.assertEqual(
            FakeSearchView.model.objects.find_by_criteria.mock_calls[0][1][0]['filters'],
            {'money': {'$gt': 1000000}})

    def test__generate_response_with_fields_without_id(self):
        """
        Test that _generate_response() works correctly when the query contains fields that do not
        include the id.
        """
        class FakeSearchView(search.SearchView):
            model = mock.MagicMock()

        query = {'filters': {'money': {'$gt': 1000000}}, 'fields': ['cash']}
        FakeSearchView.model.objects.find_by_criteria.return_value = ['big money', 'bigger money']

        results = FakeSearchView._generate_response(query)

        self.assertEqual(type(results), http.HttpResponse)
        self.assertEqual(results.content, '["big money", "bigger money"]')
        self.assertEqual(results.status_code, 200)
        self.assertEqual(
            FakeSearchView.model.objects.find_by_criteria.mock_calls[0][1][0]['fields'],
            ['cash', 'id'])
        self.assertEqual(
            FakeSearchView.model.objects.find_by_criteria.mock_calls[0][1][0]['filters'],
            {'money': {'$gt': 1000000}})

    def test__generate_response_with_serializer(self):
        """
        Test the _generate_response() method for the case where the SearchView is configured to
        use a serializer.
        """
        class FakeSearchView(search.SearchView):
            model = mock.MagicMock()
            serializer = mock.MagicMock(side_effect=['biggest money', 'unreal money'])

        query = {'filters': {'money': {'$gt': 1000000}}}
        FakeSearchView.model.objects.find_by_criteria.return_value = ['big money', 'bigger money']

        results = FakeSearchView._generate_response(query)

        self.assertEqual(type(results), http.HttpResponse)
        self.assertEqual(results.content, '["biggest money", "unreal money"]')
        self.assertEqual(results.status_code, 200)
        self.assertEqual(
            FakeSearchView.model.objects.find_by_criteria.mock_calls[0][1][0]['fields'], None)
        self.assertEqual(
            FakeSearchView.model.objects.find_by_criteria.mock_calls[0][1][0]['filters'],
            {'money': {'$gt': 1000000}})
        self.assertEqual([c[1][0] for c in FakeSearchView.serializer.mock_calls],
                         ['big money', 'bigger money'])
