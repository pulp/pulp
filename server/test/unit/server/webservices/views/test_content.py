from gettext import gettext as _
import json
import mock
import unittest

from django.http import HttpResponseBadRequest, HttpResponseNotFound

from base import assert_auth_CREATE, assert_auth_DELETE, assert_auth_READ, assert_auth_UPDATE
from pulp.server import constants
from pulp.server.exceptions import InvalidValue, MissingResource, OperationPostponed
from pulp.server.webservices.views.content import (
    CatalogResourceView,
    ContentSourceCollectionActionView,
    ContentSourceCollectionView,
    ContentSourceResourceActionView,
    ContentSourceResourceView,
    ContentUnitResourceView,
    ContentUnitsCollectionView,
    ContentUnitSearch,
    ContentUnitUserMetadataResourceView,
    DeleteOrphansActionView,
    OrphanCollectionView,
    OrphanResourceView,
    OrphanTypeSubCollectionView,
    UploadResourceView,
    UploadsCollectionView,
    UploadSegmentResourceView
)


class TestOrphanCollectionView(unittest.TestCase):
    """
    Tests for views for all orphaned content.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.reverse')
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_orphan_collection_view(self, mock_factory, mock_resp, mock_reverse):
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
        mock_resp.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
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

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.reverse')
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_orphan_type_subcollection(self, mock_factory, mock_resp, mock_reverse):
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

        mock_resp.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_orphan_type_subcollection_with_empty_list(self, mock_factory, mock_resp):
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
        mock_resp.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.controllers.units.get_unit_key_fields_for_type', spec_set=True)
    @mock.patch('pulp.server.webservices.views.content.content_orphan')
    def test_delete_orphan_type_subcollection(self, mock_orphan_manager, mock_get_unit_key_fields):
        """
        Delete orphans should be called with the correct arguments and OperationPostponed is raised.
        """
        request = mock.MagicMock()
        mock_get_unit_key_fields.return_value = ('id',)

        orphan_type_subcollection = OrphanTypeSubCollectionView()
        self.assertRaises(OperationPostponed, orphan_type_subcollection.delete,
                          request, 'mock_type')

        mock_orphan_manager.delete_orphans_by_type.apply_async.assert_called_once_with(
            ('mock_type',), tags=['pulp:content_unit:orphans']
        )
        mock_get_unit_key_fields.assert_called_once_with('mock_type')

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth', new=assert_auth_DELETE())
    @mock.patch('pulp.server.controllers.units.get_unit_key_fields_for_type', spec_set=True)
    def test_delete_unknown_type(self, mock_get_unit_key_fields):
        mock_get_unit_key_fields.side_effect = ValueError
        request = mock.MagicMock()

        orphan_type_subcollection = OrphanTypeSubCollectionView()
        self.assertRaises(MissingResource, orphan_type_subcollection.delete, request, 'mock_type')


class TestOrphanResourceView(unittest.TestCase):
    """
    Tests for views of a specific orphan.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_orphan_resource(self, mock_factory, mock_resp):
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

        mock_resp.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.factory.content_orphan_manager')
    @mock.patch('pulp.server.webservices.views.content.content_orphan')
    def test_delete_orphan_resource(self, mock_orphan_manager, mock_orphan):
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
        mock_orphan.return_value.get_orphan.assert_called_once_with('mock_type', 'mock_id')


