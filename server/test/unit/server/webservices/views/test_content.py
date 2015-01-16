import json
import unittest

import mock
from django.http import HttpResponse, HttpResponseNotFound

from .base import assert_auth_READ
from pulp.server.exceptions import MissingResource
from pulp.server.webservices.views.content import ContentUnitResourceView


class TestContentUnitResourceView(unittest.TestCase):

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth', new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.serialization')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_unit_resource_view(self, mock_factory, mock_serializer):
        """
        Test ContentUnitResourceView when the requested unit is found.
        """
        mock_cqm = mock.MagicMock()
        mock_cqm.get_content_unit_by_id.return_value = {}
        mock_factory.content_query_manager.return_value = mock_cqm
        request = mock.MagicMock()

        mock_serializer.content.content_unit_obj.return_value = {}
        mock_serializer.content.content_unit_child_link_objs.return_value = {'child': 1}

        content_unit_resource_view = ContentUnitResourceView()
        response = content_unit_resource_view.get(request, 'mock_type', 'mock_unit')

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertFalse(isinstance(response, HttpResponseNotFound))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

        content = json.loads(response.content)
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(content['children'], {'child': 1})

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth', new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.serialization')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_missing_content_unit_resource_view(self, mock_factory, mock_serializer):
        """
        Test ContentUnitResourceView when the requested unit is not found.
        """
        mock_cqm = mock.MagicMock()
        mock_cqm.get_content_unit_by_id.side_effect = MissingResource()
        mock_factory.content_query_manager.return_value = mock_cqm
        request = mock.MagicMock()

        mock_serializer.content.content_unit_obj.return_value = {}
        mock_serializer.content.content_unit_child_link_objs.return_value = {'child': 1}

        content_unit_resource_view = ContentUnitResourceView()
        response = content_unit_resource_view.get(request, 'mock_type', 'mock_unit')

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertTrue(isinstance(response, HttpResponseNotFound))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

        expected_message = 'No content unit resource: mock_unit'
        content = json.loads(response.content)
        self.assertEqual(expected_message, content)
