import unittest

import mock

from pulp.bindings.repository import (RepositoryActionsAPI, RepositorySearchAPI,
                                      RepositoryUnitAPI, RepositoryAPI,
                                      RepositoryDistributorAPI, RepositoryHistoryAPI)
from pulp.bindings.server import PulpConnection
from pulp.common import constants


class TestRepoSearchAPI(unittest.TestCase):
    def test_path_defined(self):
        api = RepositorySearchAPI(mock.MagicMock())
        self.assertTrue(api.PATH is not None)
        self.assertTrue(len(api.PATH) > 0)


class TestRepoUnitSearchAPI(unittest.TestCase):
    def setUp(self):
        self.api = RepositoryUnitAPI(mock.MagicMock())

    @property
    def query(self):
        return self.api.server.POST.call_args[0][1]['criteria']

    def test_path(self):
        self.api.search('repo1', type_ids=['rpm'])
        path = self.api.server.POST.call_args[0][0]
        self.assertEqual(path, 'v2/repositories/repo1/search/units/')

    def test_sort(self):
        self.api.search('repo1', type_ids=['rpm'], sort=['id'])
        self.assertEqual(self.query['sort'], {'unit': ['id']})

    def test_fields(self):
        self.api.search('repo1', type_ids=['rpm'], fields=['name'])
        self.assertEqual(self.query['fields'], {'unit': ['name']})

    def test_limit(self):
        self.api.search('repo1', type_ids=['rpm'], limit=20)
        self.assertEqual(self.query['limit'], 20)

    def test_skip(self):
        self.api.search('repo1', type_ids=['rpm'], skip=20)
        self.assertEqual(self.query['skip'], 20)

    def test_unit_filters(self):
        self.api.search('repo1', type_ids=['rpm'], lte=[('count', 5)])
        self.assertEqual(self.query['filters'],
                         {'unit': {'count': {'$lte': 5}}})

    def test_after(self):
        self.api.search('repo1', type_ids=['rpm'], after='2012-03-15')
        self.assertEqual(self.query['filters']['association'],
                         {'created': {'$gte': '2012-03-15'}})

    def test_before(self):
        self.api.search('repo1', type_ids=['rpm'], before='2012-03-15')
        self.assertEqual(self.query['filters']['association'],
                         {'created': {'$lte': '2012-03-15'}})


class TestRepoUnitCopyAPI(unittest.TestCase):
    def setUp(self):
        self.api = RepositoryUnitAPI(mock.MagicMock())

    @property
    def query(self):
        return self.api.server.POST.call_args[0][1]['criteria']

    def test_path(self):
        self.api.copy('repo1', 'repo2', type_ids=['rpm'])
        path = self.api.server.POST.call_args[0][0]
        self.assertEqual(path, 'v2/repositories/repo2/actions/associate/')

    def test_after(self):
        self.api.copy('repo1', 'repo2', type_ids=['rpm'], after='2012-03-15')
        self.assertEqual(self.query['filters']['association'],
                         {'created': {'$gte': '2012-03-15'}})

    def test_before(self):
        self.api.copy('repo1', 'repo2', type_ids=['rpm'], before='2012-03-15')
        self.assertEqual(self.query['filters']['association'],
                         {'created': {'$lte': '2012-03-15'}})

    def test_unit_filters(self):
        self.api.copy('repo1', 'repo2', type_ids=['rpm'], lte=[('count', 5)])
        self.assertEqual(self.query['filters'],
                         {'unit': {'count': {'$lte': 5}}})

    def test_unit_fields(self):
        self.api.copy('repo1', 'repo2', type_ids=['rpm'], fields=['a', 'b'])
        self.assertEqual(self.query['fields'], {'unit': ['a', 'b']})

    def test_source_repo_id(self):
        self.api.copy('repo1', 'repo2', type_ids=['rpm'])
        self.assertEqual(self.api.server.POST.call_args[0][1].get('source_repo_id', None), 'repo1')


class TestRepositoryActionsAPI(unittest.TestCase):
    """Tests for the binding to the 'v2/repositories/<repo-id>/actions/sync/' API."""

    def setUp(self):
        self.pulp_connection = mock.MagicMock(spec=PulpConnection)
        self.actions_api = RepositoryActionsAPI(self.pulp_connection)
        self.repo_id = 'mock_repo'
        self.override_config = {'key': 'value'}

    def test_sync(self):
        """Assert the sync API path is called."""
        self.response = self.actions_api.sync(self.repo_id, self.override_config)
        self.pulp_connection.POST.assert_called_once_with(
            '/v2/repositories/mock_repo/actions/sync/',
            {'override_config': self.override_config}
        )

    def test_publish(self):
        """Assert the publish API path is called."""
        self.response = self.actions_api.publish(
            self.repo_id,
            'mock_distributor',
            self.override_config
        )
        self.override_config['id'] = 'mock_distributor'
        body = {'id': 'mock_distributor', 'override_config': self.override_config}
        self.pulp_connection.POST.assert_called_once_with(
            '/v2/repositories/mock_repo/actions/publish/',
            body
        )

    def test_associate(self):
        """Assert the associate API path is called."""
        self.response = self.actions_api.associate(self.repo_id, 'other_repo')
        self.pulp_connection.POST.assert_called_once_with(
            '/v2/repositories/mock_repo/actions/associate/',
            {'source_repo_id': 'other_repo'}
        )

    def test_download(self):
        """Assert the download API path is called and the default parameters are correct."""
        self.response = self.actions_api.download(self.repo_id)
        self.pulp_connection.POST.assert_called_once_with(
            '/v2/repositories/mock_repo/actions/download/',
            {'verify_all_units': False}
        )

    def test_download_verify(self):
        """Assert the download API path is called and the default parameters are correct."""
        self.response = self.actions_api.download(self.repo_id, verify_all_units=True)
        self.pulp_connection.POST.assert_called_once_with(
            '/v2/repositories/mock_repo/actions/download/',
            {'verify_all_units': True}
        )