class TestDeleteOrphansActionView(unittest.TestCase):
    """
    Tests for the Delete Orphans Action view, deprecated in 2.4.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.content_orphan')
    @mock.patch('pulp.server.webservices.views.content.tags')
    def test_post_delete_orphans_action(self, mock_tags, mock_orphan_manager):
        """
        Test delete orphans action, should call delete_orphans_by_id with appropriate tags.
        """
        request = mock.MagicMock()
        request.body = json.dumps({'fake': 'json'})
        mock_tags.action_tag.return_value = 'mock_action_tag'
        mock_tags.resource_tag.return_value = 'mock_resource_tag'

        delete_orphans_view = DeleteOrphansActionView()
        self.assertRaises(OperationPostponed, delete_orphans_view.post, request)

        mock_orphan_manager.delete_orphans_by_id.apply_async.assert_called_once_with(
            [{'fake': 'json'}], tags=['mock_action_tag', 'mock_resource_tag']
        )

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.content_orphan')
    @mock.patch('pulp.server.webservices.views.content.tags')
    def test_post_delete_orphans_action_no_json(self, mock_tags, mock_orphan_manager):
        """
        Test delete orphans action, without json body.
        """
        request = mock.MagicMock()
        request.body = None
        mock_tags.action_tag.return_value = 'mock_action_tag'
        mock_tags.resource_tag.return_value = 'mock_resource_tag'

        delete_orphans_view = DeleteOrphansActionView()
        try:
            delete_orphans_view.post(request)
        except OperationPostponed:
            pass

        mock_orphan_manager.delete_orphans_by_id.apply_async.assert_called_once_with(
            [{}], tags=['mock_action_tag', 'mock_resource_tag']
        )


class TestCatalogResourceView(unittest.TestCase):
    """
    Tests for the catalog resource view.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_delete_catalog_resource(self, mock_factory, mock_resp):
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
        mock_resp.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)


class TestContentUnitSearch(unittest.TestCase):
    """
    Tests for ContentUnitSearch view.
    """

    @mock.patch('pulp.server.webservices.views.content.factory')
    @mock.patch('pulp.server.webservices.views.content.Criteria')
    def test_add_repo_memberships_empty(self, mock_crit, mock_factory):
        """
        Make sure it doesn't do a search for associations if there are no units found
        """
        mock_find = mock_factory.repo_unit_association_query_manager().find_by_criteria
        ContentUnitSearch()._add_repo_memberships([], 'rpm')
        self.assertEqual(mock_find.call_count, 0)

    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_add_repo_memberships_(self, mock_factory):
        """
        Ensure that _add_repo_memberships adds a list of repos for the the units.
        """
        mock_find = mock_factory.repo_unit_association_query_manager().find_by_criteria
        mock_find.return_value = [{'repo_id': 'repo1', 'unit_id': 'unit1'}]
        units = [{'_id': 'unit1'}]
        ret = ContentUnitSearch()._add_repo_memberships(units, 'rpm')
        self.assertEqual(mock_find.call_count, 1)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].get('repository_memberships'), ['repo1'])

    @mock.patch('pulp.server.webservices.views.content.ContentUnitSearch._add_repo_memberships')
    @mock.patch('pulp.server.webservices.views.content._process_content_unit')
    def test_get_results_without_repos(self, mock_process, mock_add_repo):
        """
        Get results without the optional `include_repos`.
        """
        content_search = ContentUnitSearch()
        mock_query = mock.MagicMock()
        mock_search = mock.MagicMock(return_value=['result_1', 'result_2'])
        serialized_results = content_search.get_results(mock_query, mock_search, {},
                                                        type_id='mock_type')
        mock_process.assert_has_calls([mock.call('result_1', 'mock_type'),
                                       mock.call('result_2', 'mock_type')])
        self.assertEqual(serialized_results, [mock_process.return_value, mock_process.return_value])
        self.assertEqual(mock_add_repo.call_count, 0)

    @mock.patch('pulp.server.webservices.views.content.ContentUnitSearch._add_repo_memberships')
    @mock.patch('pulp.server.webservices.views.content._process_content_unit')
    def test_get_results_with_repos(self, mock_process, mock_add_repo):
        """
        Get results with the optional `include_repos`.
        """
        content_search = ContentUnitSearch()
        mock_query = mock.MagicMock()
        mock_search = mock.MagicMock(return_value=['result_1', 'result_2'])
        serialized_results = content_search.get_results(
            mock_query, mock_search, {'include_repos': True}, type_id='mock_type'
        )
        mock_process.assert_has_calls([mock.call('result_1', 'mock_type'),
                                       mock.call('result_2', 'mock_type')])
        self.assertEqual(serialized_results, [mock_process.return_value, mock_process.return_value])
        mock_add_repo.assert_called_once_with([mock_process(), mock_process()], 'mock_type')


