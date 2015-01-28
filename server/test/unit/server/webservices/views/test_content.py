from gettext import gettext as _
import json
import mock
import unittest

from django.http import HttpResponseNotFound, HttpResponseRedirect

from .base import assert_auth_DELETE, assert_auth_READ, assert_auth_CREATE, assert_auth_UPDATE
from pulp.server.exceptions import InvalidValue, MissingResource, OperationPostponed
from pulp.server.webservices.views.content import (
    CatalogResourceView, ContentTypeResourceView, ContentTypesView, ContentUnitResourceView,
    ContentUnitsCollectionView, DeleteOrphansActionView, OrphanCollectionView,
    OrphanTypeSubCollectionView, OrphanResourceView, UploadResourceView, UploadsCollectionView,
    UploadSegmentResourceView
)


class TestOrphanCollectionView(unittest.TestCase):
    """
    Tests for views for all orphaned content.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.reverse')
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_orphan_collection_view(self, mock_factory, mock_serializer, mock_reverse):
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
        mock_reverse.return_value = '/mock/path/'

        orphan_collection = OrphanCollectionView()
        response = orphan_collection.get(request)

        expected_content = {
            'orphan1': {
                'count': 1,
                '_href': '/mock/path/',
            },
            'orphan2': {
                'count': 2,
                '_href': '/mock/path/',
            },
        }
        mock_serializer.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_serializer.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.content_orphan')
    def test_delete_orphan_collection_view(self, mock_orphan_manager):
        """
        Delete orphan collection view should call the delete all orphans function.
        """
        request = mock.MagicMock()
        orphan_collection = OrphanCollectionView()
        self.assertRaises(OperationPostponed, orphan_collection.delete, request)

        mock_orphan_manager.delete_all_orphans.apply_async.assert_called_once_with(
            tags=['pulp:content_unit:orphans']
        )


class TestOrphanTypeSubCollectionView(unittest.TestCase):
    """
    Tests for views of orphans limited by type.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.reverse')
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_orphan_type_subcollection(self, mock_factory, mock_serializer, mock_reverse):
        """
        OrphanTypeSubCollection should return a response from a list of dicts, one for each orphan.
        """
        mock_orphan_manager = mock.MagicMock()
        mock_orphan_manager.generate_orphans_by_type_with_unit_keys.return_value = [
            {'_id': 'orphan1'}, {'_id': 'orphan2'}
        ]
        mock_factory.content_orphan_manager.return_value = mock_orphan_manager
        request = mock.MagicMock()
        mock_reverse.return_value = '/mock/path/'

        orphan_type_subcollection = OrphanTypeSubCollectionView()
        response = orphan_type_subcollection.get(request, 'mock_type')

        expected_content = [{'_id': 'orphan1', '_href': '/mock/path/'},
                            {'_id': 'orphan2', '_href': '/mock/path/'}]

        mock_serializer.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_serializer.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_orphan_type_subcollection_with_empty_list(self, mock_factory, mock_serializer):
        """
        View should return a response with an empty list when there are no orphans of the type.
        """
        mock_orphan_manager = mock.MagicMock()
        mock_orphan_manager.generate_orphans_by_type_with_unit_keys.return_value = []
        mock_factory.content_orphan_manager.return_value = mock_orphan_manager
        request = mock.MagicMock()

        orphan_type_subcollection = OrphanTypeSubCollectionView()
        response = orphan_type_subcollection.get(request, 'mock_type')

        expected_content = []
        mock_serializer.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_serializer.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.content_orphan')
    def test_delete_orphan_type_subcollection(self, mock_orphan_manager):
        """
        Delete orphans should be called with the correct arguments and OperationPostponed is raised.
        """
        request = mock.MagicMock()

        orphan_type_subcollection = OrphanTypeSubCollectionView()
        self.assertRaises(OperationPostponed, orphan_type_subcollection.delete,
                          request, 'mock_type')

        mock_orphan_manager.delete_orphans_by_type.apply_async.assert_called_once_with(
            ('mock_type',), tags=['pulp:content_unit:orphans']
        )


