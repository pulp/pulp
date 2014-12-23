import json
import unittest

import mock
from django.http import HttpResponse, HttpResponseNotFound

from pulp.server.exceptions import OperationPostponed
from pulp.server.webservices.views.content import OrphanResourceView


class TestOrphanResourceView(unittest.TestCase):

    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_orphan_resource(self, mock_factory):
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

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertFalse(isinstance(response, HttpResponseNotFound))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

        content = json.loads(response.content)
        self.assertTrue(isinstance(content, dict))
        expected_href = '/mock/path/'
        self.assertEqual(expected_href, content['_href'])

    @mock.patch('pulp.server.webservices.views.content.orphan')
    def test_delete_orphan_resource(self, mock_orphan):
        """
        Test delete OrphanResourceView, which should simply call helpers with the correct
        arguments. It should raise OperationPostponed.
        """
        request = mock.MagicMock()
        orphan_resource = OrphanResourceView()
        self.assertRaises(OperationPostponed, orphan_resource.delete, request, 'mock_type', 'mock_id')

        mock_orphan.delete_orphans_by_id.apply_async.assert_called_once_with(
            ([{'content_type_id': 'mock_type', 'unit_id': 'mock_id'}],), tags=['pulp:content_unit:orphans']
        )