class TestContentUnitResourceView(unittest.TestCase):
    """
    Tests for views of a single content unit.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.content.serial_content')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_unit_resource_view(self, mock_factory, mock_serializers,
                                            mock_resp):
        """
        Test ContentUnitResourceView when the requested unit is found.
        """

        mock_cqm = mock.MagicMock()
        mock_cqm.get_content_unit_by_id.return_value = {}
        mock_factory.content_query_manager.return_value = mock_cqm
        request = mock.MagicMock()

        mock_serializers.content_unit_obj.return_value = {}
        mock_serializers.content_unit_child_link_objs.return_value = {'child': 1}

        content_unit_resource_view = ContentUnitResourceView()
        response = content_unit_resource_view.get(request, 'mock_type', 'mock_unit')

        expected_content = {'children': {'child': 1}}
        mock_resp.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_unit_resource_view_missing_content(self, mock_factory, mock_resp):
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
        mock_resp.assert_called_once_with(msg, response_class=HttpResponseNotFound)
        self.assertTrue(response is mock_resp.return_value)


class TestContentUnitsCollectionView(unittest.TestCase):
    """
    Tests for content units of a particular type.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.reverse')
    @mock.patch('pulp.server.webservices.views.content.serial_content')
    @mock.patch('pulp.server.webservices.views.content.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_units_collection_view(self, mock_factory, mock_resp,
                                               mock_serializers, mock_rev):
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
        mock_serializers.content_unit_obj.side_effect = identity
        mock_serializers.content_unit_child_link_objs.return_value = 'child'
        request = mock.MagicMock()

        content_units_collection_view = ContentUnitsCollectionView()
        response = content_units_collection_view.get(request, {'content_type': 'mock_type'})

        expected_content = [{'_id': 'unit_1', '_href': mock_rev.return_value, 'children': 'child'},
                            {'_id': 'unit_2', '_href': mock_rev.return_value, 'children': 'child'}]
        mock_resp.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)