class TestRepositoryDistributorAPI(unittest.TestCase):
    """
    Tests for the RepositoryDistributorAPI.
    """
    def setUp(self):
        self.api = RepositoryDistributorAPI(mock.MagicMock(spec=PulpConnection))

    def test_update(self):
        # Setup
        expected_path = self.api.base_path % 'test-repo' + 'test-distributor/'
        expected_body = {'distributor_config': {'key': 'value'}, 'delta': {'auto_publish': True}}

        # Test
        result = self.api.update('test-repo', 'test-distributor', {'key': 'value'},
                                 {'auto_publish': True})
        self.api.server.PUT.assert_called_once_with(expected_path, expected_body)
        self.assertEqual(result, self.api.server.PUT.return_value)


class TestRepositoryHistoryAPI(unittest.TestCase):
    """
    Tests for the RepositoryHistoryAPI binding. Tests that the query is constructed correctly and
    the correct path is used
    """
    def setUp(self):
        self.api = RepositoryHistoryAPI(mock.MagicMock(spec=PulpConnection))

    def test_sync_history_no_queries(self):
        """
        Test sync_history without using any queries
        """
        # Setup
        expected_path = self.api.base_path % 'test_repo' + '/sync/'
        expected_query = {}

        # Test
        result = self.api.sync_history('test_repo')
        self.api.server.GET.assert_called_once_with(expected_path, expected_query)
        self.assertEqual(result, self.api.server.GET.return_value)

    def test_sync_history_queries(self):
        """
        Test sync_history using all the available queries
        """
        # Setup
        expected_path = self.api.base_path % 'test_repo' + '/sync/'
        expected_query = {
            constants.REPO_HISTORY_FILTER_LIMIT: 3,
            constants.REPO_HISTORY_FILTER_SORT: 'ascending',
            constants.REPO_HISTORY_FILTER_START_DATE: '2013-01-01T00:00:00Z',
            constants.REPO_HISTORY_FILTER_END_DATE: '2013-01-01T00:00:00Z'
        }

        # Test
        result = self.api.sync_history(
            'test_repo', limit=3, sort='ascending', start_date='2013-01-01T00:00:00Z',
            end_date='2013-01-01T00:00:00Z')
        self.api.server.GET.assert_called_once_with(expected_path, expected_query)
        self.assertEqual(result, self.api.server.GET.return_value)

    def test_publish_history_no_queries(self):
        """
        Test publish_history without using any queries
        """
        # Setup
        expected_path = self.api.base_path % 'test_repo' + '/publish/test_distributor/'
        expected_query = {}

        # Test
        result = self.api.publish_history('test_repo', 'test_distributor')
        self.api.server.GET.assert_called_once_with(expected_path, expected_query)
        self.assertEqual(result, self.api.server.GET.return_value)

    def test_publish_history_queries(self):
        """
        Test publish_history using all the available queries
        """
        # Setup
        expected_path = self.api.base_path % 'test_repo' + '/publish/test_distributor/'
        expected_query = {
            constants.REPO_HISTORY_FILTER_LIMIT: 3,
            constants.REPO_HISTORY_FILTER_SORT: 'ascending',
            constants.REPO_HISTORY_FILTER_START_DATE: '2013-01-01T00:00:00Z',
            constants.REPO_HISTORY_FILTER_END_DATE: '2013-01-01T00:00:00Z'
        }

        # Test
        result = self.api.publish_history(
            'test_repo', 'test_distributor', limit=3, sort='ascending',
            start_date='2013-01-01T00:00:00Z', end_date='2013-01-01T00:00:00Z')
        self.api.server.GET.assert_called_once_with(expected_path, expected_query)
        self.assertEqual(result, self.api.server.GET.return_value)


class TestRepositoryUpdateAPI(unittest.TestCase):

    def setUp(self):
        self.api = RepositoryAPI(mock.MagicMock(spec=PulpConnection))
        self.expected_path = self.api.base_path + "foo/"
        self.repo_id = 'foo'

    def test_repo_only(self):

        self.api.update(self.repo_id, {'baz': 'qux'})
        expected_body = {'delta': {'baz': 'qux'}}
        self.api.server.PUT.assert_called_once_with(self.expected_path, expected_body)

    def test_distributors(self):
        self.api.update(self.repo_id, {}, distributor_configs={'foo': {'bar': 'baz'}})
        expected_body = {'delta': {}, 'distributor_configs': {'foo': {'bar': 'baz'}}}
        self.api.server.PUT.assert_called_once_with(self.expected_path, expected_body)

    def test_importer(self):
        self.api.update(self.repo_id, {}, importer_config={'foo': 'bar'})
        expected_body = {'delta': {}, 'importer_config': {'foo': 'bar'}}
        self.api.server.PUT.assert_called_once_with(self.expected_path, expected_body)
