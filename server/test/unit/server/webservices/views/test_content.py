import json
import unittest

import mock
from django.http import HttpResponse, HttpResponseNotFound

from .base import assert_auth_DELETE
from pulp.server.webservices.views.content import CatalogResourceView


class TestCatalogResourceView(unittest.TestCase):

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth', new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_delete_catalog_resource(self, mock_factory):
        """
        Test the catalog resource view
        """
        mock_manager = mock.MagicMock()
        mock_manager.purge.return_value = 82
        mock_factory.content_catalog_manager.return_value = mock_manager

        request = mock.MagicMock()

        catalog_resource_view = CatalogResourceView()
        response = catalog_resource_view.delete(request, 'mock_id')

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertFalse(isinstance(response, HttpResponseNotFound))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

        content = json.loads(response.content)
        self.assertEqual(content['deleted'], 82)
        mock_manager.purge.assert_called_once_with('mock_id')
