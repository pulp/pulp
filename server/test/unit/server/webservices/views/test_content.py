import json
import unittest

import mock
from django.http import HttpResponse, HttpResponseNotFound

from .base import assert_auth_DELETE, assert_auth_READ
from pulp.server.exceptions import OperationPostponed
from pulp.server.webservices.views.content import OrphanTypeSubCollectionView


class TestOrphanTypeSubCollectionView(unittest.TestCase):
    """
    Tests for views of orphans limited by type.
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_orphan_type_subcollection(self, mock_factory):
        """
        OrphanTypeSubCollection get should return an HttpResponse containing a list of dictionaries
        that represent each orphan for the given type.
        """
        mock_orphan_manager = mock.MagicMock()
        mock_orphan_manager.generate_orphans_by_type_with_unit_keys.return_value = [
            {'_id': 'orphan1'}, {'_id': 'orphan2'}
        ]
        mock_factory.content_orphan_manager.return_value = mock_orphan_manager
        request = mock.MagicMock()
        request.get_full_path.return_value = '/mock/path'

        orphan_type_subcollection = OrphanTypeSubCollectionView()
        response = orphan_type_subcollection.get(request, 'mock_type')

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertFalse(isinstance(response, HttpResponseNotFound))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

        content = json.loads(response.content)
        self.assertTrue(isinstance(content, list))
        self.assertTrue(len(content), 2)
        self.assertTrue(isinstance(content[0], dict))
        expected_href = '/mock/path/%s/'
        self.assertEqual(expected_href % 'orphan1', content[0]['_href'])
        self.assertEqual(expected_href % 'orphan2', content[1]['_href'])

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.content.factory')
    def test_get_orphan_type_subcollection_with_empty_list(self, mock_factory):
        """
        OrphanTypeSubCollection get should return an HttpResponse containing an empty list
        when there are no orphans of the type listed.
        """
        mock_orphan_manager = mock.MagicMock()
        mock_orphan_manager.generate_orphans_by_type_with_unit_keys.return_value = []
        mock_factory.content_orphan_manager.return_value = mock_orphan_manager
        request = mock.MagicMock()

        orphan_type_subcollection = OrphanTypeSubCollectionView()
        response = orphan_type_subcollection.get(request, 'mock_type')

        self.assertTrue(isinstance(response, HttpResponse))
        self.assertFalse(isinstance(response, HttpResponseNotFound))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

        content = json.loads(response.content)
        self.assertTrue(isinstance(content, list))
        self.assertEqual(len(content), 0)

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.orphan')
    def test_delete_orphan_type_subcollection(self, mock_orphan):
        """
        Ensure that the command to delete orphans is called with the correct arguments and that
        the function raises an OperationPostponed.
        """
        request = mock.MagicMock()
        orphan_type_subcollection = OrphanTypeSubCollectionView()
        self.assertRaises(OperationPostponed, orphan_type_subcollection.delete,
                          request, 'mock_type')

        mock_orphan.delete_orphans_by_type.apply_async.assert_called_once_with(
            ('mock_type',), tags=['pulp:content_unit:orphans']
        )

