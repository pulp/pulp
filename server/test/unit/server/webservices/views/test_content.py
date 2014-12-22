import json
import unittest

import mock
from django.http import HttpResponse, HttpResponseNotFound

from pulp.server.webservices.views.content import UploadResourceView


class TestUploadResourceView(unittest.TestCase):

    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_delete_upload_resource_view(self, mock_factory):
        """
        UploadResourceView should delete an upload. Since this is done using
        only helper functions, these tests should only assert the correct
        headers and that the helper was called with the correct argument.
        """
        mock_upload_manager = mock.MagicMock()
        mock_factory.content_upload_manager.return_value = mock_upload_manager
        request = mock.MagicMock()

        upload_resource_view = UploadResourceView()
        response = upload_resource_view.delete(request, 'mock_unit')

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertFalse(isinstance(response, HttpResponseNotFound))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

        content = json.loads(response.content)
        self.assertEqual(content, None)
        mock_upload_manager.delete_upload.assert_called_once_with('mock_unit')
