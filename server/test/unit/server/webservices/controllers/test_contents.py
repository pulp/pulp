"""
Test the pulp.server.webservices.controllers.contents module.
"""

import mock

from .... import base
from pulp.devel import mock_plugins
from pulp.plugins.loader import api as plugin_api


class ContentsTest(base.PulpWebserviceTests):

    def setUp(self):
        super(ContentsTest, self).setUp()
        plugin_api._create_manager()
        mock_plugins.install()

    def tearDown(self):
        super(ContentsTest, self).tearDown()
        mock_plugins.reset()

    @mock.patch('pulp.server.managers.content.orphan.delete_all_orphans')
    def test_post_to_deleteorphan(self, mock_delete_all_orphans):
        """
        Tests deleting an orphan via DeleteOrphansAction
        """
        # Setup
        path = '/v2/content/actions/delete_orphans/'
        post_body = '[{"content_type_id": "rpm", "unit_id": "d692be5f-f585-4e6d-b816-0285ffecd847"}]'
        # Test
        status, body = self.post(path, post_body)
        # Verify
        self.assertEqual(202, status)
        mock_delete_all_orphans.assert_called_once()

    @mock.patch('pulp.server.managers.content.orphan.OrphanManager.delete_orphans_by_type')
    def test_delete_orphan_by_type(self, mock_delete_orphans_by_type):
        """
        Tests deleting orphans by type
        """
        # Setup
        path = '/v2/content/orphans/rpm/'
        # Test
        status, body = self.delete(path)
        # Verify
        self.assertEqual(202, status)
        mock_delete_orphans_by_type.assert_called_once()
