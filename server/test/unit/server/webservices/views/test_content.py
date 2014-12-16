import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'pulp.server.webservices.settings'

import json
import unittest

import mock
from django.http import HttpResponse, HttpResponseNotFound

from pulp.server.webservices.views.content import ContentTypesView


class TestContentTypesView(unittest.TestCase):

    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_content_types_view_get(self, mock_factory):
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

        content = json.loads(response.content)[0]
        expected_href = '/v2/content/types/rpm/'
        self.assertEqual(expected_href, content['_href'])
        self.assertEqual('rpm', content['content_type'])