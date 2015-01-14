import unittest

import mock

from .base import assert_auth_READ
from pulp.server.webservices.views.plugins import (DistributorResourceView, DistributorsView,
                                                   ImporterResourceView, ImportersView,
                                                   TypeResourceView, TypesView)


class TestDistributorResourceView(unittest.TestCase):
    pass


class TestDistributorsView(unittest.TestCase):
    pass


class TestImporterResourceView(unittest.TestCase):
    pass


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