class TestContentUnitUserMetadataResourceView(unittest.TestCase):
    """
    Tests for ContentUnitUserMetadataResourceView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.serial_content')
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_unit_user_metadata_resource(self, mock_factory, mock_resp, mock_serial):
        """
        View should return a response contains user metadata
        """
        mock_unit = {constants.PULP_USER_METADATA_FIELDNAME: 'mock_metadata'}
        mock_cqm = mock_factory.content_query_manager()
        mock_cqm.get_content_unit_by_id.return_value = mock_unit
        mock_serial.content_unit_obj.return_value = 'mock_serial_metadata'
        request = mock.MagicMock()

        metadata_resource = ContentUnitUserMetadataResourceView()
        response = metadata_resource.get(request, 'mock_type', 'mock_unit')

        mock_serial.content_unit_obj.assert_called_once_with('mock_metadata')
        expected_content = 'mock_serial_metadata'
        mock_resp.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_content_unit_user_metadata_resource_no_unit(self, mock_factory, mock_resp):
        """
        View should return a response not found and a helpful message when unit is not found.
        """
        request = mock.MagicMock()
        mock_cqm = mock_factory.content_query_manager()
        mock_cqm.get_content_unit_by_id.side_effect = MissingResource()

        metadata_resource = ContentUnitUserMetadataResourceView()
        response = metadata_resource.get(request, 'mock_type', 'mock_unit')

        msg = _('No content unit resource: mock_unit')
        mock_resp.assert_called_once_with(msg, HttpResponseNotFound)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_put_content_unit_user_metadata_resource(self, mock_factory, mock_resp):
        """
        Test update content unit user metdata resource.
        """
        request = mock.MagicMock()
        request.body = json.dumps('mock_data')
        mock_cm = mock_factory.content_manager()

        metadata_resource = ContentUnitUserMetadataResourceView()
        response = metadata_resource.put(request, 'mock_type', 'mock_unit')

        mock_delta = {constants.PULP_USER_METADATA_FIELDNAME: 'mock_data'}
        mock_cm.update_content_unit.assert_called_once_with('mock_type', 'mock_unit', mock_delta)
        mock_resp.assert_called_with(None)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_put_content_unit_user_metadata_resource_no_unit(self, mock_factory, mock_resp):
        """
        View should return a response not found and a helpful message when unit is not found.
        """
        request = mock.MagicMock()
        request.body = json.dumps('')
        mock_cqm = mock_factory.content_query_manager()
        mock_cqm.get_content_unit_by_id.side_effect = MissingResource()

        metadata_resource = ContentUnitUserMetadataResourceView()
        response = metadata_resource.put(request, 'mock_type', 'mock_unit')

        msg = _('No content unit resource: mock_unit')
        mock_resp.assert_called_once_with(msg, HttpResponseNotFound)
        self.assertTrue(response is mock_resp.return_value)


class TestUploadsCollectionView(unittest.TestCase):
    """
    Tests for views of all uploads.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_uploads_collection_view(self, mock_factory, mock_resp):
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
        mock_resp.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.content.generate_redirect_response')
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.reverse')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_post_uploads_collection_view(self, mock_factory, mock_reverse, mock_resp,
                                          mock_redirect):
        """
        View post should return a response that contains data for a new upload.
        """
        mock_upload_manager = mock.MagicMock()
        mock_upload_manager.initialize_upload.return_value = 'mock_id'
        mock_factory.content_upload_manager.return_value = mock_upload_manager

        request = mock.MagicMock()
        request.body = None
        mock_reverse.return_value = '/mock/path/'

        content_types_view = UploadsCollectionView()
        response = content_types_view.post(request)

        self.assertTrue(mock_upload_manager.initialize_upload.called)

        mock_resp.assert_called_once_with({'upload_id': 'mock_id', '_href': '/mock/path/'})
        mock_redirect.assert_called_once_with(mock_resp.return_value, '/mock/path/')
        self.assertTrue(response is mock_redirect.return_value)


class TestUploadSegmentResourceView(unittest.TestCase):
    """
    Tests for views for uploads to a specific id.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_put_upload_segment_resource(self, mock_factory, mock_resp):
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
        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
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

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response')
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_delete_upload_resource_view(self, mock_factory, mock_resp):
        """
        View should delete an upload and return a response containing None.
        """
        mock_upload_manager = mock.MagicMock()
        mock_factory.content_upload_manager.return_value = mock_upload_manager
        request = mock.MagicMock()

        upload_resource_view = UploadResourceView()
        response = upload_resource_view.delete(request, 'mock_unit')

        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)
        mock_upload_manager.delete_upload.assert_called_once_with('mock_unit')


class TestContentSourceCollectionView(unittest.TestCase):
    """
    Tests for content sources
    """
    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.content.sources.container.ContentSource.load_all')
    def test_get_content_source(self, mock_sources, mock_resp):
        """
        List all sources
        """
        source = mock.MagicMock()
        source.id = 'my-id'
        source.dict.return_value = {'source_id': 'my-id'}
        mock_sources.return_value = {'mock': source}

        request = mock.MagicMock()
        content_source_view = ContentSourceCollectionView()
        response = content_source_view.get(request)

        mock_resp.assert_called_once_with([{'source_id': 'my-id',
                                            '_href': '/v2/content/sources/my-id/'}])
        self.assertTrue(response is mock_resp.return_value)


class TestContentSourceCollectionActionView(unittest.TestCase):
    """
    Tests for content sources
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    def test_post_bad_request_content_source(self):
        """
        Test content source invalid action
        """
        request = mock.MagicMock()
        request.body = None
        content_source_view = ContentSourceCollectionActionView()
        response = content_source_view.post(request, 'no-such-action')

        self.assertTrue(isinstance(response, HttpResponseBadRequest))
        self.assertEqual(response.status_code, 400)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.content.tags')
    @mock.patch('pulp.server.content.sources.container.ContentSource.load_all')
    @mock.patch('pulp.server.webservices.views.content.content.refresh_content_sources')
    def test_refresh_content_source(self, mock_refresh, mock_sources, mock_tags):
        """
        Test refresh content sources
        """
        source = mock.MagicMock()
        source.id = 'some-source'
        source.dict.return_value = {'source_id': 'some-source'}
        mock_sources.return_value = {'some-source': source}

        mock_task_tags = [mock_tags.action_tag.return_value, mock_tags.resource_tag.return_value]

        request = mock.MagicMock()
        request.body = None
        content_source_view = ContentSourceCollectionActionView()
        try:
            content_source_view.post(request, 'refresh')
        except OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raised for asynchronous call.')
        self.assertEqual(response.http_status_code, 202)

        mock_refresh.apply_async.assert_called_with(tags=mock_task_tags)


