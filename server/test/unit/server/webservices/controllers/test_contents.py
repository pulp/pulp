"""
Test the pulp.server.webservices.controllers.contents module.
"""

from mock import patch, Mock

from .... import base


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
        self.assertNotEquals(body.get('spawned_tasks', None), None)


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
        self.assertNotEquals(body.get('spawned_tasks', None), None)

    @patch('pulp.server.content.sources.model.ContentSource.load_all')
    def test_post_create_bad_request(self, mock_load):
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
    def test_post_refresh_bad_request(self, mock_load):
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
