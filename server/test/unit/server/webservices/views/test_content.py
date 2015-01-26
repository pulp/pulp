import unittest

import mock

from .base import assert_auth_DELETE, assert_auth_READ, assert_auth_UPDATE
from pulp.server.exceptions import InvalidValue, OperationPostponed
from pulp.server.webservices.views.content import OrphanCollectionView, UploadSegmentResourceView


class TestOrphanCollectionView(unittest.TestCase):
    """
    Tests for views for all orphaned content.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_orphan_collection_view(self, mock_factory, mock_serializer):
        """
        Orphan collection should create a response from a dict of orphan dicts.
        """
        mock_orphans = {
            'orphan1': 1,
            'orphan2': 2,
        }
        mock_orphan_manager = mock.MagicMock()
        mock_orphan_manager.orphans_summary.return_value = mock_orphans
        mock_factory.content_orphan_manager.return_value = mock_orphan_manager
        request = mock.MagicMock()
        request.get_full_path.return_value = '/mock/path/'

        orphan_collection = OrphanCollectionView()
        response = orphan_collection.get(request)

        expected_content = {
            'orphan1': {
                'count': 1,
                '_href': '/mock/path/orphan1/',
            },
            'orphan2': {
                'count': 2,
                '_href': '/mock/path/orphan2/',
            },
        }
        mock_serializer.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_serializer.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.orphan')
    def test_delete_orphan_collection_view(self, mock_orphan):
        """
        Test that delete orphan collection view calls the appopriate function
        with the correct arguments.
        """
        request = mock.MagicMock()
        orphan_collection = OrphanCollectionView()
        self.assertRaises(OperationPostponed, orphan_collection.delete, request)

        mock_orphan.delete_all_orphans.apply_async.assert_called_once_with(
            tags=['pulp:content_unit:orphans']
        )


class TestUploadSegmentResourceView(unittest.TestCase):
    """
    Tests for views for uploads to a specific id.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_put_upload_segment_resource(self, mock_factory, mock_serializer):
        """
        Test the UploadSegmentResourceView under normal conditions
        """
        mock_upload_manager = mock.MagicMock()
        mock_factory.content_upload_manager.return_value = mock_upload_manager
        request = mock.MagicMock()
        request.body = 'upload these bits'

        upload_segment_resource = UploadSegmentResourceView()
        response = upload_segment_resource.put(request, 'mock_id', 4)

        mock_upload_manager.save_data.assert_called_once_with('mock_id', 4, 'upload these bits')
        mock_serializer.assert_called_once_with(None)
        self.assertTrue(response is mock_serializer.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_put_upload_segment_resource_bad_offset(self, mock_factory):
        """
        Test the UploadSegmentResourceView with an invalid offset value (not an int)
        """
        mock_upload_manager = mock.MagicMock()
        mock_factory.content_upload_manager.return_value = mock_upload_manager
        request = mock.MagicMock()

        upload_segment_resource = UploadSegmentResourceView()

        self.assertRaises(InvalidValue, upload_segment_resource.put,
                          request, 'mock_id', 'invalid_offset')