class TestOrphanResourceView(unittest.TestCase):
    """
    Tests for views of a specific orphan.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_orphan_resource(self, mock_factory, mock_serializer):
        """
        Test get OrphanResourceView, which should return a dict describing an orphan.
        """
        mock_orphan_manager = mock.MagicMock()
        mock_orphan_manager.get_orphan.return_value = {'_id': 'orphan'}
        mock_factory.content_orphan_manager.return_value = mock_orphan_manager
        request = mock.MagicMock()
        request.get_full_path.return_value = '/mock/path/'

        orphan_resource = OrphanResourceView()
        response = orphan_resource.get(request, 'mock_type', 'mock_id')

        expected_content = {'_id': 'orphan', '_href': '/mock/path/'}

        mock_serializer.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_serializer.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.content_orphan')
    def test_delete_orphan_resource(self, mock_orphan_manager):
        """
        OrphanResourceView should call delete orphans by id and raise OperationPostponed.
        """
        request = mock.MagicMock()

        orphan_resource = OrphanResourceView()
        self.assertRaises(OperationPostponed, orphan_resource.delete,
                          request, 'mock_type', 'mock_id')

        mock_orphan_manager.delete_orphans_by_id.apply_async.assert_called_once_with(
            ([{'content_type_id': 'mock_type', 'unit_id': 'mock_id'}],),
            tags=['pulp:content_unit:orphans']
        )


class TestDeleteOrphansActionView(unittest.TestCase):
    """
    Tests for the Delete Orphans Action view, deprecated in 2.4.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.content_orphan')
    @mock.patch('pulp.server.webservices.views.content.tags')
    def test_post_delete_orphans_action(self, mock_tags, mock_orphan_manager):
        """
        Test delete orphans action, should call delete_orphans_by_id with appropriate tags.
        """
        request = mock.MagicMock()
        request.body_as_json = {'fake': 'json'}
        mock_tags.action_tag.return_value = 'mock_action_tag'
        mock_tags.resource_tag.return_value = 'mock_resource_tag'

        delete_orphans_view = DeleteOrphansActionView()
        self.assertRaises(OperationPostponed, delete_orphans_view.post, request)

        mock_orphan_manager.delete_orphans_by_id.apply_async.assert_called_once_with(
            [{'fake': 'json'}], tags=['mock_action_tag', 'mock_resource_tag']
        )


class TestCatalogResourceView(unittest.TestCase):
    """
    Tests for the catalog resource view.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_delete_catalog_resource(self, mock_factory, mock_serializer):
        """
        Test that delete returns a serialized response containing a dict with the
        appropriate information.
        """
        mock_manager = mock.MagicMock()
        mock_manager.purge.return_value = 82
        mock_factory.content_catalog_manager.return_value = mock_manager

        request = mock.MagicMock()

        catalog_resource_view = CatalogResourceView()
        response = catalog_resource_view.delete(request, 'mock_id')

        expected_content = {'deleted': 82}
        mock_serializer.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_serializer.return_value)


class TestContentTypeResourceView(unittest.TestCase):
    """
    Test views of a specific content type.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.content.serialization')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_type_resource_view_valid_content_type(self, mock_factory,
                                                               mock_serialization, mock_serializer):
        """
        View should return a response containing a serialized dict for the given contentent type.
        """
        mock_cqm = mock.MagicMock()
        mock_cqm.get_content_type.return_value = 'Not None'
        mock_factory.content_query_manager.return_value = mock_cqm
        mock_serialization.content.content_type_obj.return_value = {}
        request = mock.MagicMock()
        request.get_full_path.return_value = '/mock/path/'

        content_type_resource_view = ContentTypeResourceView()
        response = content_type_resource_view.get(request, 'mock_type')

        expected_content = {'actions': {'_href': '/mock/path/actions/'},
                            'content_units': {'_href': '/mock/path/units/'}}

        mock_serializer.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_serializer.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.serialization')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_type_resource_view_invalid_type(self, mock_factory,
                                                         mock_serialization, mock_serializer):
        """
        View should return a response that contains a message about the missing content.
        """
        mock_cqm = mock.MagicMock()
        mock_cqm.get_content_type.return_value = None
        mock_factory.content_query_manager.return_value = mock_cqm
        request = mock.MagicMock()

        content_type_resource_view = ContentTypeResourceView()
        response = content_type_resource_view.get(request, 'invalid_type')

        msg = _('No content type resource: invalid_type')
        mock_serializer.assert_called_once_with(msg, response_class=HttpResponseNotFound)
        self.assertTrue(response is mock_serializer.return_value)


