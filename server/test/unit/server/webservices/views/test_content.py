import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'pulp.server.webservices.settings'

import json
import unittest

import mock
from django.http import HttpResponse, HttpResponseNotFound

from pulp.server.webservices.views.content import ContentTypesView


class TestContentTypesView(unittest.TestCase):

    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get(self, mock_factory):
        mock_cqm = mock.MagicMock()
        mock_cqm.list_content_types.return_value = ['rpm']
        mock_factory.content_query_manager.return_value = mock_cqm
        request = mock.MagicMock()

        self.content_types_view = ContentTypesView()
        response = self.content_types_view.get(request)

        self.assertIsInstance(response, HttpResponse)
        self.assertNotIsInstance(response, HttpResponseNotFound)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._headers.get('content-type'), ('Content-Type', 'application/json'))
        self.assertIn('_href', json.loads(response.content)[0])
        self.assertIn('content_type', json.loads(response.content)[0])

        expected_href = '/v2/content/types/rpm/'
        self.assertEqual(expected_href, json.loads(response.content)[0]['_href'])
        self.assertEqual('rpm', json.loads(response.content)[0]['content_type'])