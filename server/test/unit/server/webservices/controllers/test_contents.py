"""
Test the pulp.server.webservices.controllers.contents module.
"""

from mock import patch, Mock

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

    @patch('pulp.server.managers.content.orphan.delete_all_orphans')
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

    @patch('pulp.server.managers.content.orphan.OrphanManager.delete_orphans_by_type')
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


class CatalogTests(base.PulpWebserviceTests):

    @patch('pulp.server.managers.content.catalog.ContentCatalogManager.purge')
    def test_delete(self, mock_purge):
        source_id = 'test-source'
        mock_purge.return_value = 10

        # test
        url = '/v2/content/catalog/%s/' % source_id
        status, body = self.delete(url)

        # validation
        self.assertEqual(status, 200)
        self.assertEqual(body, {'deleted': 10})
        mock_purge.assert_called_with(source_id)


class ContentSourcesTests(base.PulpWebserviceTests):

    @patch('pulp.server.content.sources.model.ContentSource.load_all')
    def test_get(self, mock_load):
        sources = {
            'A': Mock(id='A', dict=Mock(return_value={'A': 1})),
            'B': Mock(id='B', dict=Mock(return_value={'B': 2})),
            'C': Mock(id='C', dict=Mock(return_value={'C': 3})),
        }

        mock_load.return_value = sources

        # test
        url = '/v2/content/sources/'
        status, body = self.get(url)

        # validation
        mock_load.assert_called_with(None)
        self.assertEqual(status, 200)
        self.assertEqual(body, [s.dict() for s in sources.values()])

    @patch('pulp.server.content.sources.model.ContentSource.load_all')
    def test_post(self, mock_load):
        sources = {
            'A': Mock(id='A', dict=Mock(return_value={'A': 1})),
            'B': Mock(id='B', dict=Mock(return_value={'B': 2})),
            'C': Mock(id='C', dict=Mock(return_value={'C': 3})),
        }

        mock_load.return_value = sources

        # test 202
        url = '/v2/content/sources/action/refresh/'

        status, body = self.post(url)
        # validation
        self.assertEqual(status, 202)
        self.assertIsNotNone(body.get('spawned_tasks', None))


class ContentSourceResourceTests(base.PulpWebserviceTests):

    @patch('pulp.server.content.sources.model.ContentSource.load_all')
    def test_get(self, mock_load):
        sources = {
            'A': Mock(id='A', dict=Mock(return_value={'A': 1})),
            'B': Mock(id='B', dict=Mock(return_value={'B': 2})),
            'C': Mock(id='C', dict=Mock(return_value={'C': 3})),
        }

        mock_load.return_value = sources

        # test 200
        url = '/v2/content/sources/B/'
        status, body = self.get(url)

        # validation
        mock_load.assert_called_with(None)
        self.assertEqual(status, 200)
        self.assertEqual(body, {'B': 2})

        # test 404
        url = '/v2/content/sources/Z/'
        status, body = self.get(url)

        # validation
        self.assertEqual(status, 404)

    @patch('pulp.server.content.sources.model.ContentSource.load_all')
    def test_post(self, mock_load):
        sources = {
            'A': Mock(id='A', dict=Mock(return_value={'A': 1})),
            'B': Mock(id='B', dict=Mock(return_value={'B': 2})),
            'C': Mock(id='C', dict=Mock(return_value={'C': 3})),
        }

        mock_load.return_value = sources

        # test 200
        url = '/v2/content/sources/B/action/refresh/'
        status, body = self.post(url)

        # validation
        self.assertEqual(status, 202)
        self.assertIsNotNone(body.get('spawned_tasks', None))

    @patch('pulp.server.content.sources.model.ContentSource.load_all')
    def test_post_bad_request(self, mock_load):
        sources = {
            'A': Mock(id='A', dict=Mock(return_value={'A': 1})),
            'B': Mock(id='B', dict=Mock(return_value={'B': 2})),
            'C': Mock(id='C', dict=Mock(return_value={'C': 3})),
        }

        mock_load.return_value = sources

        # test 400
        url = '/v2/content/sources/B/action/create/'
        status, body = self.post(url)

        # validation
        self.assertEqual(status, 400)

    @patch('pulp.server.content.sources.model.ContentSource.load_all')
    def test_post_bad_request(self, mock_load):
        sources = {
            'A': Mock(id='A', dict=Mock(return_value={'A': 1})),
            'B': Mock(id='B', dict=Mock(return_value={'B': 2})),
            'C': Mock(id='C', dict=Mock(return_value={'C': 3})),
        }

        mock_load.return_value = sources

        # test 404
        url = '/v2/content/sources/Z/action/refresh/'
        status, body = self.post(url)

        # validation
        self.assertEqual(status, 404)