class TestContentTypesView(unittest.TestCase):
    """
    Tests for views of all content types.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_types_view(self, mock_factory, mock_serializer):
        """
        View should return a response that contains a list of dicts, one for each content type.
        """
        mock_cqm = mock.MagicMock()
        mock_cqm.list_content_types.return_value = ['rpm', 'other']
        mock_factory.content_query_manager.return_value = mock_cqm
        request = mock.MagicMock()

        content_types_view = ContentTypesView()
        response = content_types_view.get(request)

        expected_content = [{'_href': '/v2/content/types/rpm/', 'content_type': 'rpm'},
                            {'_href': '/v2/content/types/other/', 'content_type': 'other'}]
        mock_serializer.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_serializer.return_value)


class TestContentUnitResourceView(unittest.TestCase):
    """
    Tests for views of a single conttent unit.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.content.serialization')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_unit_resource_view(self, mock_factory, mock_serialization,
                                            mock_serializer):
        """
        Test ContentUnitResourceView when the requested unit is found.
        """

        mock_cqm = mock.MagicMock()
        mock_cqm.get_content_unit_by_id.return_value = {}
        mock_factory.content_query_manager.return_value = mock_cqm
        request = mock.MagicMock()

        mock_serialization.content.content_unit_obj.return_value = {}
        mock_serialization.content.content_unit_child_link_objs.return_value = {'child': 1}

        content_unit_resource_view = ContentUnitResourceView()
        response = content_unit_resource_view.get(request, 'mock_type', 'mock_unit')

        expected_content = {'children': {'child': 1}}
        mock_serializer.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_serializer.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_unit_resource_view_missing_content(self, mock_factory, mock_serializer):
        """
        Test ContentUnitResourceView when the requested unit is not found.
        """
        mock_cqm = mock.MagicMock()
        mock_cqm.get_content_unit_by_id.side_effect = MissingResource()
        mock_factory.content_query_manager.return_value = mock_cqm
        request = mock.MagicMock()

        content_unit_resource_view = ContentUnitResourceView()
        response = content_unit_resource_view.get(request, 'mock_type', 'mock_unit')

        msg = _('No content unit resource: mock_unit')
        mock_serializer.assert_called_once_with(msg, response_class=HttpResponseNotFound)
        self.assertTrue(response is mock_serializer.return_value)


class TestContentUnitsCollectionView(unittest.TestCase):
    """
    Tests for content units of a particular type.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.serialization')
    @mock.patch('pulp.server.webservices.views.content.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_units_collection_view(self, mock_factory, mock_serializer,
                                               mock_serialization):
        """
        View should return a response that contains a list of dicts, one for each content unit.
        """

        def identity(arg):
            """
            Allow a side effect to return an argument.
            """
            return arg

        mock_cqm = mock.MagicMock()
        mock_cqm.find_by_criteria.return_value = [{'_id': 'unit_1'}, {'_id': 'unit_2'}]
        mock_factory.content_query_manager.return_value = mock_cqm
        mock_serialization.content.content_unit_obj.side_effect = identity
        mock_serialization.content.content_unit_child_link_objs.return_value = 'child'
        request = mock.MagicMock()
        request.get_full_path.return_value = '/mock/path/'

        content_units_collection_view = ContentUnitsCollectionView()
        response = content_units_collection_view.get(request, {'content_type': 'mock_type'})

        expected_content = [{'_id': 'unit_1', '_href': '/mock/path/unit_1/', 'children': 'child'},
                            {'_id': 'unit_2', '_href': '/mock/path/unit_2/', 'children': 'child'}]
        mock_serializer.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_serializer.return_value)


class TestUploadsCollectionView(unittest.TestCase):
    """
    Tests for views of all uploads.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_uploads_collection_view(self, mock_factory, mock_serializer):
        """
        View should return an response that contains a serialized dict with a list of upload_ids.
        """
        mock_upload_manager = mock.MagicMock()
        mock_upload_manager.list_upload_ids.return_value = ['mock_upload_1', 'mock_upload_2']
        mock_factory.content_upload_manager.return_value = mock_upload_manager
        request = mock.MagicMock()

        content_types_view = UploadsCollectionView()
        response = content_types_view.get(request)

        expected_content = {'upload_ids': ['mock_upload_1', 'mock_upload_2']}
        mock_serializer.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_serializer.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.content.reverse')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_post_uploads_collection_view(self, mock_factory, mock_reverse):
        """
        View post should return a response that contains data for a new upload.
        """
        mock_upload_manager = mock.MagicMock()
        mock_upload_manager.initialize_upload.return_value = 'mock_id'
        mock_factory.content_upload_manager.return_value = mock_upload_manager

        request = mock.MagicMock()
        mock_reverse.return_value = '/mock/path/'

        content_types_view = UploadsCollectionView()
        response = content_types_view.post(request)

        self.assertTrue(isinstance(response, HttpResponseRedirect))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.reason_phrase, "Created")
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

        content = json.loads(response.content)
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(content['_href'], '/mock/path/')
        self.assertEqual(content['upload_id'], 'mock_id')
        self.assertTrue(mock_upload_manager.initialize_upload.called)


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


class TestUploadResourceView(unittest.TestCase):
    """
    Tests for views of a single upload.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_delete_upload_resource_view(self, mock_factory, mock_serializer):
        """
        View should delete an upload and return a response containing None.
        """
        mock_upload_manager = mock.MagicMock()
        mock_factory.content_upload_manager.return_value = mock_upload_manager
        request = mock.MagicMock()

        upload_resource_view = UploadResourceView()
        response = upload_resource_view.delete(request, 'mock_unit')

        mock_serializer.assert_called_once_with(None)
        self.assertTrue(response is mock_serializer.return_value)
        mock_upload_manager.delete_upload.assert_called_once_with('mock_unit')