class TestContentSourceResourceView(unittest.TestCase):
    """
    Tests for content sources resource
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.content.sources.container.ContentSource.load_all')
    def test_get_content_source_resource(self, mock_sources, mock_resp):
        """
        Get specific content source
        """
        source = mock.MagicMock()
        source.id = 'some-source'
        source.dict.return_value = {'source_id': 'some-source'}
        mock_sources.return_value = {'some-source': source}

        request = mock.MagicMock()
        content_source_view = ContentSourceResourceView()
        response = content_source_view.get(request, 'some-source')

        mock_resp.assert_called_once_with(
            {'source_id': 'some-source', '_href': '/v2/content/sources/some-source/'})
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.content.sources.container.ContentSource.load_all')
    def test_get_invalid_content_source_resource(self, mock_sources):
        """
        Get invalid content source
        """
        mock_sources.return_value = {}

        request = mock.MagicMock()
        content_source_view = ContentSourceResourceView()
        try:
            content_source_view.get(request, 'some-source')
        except MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised with missing resource id")
        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'source_id': 'some-source'})


class TestContentSourceResourceActionView(unittest.TestCase):
    """
    Tests for content sources resource
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.content.sources.container.ContentSource.load_all')
    def test_post_invalid_action(self, mock_sources):
        """
        Test specific content source invalid action
        """
        source = mock.MagicMock()
        source.id = 'some-source'
        source.dict.return_value = {'source_id': 'some-source'}
        mock_sources.return_value = {'some-source': source}

        request = mock.MagicMock()
        request.body = None
        content_source_view = ContentSourceResourceActionView()
        response = content_source_view.post(request, 'some-source', 'no-such-action')

        self.assertTrue(isinstance(response, HttpResponseBadRequest))
        self.assertEqual(response.status_code, 400)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.content.sources.container.ContentSource.load_all')
    def test_refresh_invalid_content_source(self, mock_sources):
        """
        Test refresh invalid content source
        """
        mock_sources.return_value = {}

        request = mock.MagicMock()
        request.body = None
        content_source_view = ContentSourceResourceActionView()
        try:
            content_source_view.post(request, 'some-source', 'refresh')
        except MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised with missing resource id")
        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'source_id': 'some-source'})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.content.tags')
    @mock.patch('pulp.server.content.sources.container.ContentSource.load_all')
    @mock.patch('pulp.server.webservices.views.content.content.refresh_content_source')
    def test_refresh_specific_action(self, mock_refresh, mock_sources, mock_tags):
        """
        Test refresh specific content source
        """
        source = mock.MagicMock()
        source.id = 'some-source'
        source.dict.return_value = {'source_id': 'some-source'}
        mock_sources.return_value = {'some-source': source}

        mock_task_tags = [mock_tags.action_tag.return_value, mock_tags.resource_tag.return_value]

        request = mock.MagicMock()
        request.body = None
        content_source_view = ContentSourceResourceActionView()
        try:
            content_source_view.post(request, 'some-source', 'refresh')
        except OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raised for asynchronous call.')
        self.assertEqual(response.http_status_code, 202)

        mock_refresh.apply_async.assert_called_with(
            tags=mock_task_tags, kwargs={'content_source_id': 'some-source'})
