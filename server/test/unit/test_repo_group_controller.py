import mock

import base
from pulp.server.db.model import criteria


class RepoGroupSearchTests(base.PulpWebserviceTests):
    @mock.patch('pulp.server.webservices.controllers.search.SearchController.params')
    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_post(self, mock_query, mock_params):
        mock_params.return_value = {
            'criteria' : {}
        }
        ret = self.post('/v2/repo_groups/search/')
        self.assertEqual(ret[0], 200)
        self.assertEqual(mock_query.call_count, 1)
        query_arg = mock_query.call_args[0][0]
        self.assertTrue(isinstance(query_arg, criteria.Criteria))
        self.assertEqual(mock_params.call_count, 1)

    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_get(self, mock_query):
        ret = self.get('/v2/repo_groups/search/')
        self.assertEqual(ret[0], 200)
        self.assertEqual(mock_query.call_count, 1)
        query_arg = mock_query.call_args[0][0]
        self.assertTrue(isinstance(query_arg, criteria.Criteria))

    @mock.patch('pulp.server.webservices.controllers.search.SearchController.params')
    @mock.patch('pulp.server.webservices.serialization.link.search_safe_link_obj')
    @mock.patch('pulp.server.db.connection.PulpCollection.query',
                return_value=[{'id': 'rg1'}])
    def test_post_serialization(self, mock_query, mock_link, mock_params):
        mock_params.return_value = {
            'criteria' : {}
        }
        status, body = self.post('/v2/repo_groups/search/')
        self.assertEqual(status, 200)
        mock_link.assert_called_once_with('rg1')

    @mock.patch('pulp.server.webservices.serialization.link.search_safe_link_obj')
    @mock.patch('pulp.server.db.connection.PulpCollection.query',
                return_value=[{'id': 'rg1'}])
    def test_get_serialization(self, mock_query, mock_link):
        status, body = self.get('/v2/repo_groups/search/')
        self.assertEqual(status, 200)
        mock_link.assert_called_once_with('rg1')


class RepoGroupSearchAuthTests(base.PulpWebserviceTests):
    """
    For some reason, these tests aren't discovered while in the RepoGroupSearchTests class.
    """
    @mock.patch.object(base.PulpWebserviceTests, 'HEADERS', spec=dict)
    def test_search_get_auth(self, mock_headers):
        """
        Test that when proper authentication is missing, the server returns a 401 error when
        RepoGroupSearch.GET is called
        """
        call_status, call_body = self.get('/v2/repo_groups/search/')
        self.assertEqual(401, call_status)

    @mock.patch.object(base.PulpWebserviceTests, 'HEADERS', spec=dict)
    def test_search_post_auth(self, mock_headers):
        """
        Test that when proper authentication is missing, the server returns a 401 error when
        RepoGroupSearch.GET is called
        """
        call_status, call_body = self.post('/v2/repo_groups/search/')
        self.assertEqual(401, call_status)


