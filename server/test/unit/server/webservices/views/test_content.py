import json
import unittest

import mock
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect

from pulp.server.webservices.views.content import UploadsCollectionView


class TestUploadsCollectionView(unittest.TestCase):

    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_uploads_collection_view(self, mock_factory):
        """
        UploadsCollectionView get should return an HttpResponse that contains
        a dict with a list of upload_ids.
        """
        mock_upload_manager = mock.MagicMock()
        mock_upload_manager.list_upload_ids.return_value = ['mock_id1', 'mock_id2']
        mock_factory.content_upload_manager.return_value = mock_upload_manager
        request = mock.MagicMock()

        content_types_view = UploadsCollectionView()
        response = content_types_view.get(request)

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertFalse(isinstance(response, HttpResponseNotFound))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

        content = json.loads(response.content)
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(content['upload_ids'], ['mock_id1', 'mock_id2'])

    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_post_content_types_view(self, mock_factory):
        """
        UploadsCollectionView post return a response that indicates that a new upload id has been
        created and provide a url based for it.
        """
        mock_upload_manager = mock.MagicMock()
        mock_upload_manager.initialize_upload.return_value = 'mock_id'
        mock_factory.content_upload_manager.return_value = mock_upload_manager

        request = mock.MagicMock()
        request.get_full_path.return_value = '/mock/full/path/'

        content_types_view = UploadsCollectionView()
        response = content_types_view.post(request)

        self.assertTrue(isinstance(response, HttpResponseRedirect))
        self.assertFalse(isinstance(response, HttpResponseNotFound))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.reason_phrase, "Created")
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

        content = json.loads(response.content)
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(content['_href'], '/mock/full/path/mock_id/')
        self.assertEqual(content['upload_id'], 'mock_id')
