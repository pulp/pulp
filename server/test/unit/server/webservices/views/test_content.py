import unittest

import mock

from .base import assert_auth_DELETE
from pulp.server.exceptions import OperationPostponed
from pulp.server.webservices.views.content import DeleteOrphansActionView


class TestDeleteOrphansActionView(unittest.TestCase):
    """
    Tests for the Delete Orphans Action view
    """

    @mock.patch('pulp.server.webservices.controllers.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.content.orphan_manager')
    @mock.patch('pulp.server.webservices.views.content.tags')
    def test_post_delete_orphans_action(self, mock_tags, mock_orphan_manager):
        """
        Delete orphans action view should pass the posted json object and the appropriate tags
        to the delete_orphans_by_id function. This should be done asynchronously so it should raise
        OperationPostpone.
        """
        delete_orphans_view = DeleteOrphansActionView()
        request = mock.MagicMock()
        request.body_as_json = {'fake': 'json'}
        mock_tags.action_tag.return_value = 'mock_action_tag'
        mock_tags.resource_tag.return_value = 'mock_resource_tag'

        self.assertRaises(OperationPostponed, delete_orphans_view.post, request)

        mock_orphan_manager.delete_orphans_by_id.apply_async.assert_called_once_with(
            [{'fake': 'json'}], tags=['mock_action_tag', 'mock_resource_tag']
        )
