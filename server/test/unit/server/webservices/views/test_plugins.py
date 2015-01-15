import unittest

import mock

from .base import assert_auth_READ
from pulp.server.exceptions import MissingResource
from pulp.server.webservices.views.plugins import (DistributorResourceView, DistributorsView,
                                                   ImporterResourceView, ImportersView,
                                                   TypeResourceView, TypesView)


class TestDistributorResourceView(unittest.TestCase):
    pass


class TestDistributorsView(unittest.TestCase):
    pass


class TestImporterResourceView(unittest.TestCase):
    """
    Tests for the views of a single importer.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.plugins.generate_json_response')
    @mock.patch('pulp.server.webservices.views.plugins.factory')
    def test_get_importer_resource_view_existing_importer(self, mock_factory, mock_serializer):
        """
        Importer Resource should return a generate a serialized response with importer data.
        """
        mock_manager = mock.MagicMock()
        mock_manager.importers.return_value = [{'id': 'mock_importer_1'}, {'id': 'mock_importer_2'}]
        mock_factory.plugin_manager.return_value = mock_manager
        request = mock.MagicMock()
        request.get_full_path.return_value = '/mock/path/'

        importer_resource = ImporterResourceView()
        response = importer_resource.get(request, 'mock_importer_2')

        expected_content = {'id': 'mock_importer_2', '_href': '/mock/path/'}
        mock_serializer.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_serializer.return_value)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.plugins.factory')
    def test_get_importer_resource_view_nonexistent_importer(self, mock_factory):
        """
        Importer Resource should raise a MissingResource if the specified importer does not exist.
        """
        mock_manager = mock.MagicMock()
        mock_manager.importers.return_value = [{'id': 'mock_importer_1'}, {'id': 'mock_importer_2'}]
        mock_factory.plugin_manager.return_value = mock_manager
        request = mock.MagicMock()

        importer_resource = ImporterResourceView()
        try:
            importer_resource.get(request, 'nonexistent_importer')
        except MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised for nonexistent_importer")

        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'],
                         {'importer_type_id': 'nonexistent_importer'})


class TestImportersView(unittest.TestCase):
    pass


class TestTypeResourceView(unittest.TestCase):
    pass


class TestTypesView(unittest.TestCase):
    """
    Tests for the views for all plugin types.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.plugins.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.plugins.factory')
    def test_get_types_view(self, mock_factory, mock_serializer):
        """
        Types View should return a list of objects representing each type.
        """
        mock_type = [{'id': 'mock_id'}]
        mock_plugin_manager = mock.MagicMock()
        mock_plugin_manager.types.return_value = mock_type
        mock_factory.plugin_manager.return_value = mock_plugin_manager
        request = mock.MagicMock()
        request.get_full_path.return_value = '/mock/path'

        types_view = TypesView()
        types_view.get(request)

        expected_content = [{'id': 'mock_id', '_href': '/mock/path/mock_id/'}]
        mock_serializer.assert_called_once_with(expected_content)

