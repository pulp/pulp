import json
import unittest

import mock
from mock import call
from django.http import HttpResponse, HttpResponseNotFound

from pulp.server.webservices.views.content import (ContentTypesView, ContentTypeResourceView,
                                                   ContentUnitsCollectionView)


class TestContentTypesView(unittest.TestCase):

    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_types_view(self, mock_factory):
        """
        ContentTypesView should return an HttpResponse. The content of the
        response should be JSON containing the appropriate data.
        """
        mock_cqm = mock.MagicMock()
        mock_cqm.list_content_types.return_value = ['rpm']
        mock_factory.content_query_manager.return_value = mock_cqm
        request = mock.MagicMock()

        content_types_view = ContentTypesView()
        response = content_types_view.get(request)

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertFalse(isinstance(response, HttpResponseNotFound))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

        content = json.loads(response.content)
        self.assertTrue(len(content), 1)
        expected_href = '/v2/content/types/rpm/'
        self.assertEqual(expected_href, content[0]['_href'])
        self.assertEqual('rpm', content[0]['content_type'])


class TestContentTypeResourceView(unittest.TestCase):

    @mock.patch('pulp.server.webservices.views.content.serialization')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_type_resource_view(self, mock_factory, mock_serializer):
        """
        ContentTypeResourceView should return an HttpResponse, or an HttpResponseNotFound
        if the specified content type is not found. The content of the response should be JSON
        containing a dictionary for each content type.
        """
        mock_cqm = mock.MagicMock()
        mock_cqm.get_content_type.return_value = None
        mock_factory.content_query_manager.return_value = mock_cqm
        request = mock.MagicMock()

        content_type_resource_view = ContentTypeResourceView()

        # Test invalid content type
        response = content_type_resource_view.get(request, 'hello')
        self.assertTrue(isinstance(response, HttpResponseNotFound))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

        # Test valid content type
        mock_cqm.get_content_type.return_value = 'Not None'
        mock_serializer.content.content_type_obj.return_value = {}

        request.get_full_path.return_value = '/pulp/view/test/'
        response = content_type_resource_view.get(request, 'mock_type')

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertFalse(isinstance(response, HttpResponseNotFound))

        content = json.loads(response.content)
        expected_actions = {'_href': '/pulp/view/test/actions/'}
        expected_content_units = {'_href': '/pulp/view/test/units/'}
        self.assertEqual(expected_actions, content['actions'])
        self.assertEqual(expected_content_units, content['content_units'])


class TestContentUnitsCollectionView(unittest.TestCase):

    # TODO(asmacdo) remove this and the method it tests
    # This is intentionally untested. I have another PR that reimplements this helper. No need to
    # test twice.
    def test_process_unit(self):
        self.assertTrue(False)

    @mock.patch('pulp.server.webservices.views.content.ContentUnitsCollectionView.process_unit')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_units_collection_view(self, mock_factory, mock_process):
        """
        ContentUnitsCollectionView should return an HttpResponse. The majority of the work done
        in this call is accomplished by helper functions, so the the important things to be tested
        are the headers, calls to the helper functions, and how the results of the helper calls
        are processed.
        """
        mock_cqm = mock.MagicMock()
        mock_cqm.find_by_criteria.return_value = ['thing1', 'thing2']
        mock_factory.content_query_manager.return_value = mock_cqm
        request = mock.MagicMock()
        request.get_full_path.return_value = '/path/'
        mock_process.return_value = {}

        content_units_collection_view = ContentUnitsCollectionView()
        response = content_units_collection_view.get(request, 'mock_type')

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertFalse(isinstance(response, HttpResponseNotFound))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

        content = json.loads(response.content)
        self.assertEqual(len(content), 2)
        mock_process.assert_has_calls([call('thing1', request), call('thing2', request)])
