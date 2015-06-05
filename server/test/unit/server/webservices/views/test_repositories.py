from operator import itemgetter
import datetime
import unittest

import json
import mock

from base import (
    assert_auth_CREATE, assert_auth_DELETE, assert_auth_EXECUTE, assert_auth_READ,
    assert_auth_UPDATE
)
from pulp.common import constants, dateutils, error_codes
from pulp.server import exceptions as pulp_exceptions
from pulp.server.managers.repo import query as repo_query, distributor
from pulp.server.webservices.views import repositories, util, search
from pulp.server.webservices.views.repositories import(
    ContentApplicabilityRegenerationView, RepoAssociate, RepoDistributorResourceView,
    RepoDistributorsView, RepoDistributorsSearchView, RepoImportUpload, RepoImporterResourceView,
    RepoImportersView, RepoPublish, RepoPublishHistory, RepoPublishScheduleResourceView,
    RepoPublishSchedulesView, RepoResourceView, RepoSearch, RepoSync, RepoSyncHistory,
    RepoSyncScheduleResourceView, RepoSyncSchedulesView, RepoUnassociate, RepoUnitSearch, ReposView
)


class TestMergeRelatedObjects(unittest.TestCase):
    """
    Tests for merge related objects
    """

    def test__merge_related_objects(self):
        """
        Test that objects are included in the appropriate repositories.
        """

        mock_repos = [{'id': 'mock1'}, {'id': 'mock2'}]
        mock_importers = [{'repo_id': 'mock1', 'id': 'mock_importer1'},
                          {'repo_id': 'mock1', 'id': 'mock_importer2'},
                          {'repo_id': 'mock2', 'id': 'mock_importer2'}]

        mock_importer_manager = mock.MagicMock()
        mock_importer_manager.find_by_repo_list.return_value = mock_importers
        ret = repositories._merge_related_objects('importers', mock_importer_manager, mock_repos)

        self.assertTrue(len(ret) == 2)
        self.assertEqual(map(itemgetter('id'), ret), ['mock1', 'mock2'])
        mock1_expected_importers = [{'repo_id': 'mock1', 'id': 'mock_importer1',
                                     '_href': '/v2/repositories/mock1/importers/mock_importer1/'},
                                    {'repo_id': 'mock1', 'id': 'mock_importer2',
                                     '_href': '/v2/repositories/mock1/importers/mock_importer2/'}]
        mock2_expected_importers = [{'repo_id': 'mock2', 'id': 'mock_importer2',
                                     '_href': '/v2/repositories/mock2/importers/mock_importer2/'}]
        mock1_importers = ret[map(itemgetter('id'), ret).index('mock1')]['importers']
        mock2_importers = ret[map(itemgetter('id'), ret).index('mock2')]['importers']
        self.assertEqual(mock1_importers, mock1_expected_importers)
        self.assertEqual(mock2_importers, mock2_expected_importers)

    def test__merge_related_objects_distributors(self):
        """
        Test that objects are included in the appropriate for distributors
        """

        mock_repos = [{'id': 'mock1'}, {'id': 'mock2'}]
        mock_distributors = [{'repo_id': 'mock1', 'id': 'mock_distributor1'},
                             {'repo_id': 'mock1', 'id': 'mock_distributor2'},
                             {'repo_id': 'mock2', 'id': 'mock_distributor2'}]

        mock_distributor_manager = mock.MagicMock()
        mock_distributor_manager.find_by_repo_list.return_value = mock_distributors
        ret = repositories._merge_related_objects('distributors', mock_distributor_manager,
                                                  mock_repos)

        self.assertTrue(len(ret) == 2)
        self.assertEqual(map(itemgetter('id'), ret), ['mock1', 'mock2'])
        mock1_expected_distributors = [{'repo_id': 'mock1', 'id': 'mock_distributor1'},
                                       {'repo_id': 'mock1', 'id': 'mock_distributor2'}]
        mock2_expected_distributors = [{'repo_id': 'mock2', 'id': 'mock_distributor2'}]
        mock1_distributors = ret[map(itemgetter('id'), ret).index('mock1')]['distributors']
        mock2_distributors = ret[map(itemgetter('id'), ret).index('mock2')]['distributors']
        self.assertEqual(mock1_distributors, mock1_expected_distributors)
        self.assertEqual(mock2_distributors, mock2_expected_distributors)

    def test__merge_related_objects_no_objects(self):
        """
        Test that merge happens correctly when there are no objects to merge.
        """

        mock_repos = [{'id': 'mock1'}, {'id': 'mock2'}]

        mock_importer_manager = mock.MagicMock()
        mock_importer_manager.find_by_repo_list.return_value = []
        ret = repositories._merge_related_objects('importers', mock_importer_manager, mock_repos)

        self.assertTrue(len(ret) == 2)
        self.assertEqual(map(itemgetter('id'), ret), ['mock1', 'mock2'])
        mock1_importers = ret[map(itemgetter('id'), ret).index('mock1')]['importers']
        mock2_importers = ret[map(itemgetter('id'), ret).index('mock2')]['importers']
        self.assertEqual(mock1_importers, [])
        self.assertEqual(mock2_importers, [])


class TestConvertRepoDatesToStrings(unittest.TestCase):
    """
    Tests the standardization of dates in repo fields.
    """

    def test_last_unit_added_and_removed(self):
        """
        Test that last_unit_added and last_unit_removed fields contain properly formatted dates.
        """

        dt = datetime.datetime.utcnow()
        repo = {'id': 'dummy-1', 'display_name': 'dummy',
                'last_unit_added': dt,
                'last_unit_removed': dt}
        string_date = dateutils.format_iso8601_datetime(
            dateutils.to_utc_datetime(dt, no_tz_equals_local_tz=False))
        repositories._convert_repo_dates_to_strings(repo)
        self.assertEquals(repo['last_unit_added'], string_date)
        self.assertEquals(repo['last_unit_removed'], string_date)

    @mock.patch('pulp.server.webservices.views.repositories.dateutils.to_utc_datetime')
    @mock.patch('pulp.server.webservices.views.repositories.dateutils.format_iso8601_datetime')
    def test_no_last_added_or_removed(self, mock_to_utc, mock_8601):
        """
        When last_unit_added or last_unit_removed do not exist, they should be ignored.
        """

        repo = {'id': 'dummy-1', 'display_name': 'dummy',
                'last_unit_added': None,
                'last_unit_removed': None}
        repositories._convert_repo_dates_to_strings(repo)
        self.assertEquals(repo['last_unit_added'], None)
        self.assertEquals(repo['last_unit_removed'], None)
        self.assertFalse(mock_to_utc.called)
        self.assertFalse(mock_8601.called)


class TestReposView(unittest.TestCase):
    """
    Tests for ReposView.
    """

    @mock.patch('pulp.server.webservices.views.repositories._convert_repo_dates_to_strings')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    def test__process_repos_minimal(self, mock_rev, mock_convert_date):
        """
        Test _process_repos without optional args, assert that processing was called for each repo.
        """

        mock_repos = [{'id': 'mock1'}, {'id': 'mock2'}]
        repositories._process_repos(mock_repos, 'false', 'false', 'false')
        mock_rev.assert_has_calls(
            [mock.call('repo_resource', kwargs={'repo_id': 'mock1'}),
             mock.call('repo_resource', kwargs={'repo_id': 'mock2'})]
        )
        mock_convert_date.assert_has_calls(
            [mock.call({'id': 'mock1', '_href': mock_rev.return_value}),
             mock.call({'id': 'mock2', '_href': mock_rev.return_value})]
        )

    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    @mock.patch('pulp.server.webservices.views.repositories._merge_related_objects')
    @mock.patch('pulp.server.webservices.views.repositories._convert_repo_dates_to_strings')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    def test__process_repos_details(self, mock_rev, mock_convert_date, mock_merge,
                                    mock_factory):
        """
        Test that importer and distributor options cause the expected merges to happen.
        """

        mock_repos = [{'id': 'mock1'}, {'id': 'mock2'}]
        repositories._process_repos(mock_repos, 'true', 'false', 'false')
        mock_merge.assert_has_calls(
            [mock.call('importers', mock_factory.repo_importer_manager(), mock_repos),
             mock.call('distributors', mock_factory.repo_distributor_manager(), mock_repos)]
        )
        mock_rev.assert_has_calls(
            [mock.call('repo_resource', kwargs={'repo_id': 'mock1'}),
             mock.call('repo_resource', kwargs={'repo_id': 'mock2'})]
        )
        mock_convert_date.assert_has_calls(
            [mock.call({'id': 'mock1', '_href': mock_rev.return_value}),
             mock.call({'id': 'mock2', '_href': mock_rev.return_value})]
        )

    @mock.patch('pulp.server.webservices.views.repositories._convert_repo_dates_to_strings')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    def test__process_repos_scratchpad(self, mock_rev, mock_convert_date):
        """
        Test that scratchpad field has been removed.
        """

        mock_repos = [{'id': 'mock1', 'scratchpad': 'should be removed'}, {'id': 'mock2'}]
        repositories._process_repos(mock_repos, 'false', 'false', 'false')
        mock_rev.assert_has_calls(
            [mock.call('repo_resource', kwargs={'repo_id': 'mock1'}),
             mock.call('repo_resource', kwargs={'repo_id': 'mock2'})]
        )
        mock_convert_date.assert_has_calls(
            [mock.call({'id': 'mock1', '_href': mock_rev.return_value}),
             mock.call({'id': 'mock2', '_href': mock_rev.return_value})]
        )

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    @mock.patch('pulp.server.webservices.views.repositories.RepoModel.get_collection')
    def test_get_repos_no_options(self, mock_collection, mock_process, mock_resp):
        """
        Get repos without passing options.
        """

        mock_repos = [{'mock_repo_1': 'somedata'}, {'mock_repo_2': 'moredata'}]
        mock_collection.return_value.find.return_value = mock_repos
        mock_request = mock.MagicMock()
        mock_request.GET = {}
        repos_view = ReposView()

        response = repos_view.get(mock_request)
        mock_process.assert_called_once_with(mock_repos, 'false', 'false', 'false')
        mock_resp.assert_called_once_with(mock_collection().find.return_value)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    @mock.patch('pulp.server.webservices.views.repositories.RepoModel.get_collection')
    def test_get_repos_with_details(self, mock_collection, mock_process):
        """
        Get repos with the details shortcut.
        """

        mock_repos = [{'mock_repo_1': 'somedata'}, {'mock_repo_2': 'moredata'}]
        mock_collection.return_value.find.return_value = mock_repos
        mock_request = mock.MagicMock()
        mock_request.GET = {'details': 'true'}
        repos_view = ReposView()

        repos_view.get(mock_request)
        mock_process.assert_called_once_with(mock_repos, 'true', 'false', 'false')

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    @mock.patch('pulp.server.webservices.views.repositories.RepoModel.get_collection')
    def test_get_repos_with_false(self, mock_collection, mock_process):
        """
        Get repos with by passing an optional get parameter 'details=false'

        This test seem a little excessive, but this is in response to previous incorrect
        behavior. The string 'false' is actually truthy and was being used incorrectly.
        """

        mock_repos = [{'mock_repo_1': 'somedata'}, {'mock_repo_2': 'moredata'}]
        mock_collection.return_value.find.return_value = mock_repos
        mock_request = mock.MagicMock()
        mock_request.GET = {'details': 'false'}
        repos_view = ReposView()

        repos_view.get(mock_request)
        mock_process.assert_called_once_with(mock_repos, 'false', 'false', 'false')

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    @mock.patch('pulp.server.webservices.views.repositories.RepoModel.get_collection')
    def test_get_repos_with_uppercase_boolean(self, mock_collection, mock_process):
        """
        Get repos with invalid details get parameter, default to False
        """

        mock_repos = [{'mock_repo_1': 'somedata'}, {'mock_repo_2': 'moredata'}]
        mock_collection.return_value.find.return_value = mock_repos
        mock_request = mock.MagicMock()
        mock_request.GET = {'details': 'True'}
        repos_view = ReposView()

        repos_view.get(mock_request)
        mock_process.assert_called_once_with(mock_repos, 'True', 'false', 'false')

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    @mock.patch('pulp.server.webservices.views.repositories.RepoModel.get_collection')
    def test_get_repos_with_invalid_boolean(self, mock_collection, mock_process):
        """
        Get repos with invalid details get parameter, default to False
        """

        mock_repos = [{'mock_repo_1': 'somedata'}, {'mock_repo_2': 'moredata'}]
        mock_collection.return_value.find.return_value = mock_repos
        mock_request = mock.MagicMock()
        mock_request.GET = {'details': 'yes'}
        repos_view = ReposView()

        repos_view.get(mock_request)
        mock_process.assert_called_once_with(mock_repos, 'yes', 'false', 'false')

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    @mock.patch('pulp.server.webservices.views.repositories.RepoModel.get_collection')
    def test_get_repos_with_importers(self, mock_collection, mock_process):
        """
        Get repos with importer information.
        """

        mock_repos = [{'mock_repo_1': 'somedata'}, {'mock_repo_2': 'moredata'}]
        mock_collection.return_value.find.return_value = mock_repos
        mock_request = mock.MagicMock()
        mock_request.GET = {'importers': 'true'}
        repos_view = ReposView()

        repos_view.get(mock_request)
        mock_process.assert_called_once_with(mock_repos, 'false', 'true', 'false')

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    @mock.patch('pulp.server.webservices.views.repositories.RepoModel.get_collection')
    def test_get_repos_with_distributors(self, mock_collection, mock_process):
        """
        Get repos with distributor information.
        """

        mock_repos = [{'mock_repo_1': 'somedata'}, {'mock_repo_2': 'moredata'}]
        mock_collection.return_value.find.return_value = mock_repos
        mock_request = mock.MagicMock()
        mock_request.GET = {'distributors': 'true'}
        repos_view = ReposView()

        repos_view.get(mock_request)
        mock_process.assert_called_once_with(mock_repos, 'false', 'false', 'true')

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.generate_redirect_response')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_repos_only_id(self, mock_factory, mock_rev, mock_redir, mock_resp):
        """
        Create a repo using the minimal body.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'id': 'mock_repo'})
        mock_repo_manager = mock_factory.repo_manager.return_value
        mock_repo_manager.create_and_configure_repo.return_value = {'id': 'mock_repo'}

        repos_view = ReposView()
        response = repos_view.post(mock_request)

        expected_content = {'id': 'mock_repo', '_href': mock_rev.return_value}
        mock_rev.assert_called_once_with('repo_resource', kwargs={'repo_id': 'mock_repo'})
        mock_resp.assert_called_once_with(expected_content)
        mock_redir.assert_called_once_with(mock_resp.return_value, expected_content['_href'])
        self.assertTrue(response is mock_redir.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.generate_redirect_response')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_repos_all_fields(self, mock_factory, mock_rev, mock_redir, mock_resp):
        """
        Create a repo using all allowed fields.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({
            'id': 'mock_repo', 'display_name': 'mock_display', 'description': 'mock_desciption',
            'notes': 'mock_notes', 'importer_type_id': 'mock_importer', 'distributors': ['dist1']
        })
        mock_repo_manager = mock_factory.repo_manager.return_value
        mock_repo_manager.create_and_configure_repo.return_value = {
            'id': 'mock_repo', 'display_name': 'mock_display', 'description': 'mock_desciption',
            'notes': 'mock_notes', 'importer_type_id': 'mock_importer', 'distributors': ['dist1']
        }

        repos_view = ReposView()
        response = repos_view.post(mock_request)

        mock_rev.assert_called_once_with('repo_resource', kwargs={'repo_id': 'mock_repo'})
        mock_resp.assert_called_once_with({
            'id': 'mock_repo', 'display_name': 'mock_display', 'description': 'mock_desciption',
            'notes': 'mock_notes', 'importer_type_id': 'mock_importer', 'distributors': ['dist1'],
            '_href': mock_rev.return_value
        })
        mock_redir.assert_called_once_with(mock_resp.return_value, mock_rev.return_value)
        self.assertTrue(response is mock_redir.return_value)


class TestRepoResourceView(unittest.TestCase):
    """
    Tests for RepoResoureceView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory.repo_query_manager')
    def test_get_existing_repo(self, mock_rqm, mock_resp, mock_rev):
        """
        Retrieve an existing repository.
        """

        mock_rqm().find_by_id.return_value = {'mock_repo': 'somedata'}
        mock_request = mock.MagicMock()
        mock_request.GET = {}

        repos_resource = RepoResourceView()
        response = repos_resource.get(mock_request, 'mock_repo')

        expected_result = {'mock_repo': 'somedata', '_href': mock_rev.return_value}
        mock_rev.assert_called_once_with('repo_resource', kwargs={'repo_id': 'mock_repo'})
        mock_resp.assert_called_once_with(expected_result)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_nonexisting_repo(self, mock_factory):
        """
        Retrieve a nonexisting repository.
        """

        mock_q_manager = mock_factory.repo_query_manager.return_value
        mock_q_manager.find_by_id.return_value = None
        mock_request = mock.MagicMock()

        repos_resource = RepoResourceView()
        try:
            repos_resource.get(mock_request, 'mock_repo')
        except pulp_exceptions.MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised for a nonexisting repository")

        self.assertEqual(response.http_status_code, 404)
        self.assertTrue(response.error_code is error_codes.PLP0009)
        self.assertEqual(response.error_data['resources'], {'repo': 'mock_repo'})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._merge_related_objects')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_existing_repo_with_details(self, mock_factory, mock_merge, mock_resp, mock_rev):
        """
        Retrieve an existing repository with details.
        """

        mock_q_manager = mock_factory.repo_query_manager.return_value
        mock_q_manager.find_by_id.return_value = {'mock_repo': 'somedata'}
        mock_request = mock.MagicMock()
        mock_request.GET = {'details': 'true'}
        mock_merge.side_effect = lambda x, y, z: z
        mock_rev.return_value = mock_rev.return_value

        repos_resource = RepoResourceView()
        response = repos_resource.get(mock_request, 'mock_repo')

        mock_rev.assert_called_once_with('repo_resource', kwargs={'repo_id': 'mock_repo'})
        mock_resp.assert_called_once_with({'mock_repo': 'somedata', '_href': mock_rev.return_value})
        self.assertTrue(response is mock_resp.return_value)
        self.assertEqual(mock_merge.call_count, 2)
        mock_merge.assert_has_calls([
            mock.call('importers', mock_factory.repo_importer_manager(),
                      ({'mock_repo': 'somedata', '_href': mock_rev.return_value},)),
            mock.call('distributors', mock_factory.repo_distributor_manager(),
                      ({'mock_repo': 'somedata', '_href': mock_rev.return_value},))
        ])

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._merge_related_objects')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_existing_repo_with_details_false(self, mock_factory, mock_merge, mock_resp):
        """
        Retrieve an existing repository with details set to false.
        """

        mock_repo = {'mock_repo': 'somedata'}
        mock_q_manager = mock_factory.repo_query_manager.return_value
        mock_q_manager.find_by_id.return_value = mock_repo
        mock_request = mock.MagicMock()
        mock_request.GET = {'details': 'false'}
        mock_merge.side_effect = lambda x, y, z: z

        repos_resource = RepoResourceView()
        response = repos_resource.get(mock_request, 'mock_repo')

        mock_resp.assert_called_once_with(mock_repo)
        self.assertTrue(response is mock_resp.return_value)
        self.assertEqual(mock_merge.call_count, 0)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._merge_related_objects')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_existing_repo_with_importers(self, mock_factory, mock_merge, mock_resp):
        """
        Retrieve an existing repository with importers.
        """

        mock_repo = {'mock_repo': 'somedata'}
        mock_q_manager = mock_factory.repo_query_manager.return_value
        mock_q_manager.find_by_id.return_value = mock_repo
        mock_request = mock.MagicMock()
        mock_request.GET = {'importers': 'true'}
        mock_merge.side_effect = lambda x, y, z: z

        repos_resource = RepoResourceView()
        response = repos_resource.get(mock_request, 'mock_repo')

        mock_resp.assert_called_once_with(mock_repo)
        self.assertTrue(response is mock_resp.return_value)
        mock_merge.assert_called_once_with('importers', mock_factory.repo_importer_manager(),
                                           (mock_repo,))

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._merge_related_objects')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_existing_repo_with_distributors(self, mock_factory, mock_merge, mock_resp):
        """
        Retrieve an existing repository with distributors.
        """

        mock_repo = {'mock_repo': 'somedata'}
        mock_q_manager = mock_factory.repo_query_manager.return_value
        mock_q_manager.find_by_id.return_value = mock_repo
        mock_request = mock.MagicMock()
        mock_request.GET = {'distributors': 'true'}
        mock_merge.side_effect = lambda x, y, z: z

        repos_resource = RepoResourceView()
        response = repos_resource.get(mock_request, 'mock_repo')

        mock_resp.assert_called_once_with(mock_repo)
        self.assertTrue(response is mock_resp.return_value)
        mock_merge.assert_called_once_with('distributors', mock_factory.repo_distributor_manager(),
                                           (mock_repo,))

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.repositories.tags')
    @mock.patch('pulp.server.webservices.views.repositories.repo_tasks.delete')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_delete_existing_repo(self, mock_factory, mock_delete, mock_tags):
        """
        Dispatch a delete task to remove an existing repository.
        """

        mock_request = mock.MagicMock()
        repos_resource = RepoResourceView()
        try:
            repos_resource.delete(mock_request, 'mock_repo')
        except pulp_exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raised for asynchronous delete.')

        mock_task_tags = [mock_tags.resource_tag.return_value, mock_tags.action_tag.return_value]

        self.assertEqual(response.http_status_code, 202)
        mock_delete.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE, 'mock_repo', ['mock_repo'], tags=mock_task_tags
        )

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._convert_repo_dates_to_strings')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_put_existing_repo_no_delta(self, mock_factory, mock_rev, mock_date, mock_resp):
        """
        Test update without any data.
        """

        mock_repo = {'mock_repo': 'somedata'}
        mock_manager = mock_factory.repo_manager.return_value
        mock_task_result = mock_manager.update_repo_and_plugins.return_value
        mock_task_result.spawned_tasks = False
        mock_task_result.serialize.return_value = mock_repo

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({})

        repos_resource = RepoResourceView()
        response = repos_resource.put(mock_request, 'mock_repo')

        mock_rev.assert_called_once_with('repo_resource', kwargs={'repo_id': 'mock_repo'})
        mock_manager.update_repo_and_plugins.assert_called_once_with('mock_repo', None, None, None)
        mock_repo.update(_href=mock_rev.return_value)
        mock_resp.assert_called_once_with(mock_repo)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._convert_repo_dates_to_strings')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_put_existing_repo_with_delta(self, mock_factory, mock_rev, mock_date, mock_resp):
        """
        Test update with delta data.
        """

        mock_repo = {'mock_repo': 'somedata'}
        mock_manager = mock_factory.repo_manager.return_value
        mock_task_result = mock_manager.update_repo_and_plugins.return_value
        mock_task_result.spawned_tasks = False
        mock_task_result.serialize.return_value = mock_repo

        mock_request = mock.MagicMock()
        mock_data = {'delta': {'description': 'test'}}
        mock_request.body = json.dumps(mock_data)

        repos_resource = RepoResourceView()
        response = repos_resource.put(mock_request, 'mock_repo')

        mock_rev.assert_called_once_with('repo_resource', kwargs={'repo_id': 'mock_repo'})
        mock_repo.update(_href=mock_rev.return_value)
        mock_manager.update_repo_and_plugins.assert_called_once_with(
            'mock_repo', mock_data['delta'], None, None)
        mock_resp.assert_called_once_with(mock_repo)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._convert_repo_dates_to_strings')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_put_existing_repo_with_importer(self, mock_factory, mock_rev, mock_date, mock_resp):
        """
        Test update with importer config update.
        """

        mock_manager = mock_factory.repo_manager.return_value
        mock_task_result = mock_manager.update_repo_and_plugins.return_value
        mock_task_result.spawned_tasks = False
        mock_task_result.serialize.return_value = {'mock': 'repo'}

        mock_request = mock.MagicMock()
        mock_data = {'importer_config': 'importer_data'}
        mock_request.body = json.dumps(mock_data)

        repos_resource = RepoResourceView()
        response = repos_resource.put(mock_request, 'mock_repo')

        mock_rev.assert_called_once_with('repo_resource', kwargs={'repo_id': 'mock_repo'})
        mock_resp.assert_called_once_with({'mock': 'repo'})
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories._convert_repo_dates_to_strings')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_put_existing_repo_with_distributor(self, mock_factory, mock_date):
        """
        Test update with importer config update.
        """

        mock_manager = mock_factory.repo_manager.return_value
        mock_task_result = mock_manager.update_repo_and_plugins.return_value
        mock_task_result.spawned_tasks = 'distributor'

        mock_request = mock.MagicMock()
        mock_data = {'distributor_configs': 'distributor_data'}
        mock_request.body = json.dumps(mock_data)

        repos_resource = RepoResourceView()

        self.assertRaises(pulp_exceptions.OperationPostponed, repos_resource.put,
                          mock_request, 'mock_repo')
        mock_manager.update_repo_and_plugins.assert_called_once_with(
            'mock_repo', None, None, 'distributor_data'
        )


class TestRepoSearch(unittest.TestCase):
    """
    Tests for RepoSearch.
    """

    def test_class_attributes(self):
        """
        Ensure that class attributes are set correctly.
        """
        repo_search = RepoSearch()
        self.assertTrue(isinstance(repo_search.manager, repo_query.RepoQueryManager))
        self.assertEqual(repo_search.optional_fields, ['details', 'importers', 'distributors'])
        self.assertEqual(repo_search.response_builder,
                         util.generate_json_response_with_pulp_encoder)

    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    def test_get_results(self, mock_process):
        """
        Test that optional arguments and the data are properly passed to _process_repos.
        """
        mock_search = mock.MagicMock(return_value=[])
        mock_query = mock.MagicMock()
        options = {'details': 'mock_deets', 'importers': 'mock_imp', 'distributors': 'mock_dist'}
        repo_search = RepoSearch()
        content = repo_search.get_results(mock_query, mock_search, options)
        self.assertEqual(content, mock_process.return_value)
        mock_process.assert_called_once_with([], 'mock_deets', 'mock_imp', 'mock_dist')


class TestRepoUnitSearch(unittest.TestCase):
    """
    Tests for RepoUnitSearch.
    """

    @mock.patch('pulp.server.webservices.views.repositories.manager_factory.repo_query_manager')
    def test__generate_response_missing_repo(self, mock_rqm):
        """
        Assert that MissingResource is raised if the provided repo does not exist.
        """
        mock_rqm().find_by_id.return_value = None
        repo_unit_search = RepoUnitSearch()
        self.assertRaises(pulp_exceptions.MissingResource, repo_unit_search._generate_response,
                          "", "", {}, type_id='fake_repo')

    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory.'
                'repo_unit_association_query_manager')
    @mock.patch('pulp.server.webservices.views.repositories.UnitAssociationCriteria')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory.repo_query_manager')
    def test__generate_response_one_type(self, mock_rqm, mock_crit, mock_uqm, mock_resp):
        """
        Test that responses are created using `get_units_by_type` if there is only one type.
        """
        mock_rqm().find_by_id.return_value = 'exists'
        criteria = mock_crit.from_client_input.return_value
        criteria.type_ids = ['one_type']
        repo_unit_search = RepoUnitSearch()
        repo_unit_search._generate_response('mock_q', {}, repo_id='mock_repo')
        mock_crit.from_client_input.assert_called_once_with('mock_q')
        mock_uqm().get_units_by_type.assert_called_once_with('mock_repo', 'one_type',
                                                             criteria=criteria)
        mock_resp.assert_called_once_with(mock_uqm().get_units_by_type.return_value)

    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory.'
                'repo_unit_association_query_manager')
    @mock.patch('pulp.server.webservices.views.repositories.UnitAssociationCriteria')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory.repo_query_manager')
    def test__generate_response_multiple_types(self, mock_rqm, mock_crit, mock_uqm, mock_resp):
        """
        Test that responses are created using `get_units_across_types` if there are multiple types.
        """
        mock_rqm().find_by_id.return_value = 'exists'
        criteria = mock_crit.from_client_input.return_value
        criteria.type_ids = ['one_type', 'two_types']
        repo_unit_search = RepoUnitSearch()
        repo_unit_search._generate_response('mock_q', {}, repo_id='mock_repo')
        mock_crit.from_client_input.assert_called_once_with('mock_q')
        mock_uqm().get_units_across_types.assert_called_once_with('mock_repo', criteria=criteria)
        mock_resp.assert_called_once_with(mock_uqm().get_units_across_types.return_value)


class TestRepoImportersView(unittest.TestCase):
    """
    Tests for RepoImportersView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_importers(self, mock_factory, mock_resp):
        """
        Get importers for a repository.
        """

        mock_request = mock.MagicMock()
        mock_importer = [{"id": "importer", 'repo_id': 'mock_repo'}]
        mock_factory.repo_importer_manager.return_value.get_importers.return_value = mock_importer
        repo_importers = RepoImportersView()
        response = repo_importers.get(mock_request, 'mock_repo')
        expected_response = [{'repo_id': 'mock_repo', 'id': 'importer',
                              '_href': '/v2/repositories/mock_repo/importers/importer/'}]
        mock_resp.assert_called_once_with(expected_response)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.repositories.repo_importer_manager')
    @mock.patch('pulp.server.webservices.views.repositories.tags')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_importers(self, mock_factory, mock_tags, mock_importer_manager):
        """
        Associate an importer to a repository.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'importer_type_id': 'mock_type', 'importer_config': 'conf'})
        repo_importers = RepoImportersView()

        try:
            repo_importers.post(mock_request, 'mock_repo')
        except pulp_exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError("Associate importer call should raise OperationPostponed")

        mock_task_tags = [mock_tags.resource_tag(), mock_tags.action_tag()]
        self.assertEqual(response.http_status_code, 202)
        mock_importer_manager.set_importer.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE, 'mock_repo', ['mock_repo', 'mock_type'],
            {'repo_plugin_config': 'conf'}, tags=mock_task_tags
        )


class TestRepoImporterResourceView(unittest.TestCase):
    """
    Tests for RepoImporterResourceView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_importer(self, mock_factory, mock_resp):
        """
        Get an importer for a repository.
        """

        mock_request = mock.MagicMock()
        mock_importer = {"id": "mock_importer", 'repo_id': 'mock-repo'}
        mock_factory.repo_importer_manager.return_value.get_importer.return_value = mock_importer

        repo_importer = RepoImporterResourceView()
        response = repo_importer.get(mock_request, 'mock_repo', 'mock_importer')

        expected_response = {'repo_id': 'mock-repo', 'id': 'mock_importer',
                             '_href': '/v2/repositories/mock-repo/importers/mock_importer/'}
        mock_resp.assert_called_once_with(expected_response)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_nonexisting_importer(self, mock_factory):
        """
        Try to get an importer that doesn't exist.
        """

        mock_request = mock.MagicMock()
        mock_importer = {"id": "mock_importer"}
        mock_factory.repo_importer_manager.return_value.get_importer.return_value = mock_importer

        repo_importer = RepoImporterResourceView()
        try:
            repo_importer.get(mock_request, 'mock_repo', 'do_not_find_this')
        except pulp_exceptions.MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised if importer does not exist")

        self.assertEqual(response.http_status_code, 404)
        self.assertTrue(response.error_code is error_codes.PLP0009)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.repositories.repo_importer_manager.remove_importer')
    @mock.patch('pulp.server.webservices.views.repositories.tags')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_delete_importer(self, mock_factory, mock_tags, mock_remove_importer):
        """
        Diassociate an importer from a repository.
        """

        mock_request = mock.MagicMock()
        mock_importer = {"id": "mock_importer"}
        mock_factory.repo_importer_manager.return_value.get_importer.return_value = mock_importer
        mock_task = [mock_tags.resource_tag(), mock_tags.resource_tag(), mock_tags.action_tag()]

        repo_importer = RepoImporterResourceView()
        try:
            repo_importer.delete(mock_request, 'mock_repo', 'mock_importer')
        except pulp_exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError("OperationPostponed should be raised for delete task")

        self.assertEqual(response.http_status_code, 202)
        mock_remove_importer.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE, 'mock_repo', ['mock_repo'], tags=mock_task
        )

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_delete_nonexisting_importer(self, mock_factory):
        """
        Attpempt diassociate an importer that is not associated to a repository.
        """

        mock_request = mock.MagicMock()
        mock_importer = {"id": "mock_importer"}
        mock_factory.repo_importer_manager.return_value.get_importer.return_value = mock_importer

        repo_importer = RepoImporterResourceView()
        try:
            repo_importer.delete(mock_request, 'mock_repo', 'not_mock_importer')
        except pulp_exceptions.MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised if importer is not associated "
                                 "with the repo.")

        self.assertEqual(response.http_status_code, 404)
        self.assertTrue(response.error_code is error_codes.PLP0009)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch(
        'pulp.server.webservices.views.repositories.repo_importer_manager.update_importer_config')
    @mock.patch('pulp.server.webservices.views.repositories.tags')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_put_update_importer(self, mock_factory, mock_tags, mock_update_importer):
        """
        Update an importer with all required params.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'importer_config': 'test'})
        mock_importer = {"id": "mock_importer"}
        mock_factory.repo_importer_manager.return_value.get_importer.return_value = mock_importer
        mock_task = [mock_tags.resource_tag(), mock_tags.resource_tag(), mock_tags.action_tag()]

        repo_importer = RepoImporterResourceView()
        try:
            repo_importer.put(mock_request, 'mock_repo', 'mock_importer')
        except pulp_exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError("OperationPostponed should be raised for update importer task")

        self.assertEqual(response.http_status_code, 202)
        mock_update_importer.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE, 'mock_repo', ['mock_repo'],
            {'importer_config': 'test'}, tags=mock_task
        )

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_put_bad_importer_id(self, mock_factory):
        """
        Update an importer with invalid importer_id.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'importer_config': 'test'})
        mock_importer = {"id": "mock_importer"}
        mock_factory.repo_importer_manager.return_value.get_importer.return_value = mock_importer

        repo_importer = RepoImporterResourceView()
        try:
            repo_importer.put(mock_request, 'mock_repo', 'not_mock_importer')
        except pulp_exceptions.MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised if the importer for a repo "
                                 "is not the same as the importer_id passed in")

        self.assertEqual(response.http_status_code, 404)
        self.assertTrue(response.error_code is error_codes.PLP0009)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_put_no_importer_conf(self, mock_factory):
        """
        Update an importer with the importer config missing from the request body.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'not_importer_config': 'will fail'})
        mock_importer = {"id": "mock_importer"}
        mock_factory.repo_importer_manager.return_value.get_importer.return_value = mock_importer

        repo_importer = RepoImporterResourceView()
        try:
            repo_importer.put(mock_request, 'mock_repo', 'mock_importer')
        except pulp_exceptions.MissingValue, response:
            pass
        else:
            raise AssertionError("MissingValue should be raised if importer config is not passed")

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0016)


class TestRepoSyncSchedulesView(unittest.TestCase):
    """
    Tests for RepoSyncSchedulesView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories.generate_json_response')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_all_scheduled_syncs(self, mock_factory, mock_rev, mock_resp):
        """
        Get a list of scheduled syncs.
        """

        mock_request = mock.MagicMock()
        mock_schedule = mock.MagicMock()
        mock_schedule.for_display.return_value = {'_id': 'mock_schedule'}
        mock_factory.repo_sync_schedule_manager.return_value.list.return_value = [mock_schedule]

        sync_schedule = RepoSyncSchedulesView()
        response = sync_schedule.get(mock_request, 'mock_repo', 'mock_importer')

        mock_rev.assert_called_once_with('repo_sync_schedule_resource', kwargs={
            'importer_id': 'mock_importer', 'schedule_id': 'mock_schedule', 'repo_id': 'mock_repo'}
        )
        mock_resp.assert_called_once_with([{'_id': 'mock_schedule',
                                            '_href': mock_rev.return_value}])
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.repositories.generate_json_response')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_new_scheduled_sync_minimal(self, mock_factory, mock_rev, mock_resp):
        """
        Create a new scheduled sync with minimal data.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'schedule': 'some iso8601'})
        mock_schedule = mock.MagicMock()
        mock_schedule.for_display.return_value = {'_id': 'mock_schedule'}
        mock_factory.repo_sync_schedule_manager.return_value.create.return_value = mock_schedule

        sync_schedule = RepoSyncSchedulesView()
        response = sync_schedule.post(mock_request, 'mock_repo', 'mock_importer')
        mock_rev.assert_called_once_with('repo_sync_schedule_resource', kwargs={
            'importer_id': 'mock_importer', 'schedule_id': mock_schedule['_id'],
            'repo_id': 'mock_repo'
        })
        mock_factory.repo_sync_schedule_manager.return_value.create.assert_called_once_with(
            'mock_repo', 'mock_importer', {'override_config': {}}, 'some iso8601', None, True
        )
        mock_resp.assert_called_once_with({'_id': 'mock_schedule', '_href': mock_rev.return_value})
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.repositories.generate_json_response')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_new_scheduled_sync_all_fields(self, mock_factory, mock_rev, mock_resp):
        """
        Create a new scheduled sync with all allowed fields.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps(
            {'schedule': 'some iso8601', 'override_config': {'over': 'ride'},
             'failure_threshold': 2, 'enabled': False}
        )
        mock_schedule = mock.MagicMock()
        mock_schedule.for_display.return_value = {'_id': 'mock_schedule'}
        mock_factory.repo_sync_schedule_manager.return_value.create.return_value = mock_schedule

        sync_schedule = RepoSyncSchedulesView()
        response = sync_schedule.post(mock_request, 'mock_repo', 'mock_importer')

        mock_rev.assert_called_once_with('repo_sync_schedule_resource', kwargs={
            'importer_id': 'mock_importer', 'schedule_id': mock_schedule['_id'],
            'repo_id': 'mock_repo'
        })
        mock_factory.repo_sync_schedule_manager.return_value.create.assert_called_once_with(
            'mock_repo', 'mock_importer', {'override_config': {'over': 'ride'}},
            'some iso8601', 2, False
        )
        mock_resp.assert_called_once_with({'_id': 'mock_schedule', '_href': mock_rev.return_value})
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_new_scheduled_sync_extra_fields(self, mock_factory):
        """
        Create a new scheduled sync with extra nonallowed fields.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps(
            {'schedule': 'some iso8601', 'override_config': {'over': 'ride'},
             'failure_threshold': 2, 'enabled': False, 'extrafield': 'cause failure'}
        )
        sync_schedule = RepoSyncSchedulesView()
        try:
            sync_schedule.post(mock_request, 'mock_repo', 'mock_importer')
        except pulp_exceptions.UnsupportedValue, response:
            pass
        else:
            raise AttributeError("UnsupportedValue should be raised with extra fields in body")

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0017)


class TestRepoSyncScheduleResourceView(unittest.TestCase):
    """
    Tests for the RepoSyncScheduleResourceView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories.RepoSyncScheduleResourceView._get')
    @mock.patch(
        'pulp.server.webservices.views.repositories.manager_factory.repo_sync_schedule_manager')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    def test_get_sync_schedule(self, mock_rev, mock_manager, mock_get):
        """
        Retrieve a single schedule.
        """

        mock_request = mock.MagicMock()
        sync_resource = RepoSyncScheduleResourceView()
        response = sync_resource.get(mock_request, 'mock_repo', 'mock_importer', 'mock_schedule')
        sync_resource.manager.validate_importer.assert_called_once_with('mock_repo',
                                                                        'mock_importer')
        mock_rev.assert_called_once_with('repo_sync_schedule_resource', kwargs={
            'importer_id': 'mock_importer', 'schedule_id': 'mock_schedule', 'repo_id': 'mock_repo'})
        mock_get.assert_called_once_with('mock_schedule', mock_rev.return_value)
        self.assertTrue(response is mock_get.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.repositories.generate_json_response')
    @mock.patch(
        'pulp.server.webservices.views.repositories.manager_factory.repo_sync_schedule_manager')
    def test_delete_sync_schedule(self, mock_manager, mock_resp):
        """
        Delete a single schedule.
        """

        mock_request = mock.MagicMock()
        sync_resource = RepoSyncScheduleResourceView()
        response = sync_resource.delete(mock_request, 'mock_repo', 'mock_importer', 'mock_schedule')
        sync_resource.manager.delete.assert_called_once_with(
            'mock_repo', 'mock_importer', 'mock_schedule')
        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch(
        'pulp.server.webservices.views.repositories.manager_factory.repo_sync_schedule_manager')
    def test_delete_sync_schedule_invalid_schedule(self, mock_manager):
        """
        Attempt to delete a scheduled sync passing an invalid schedule id.
        """

        mock_request = mock.MagicMock()
        selfmanager = mock_manager.return_value
        selfmanager.delete.side_effect = pulp_exceptions.InvalidValue('InvalidValue')
        sync_resource = RepoSyncScheduleResourceView()
        try:
            sync_resource.delete(mock_request, 'mock_repo', 'mock_importer', 'mock_schedule')
        except pulp_exceptions.MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised if url param is invalid")

        self.assertEqual(response.http_status_code, 404)
        self.assertTrue(response.error_code is error_codes.PLP0009)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.generate_json_response')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch(
        'pulp.server.webservices.views.repositories.manager_factory.repo_sync_schedule_manager')
    def test_update_sync_schedule_no_schedule_param(self, mock_manager, mock_rev, mock_resp):
        """
        Attempt to update a dschedueld sync while missing the required schedule parameter.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'some': 'data'})
        sync_resource = RepoSyncScheduleResourceView()
        response = sync_resource.put(mock_request, 'mock_repo', 'mock_importer', 'mock_schedule')
        sync_resource.manager.update.assert_called_once_with(
            'mock_repo', 'mock_importer', 'mock_schedule', {'some': 'data'})

        mock_rev.assert_called_once_with('repo_sync_schedule_resource', kwargs={
            'importer_id': 'mock_importer', 'schedule_id': 'mock_schedule', 'repo_id': 'mock_repo'})
        mock_resp.assert_called_once_with(sync_resource.manager.update().for_display())
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.generate_json_response')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch(
        'pulp.server.webservices.views.repositories.manager_factory.repo_sync_schedule_manager')
    def test_update_sync_schedule_with_schedule_param(self, mock_manager, mock_rev, mock_resp):
        """
        Update a schedueld sync with all required parameters.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'schedule': 'data'})
        sync_resource = RepoSyncScheduleResourceView()
        response = sync_resource.put(mock_request, 'mock_repo', 'mock_importer', 'mock_schedule')

        mock_rev.assert_called_once_with('repo_sync_schedule_resource', kwargs={
            'importer_id': 'mock_importer', 'schedule_id': 'mock_schedule', 'repo_id': 'mock_repo'})
        sync_resource.manager.update.assert_called_once_with(
            'mock_repo', 'mock_importer', 'mock_schedule', {'iso_schedule': 'data'})

        mock_resp.assert_called_once_with(sync_resource.manager.update().for_display())
        self.assertTrue(response is mock_resp.return_value)


class TestRepoDistributorsView(unittest.TestCase):
    """
    Tests for RepoDistributorsView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_distributors(self, mock_factory, mock_resp):
        """
        Get distributors for a repository.
        """

        mock_request = mock.MagicMock()
        mock_dist = [{"mock": "distributor"}]
        mock_factory.repo_distributor_manager.return_value.get_distributors.return_value = mock_dist
        repo_importers = RepoDistributorsView()
        response = repo_importers.get(mock_request, 'mock_repo')
        mock_resp.assert_called_once_with(mock_dist)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.repositories.generate_redirect_response')
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_distributors(self, mock_factory, mock_rev, mock_resp, mock_redir):
        """
        Associate a distributor to a repository with minimal options.
        """

        mock_dist = {'id': 'mock_distributor'}
        mock_manager = mock_factory.repo_distributor_manager.return_value
        mock_manager.add_distributor.return_value = mock_dist
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({})
        repo_dist = RepoDistributorsView()
        response = repo_dist.post(mock_request, 'mock_repo')

        mock_rev.assert_called_once_with('repo_distributor_resource', kwargs={
            'repo_id': 'mock_repo', 'distributor_id': 'mock_distributor'})
        mock_manager.add_distributor.assert_called_once_with(
            'mock_repo', None, None, False, None
        )
        mock_dist['_href'] = mock_rev.return_value
        mock_resp.assert_called_once_with(mock_dist)
        mock_redir.assert_called_once_with(mock_resp.return_value, mock_rev.return_value)
        self.assertTrue(response is mock_redir.return_value)


class TestRepoDistributorsSearchView(unittest.TestCase):

    def test_view(self):
        view = RepoDistributorsSearchView()
        self.assertTrue(isinstance(view, search.SearchView))
        self.assertTrue(isinstance(RepoDistributorsSearchView.manager,
                                   distributor.RepoDistributorManager))
        self.assertEqual(RepoDistributorsSearchView.response_builder,
                         util.generate_json_response_with_pulp_encoder)


class TestRepoDistributorResourceView(unittest.TestCase):
    """
    Tests for RepoDistributorResourceView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_distributor(self, mock_factory, mock_resp):
        """
        Get a distributor for a repository.
        """

        mock_request = mock.MagicMock()
        mock_dist = {"id": "mock_distributor"}
        mock_factory.repo_distributor_manager.return_value.get_distributor.return_value = mock_dist

        repo_dist = RepoDistributorResourceView()
        response = repo_dist.get(mock_request, 'mock_repo', 'mock_distributor')

        mock_resp.assert_called_once_with(mock_dist)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.repositories.repo_tasks.distributor_delete')
    @mock.patch('pulp.server.webservices.views.repositories.tags')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_delete_distributor(self, mock_factory, mock_tags, mock_delete):
        """
        Diassociate a distributor from a repository.
        """

        mock_request = mock.MagicMock()
        mock_task = [mock_tags.resource_tag(), mock_tags.resource_tag(), mock_tags.action_tag()]
        repo_dist = RepoDistributorResourceView()

        try:
            repo_dist.delete(mock_request, 'mock_repo', 'mock_distributor')
        except pulp_exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError("OperationPostponed should be raised for delete task")

        self.assertEqual(response.http_status_code, 202)
        mock_delete.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE, 'mock_repo', ['mock_repo', 'mock_distributor'],
            tags=mock_task
        )

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.repo_tasks')
    @mock.patch('pulp.server.webservices.views.repositories.tags')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_put_update_distributor(self, mock_factory, mock_tags, mock_repo_tasks):
        """
        Update a distributor with all required params.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'distributor_config': 'test'})
        mock_task = [mock_tags.resource_tag(), mock_tags.resource_tag(), mock_tags.action_tag()]

        repo_distributor = RepoDistributorResourceView()
        try:
            repo_distributor.put(mock_request, 'mock_repo', 'mock_distributor')
        except pulp_exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError("OperationPostponed should be raised for update distributor task")

        self.assertEqual(response.http_status_code, 202)
        mock_repo_tasks.distributor_update.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE, 'mock_repo',
            ['mock_repo', 'mock_distributor', 'test', None], tags=mock_task
        )

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_put_update_dist_no_conf(self, mock_factory):
        """
        Update a distributor without the required param 'distributor_config'.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({})
        repo_distributor = RepoDistributorResourceView()
        try:
            repo_distributor.put(mock_request, 'mock_repo', 'mock_distributor')
        except pulp_exceptions.MissingValue, response:
            pass
        else:
            raise AssertionError("MissingValue should be raised if distributor_config is missing")

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0016)


class TestRepoPublishSchedulesView(unittest.TestCase):
    """
    Tests for RepoPublishSchedulesView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories.generate_json_response')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_all_scheduled_publishes(self, mock_factory, mock_rev, mock_resp):
        """
        Get a list of scheduled publishes.
        """

        mock_request = mock.MagicMock()
        mock_schedule = mock.MagicMock()
        mock_schedule.for_display.return_value = {'_id': 'mock_schedule'}
        mock_factory.repo_publish_schedule_manager.return_value.list.return_value = [mock_schedule]

        publish_schedule = RepoPublishSchedulesView()
        response = publish_schedule.get(mock_request, 'mock_repo', 'mock_importer')

        mock_rev.assert_called_once_with('repo_publish_schedule_resource', kwargs={
            'schedule_id': 'mock_schedule', 'repo_id': 'mock_repo',
            'distributor_id': 'mock_importer'})
        mock_resp.assert_called_once_with([{'_id': 'mock_schedule',
                                            '_href': mock_rev.return_value}])
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.repositories.generate_redirect_response')
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_new_scheduled_publish(self, mock_factory, mock_rev, mock_resp, mock_redir):
        """
        Create a new scheduled publish.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({})
        mock_schedule = mock.MagicMock()
        mock_schedule.for_display.return_value = {'_id': 'mock_schedule'}
        mock_factory.repo_publish_schedule_manager.return_value.create.return_value = mock_schedule

        publish_schedule = RepoPublishSchedulesView()
        response = publish_schedule.post(mock_request, 'mock_repo', 'mock_distributor')

        mock_rev.assert_called_once_with('repo_publish_schedule_resource', kwargs={
            'schedule_id': mock_schedule.id, 'repo_id': 'mock_repo',
            'distributor_id': 'mock_distributor'})
        mock_factory.repo_publish_schedule_manager.return_value.create.assert_called_once_with(
            'mock_repo', 'mock_distributor', {'override_config': {}}, None, None, True
        )
        mock_resp.assert_called_once_with({'_id': 'mock_schedule', '_href': mock_rev.return_value})
        self.assertTrue(response is mock_redir.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_new_scheduled_publish_extra_fields(self, mock_factory):
        """
        Create a new scheduled publish with extra nonallowed fields.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'schedule': 'some iso8601', 'extrafield': 'cause failure'})
        publish_schedule = RepoPublishSchedulesView()
        try:
            publish_schedule.post(mock_request, 'mock_repo', 'mock_distributor')
        except pulp_exceptions.UnsupportedValue, response:
            pass
        else:
            raise AttributeError("UnsupportedValue should be raised with extra fields in body")

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0017)


class TestRepoPublishScheduleResourceView(unittest.TestCase):
    """
    Tests for the RepoPublishScheduleResourceView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories.RepoPublishScheduleResourceView._get')
    @mock.patch(
        'pulp.server.webservices.views.repositories.manager_factory.repo_publish_schedule_manager')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    def test_get_publish_schedule(self, mock_rev, mock_manager, mock_get):
        """
        Test retrieval of a single scheduled publish.
        """

        mock_request = mock.MagicMock()
        publish_resource = RepoPublishScheduleResourceView()
        response = publish_resource.get(mock_request, 'repo', 'dist', 'mock_schedule')

        mock_rev.assert_called_once_with('repo_publish_schedule_resource', kwargs={
            'schedule_id': 'mock_schedule', 'repo_id': 'repo', 'distributor_id': 'dist'})
        publish_resource.manager.validate_distributor.assert_called_once_with('repo', 'dist')
        mock_get.assert_called_once_with('mock_schedule', mock_rev.return_value)
        self.assertTrue(response is mock_get.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.repositories.generate_json_response')
    @mock.patch(
        'pulp.server.webservices.views.repositories.manager_factory.repo_publish_schedule_manager')
    def test_delete_publish_schedule(self, mock_manager, mock_resp):
        """
        Test delete of a sheduled publish.
        """

        mock_request = mock.MagicMock()
        publish_resource = RepoPublishScheduleResourceView()
        response = publish_resource.delete(mock_request, 'mock_repo', 'mock_dist', 'mock_schedule')
        publish_resource.manager.delete.assert_called_once_with(
            'mock_repo', 'mock_dist', 'mock_schedule')
        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch(
        'pulp.server.webservices.views.repositories.manager_factory.repo_publish_schedule_manager')
    def test_delete_publish_schedule_invalid_schedule(self, mock_manager):
        """
        Test delete of a sheduled publish with an invalid schedule id.
        """

        mock_request = mock.MagicMock()
        selfmanager = mock_manager.return_value
        selfmanager.delete.side_effect = pulp_exceptions.InvalidValue('InvalidValue')
        publish_resource = RepoPublishScheduleResourceView()
        try:
            publish_resource.delete(mock_request, 'mock_repo', 'mock_importer', 'mock_schedule')
        except pulp_exceptions.MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised if url param is invalid")

        self.assertEqual(response.http_status_code, 404)
        self.assertTrue(response.error_code is error_codes.PLP0009)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.generate_json_response')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch(
        'pulp.server.webservices.views.repositories.manager_factory.repo_publish_schedule_manager')
    def test_update_publish_schedule_no_schedule_param(self, mock_manager, mock_rev, mock_resp):
        """
        Test update schedule with minimal data.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'some': 'data'})
        publish_resource = RepoPublishScheduleResourceView()
        response = publish_resource.put(mock_request, 'mock_repo', 'mock_dist', 'mock_schedule')
        publish_resource.manager.update.assert_called_once_with(
            'mock_repo', 'mock_dist', 'mock_schedule', {'some': 'data'})

        mock_rev.assert_called_once_with('repo_publish_schedule_resource', kwargs={
            'schedule_id': 'mock_schedule', 'repo_id': 'mock_repo', 'distributor_id': 'mock_dist'})
        mock_resp.assert_called_once_with(publish_resource.manager.update().for_display())
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.generate_json_response')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    @mock.patch(
        'pulp.server.webservices.views.repositories.manager_factory.repo_publish_schedule_manager')
    def test_update_publish_schedule_with_schedule_param(self, mock_manager, mock_rev, mock_resp):
        """
        Test that schedule param is changed to iso_schedule.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'schedule': 'data'})
        publish_resource = RepoPublishScheduleResourceView()
        response = publish_resource.put(mock_request, 'mock_repo', 'mock_dist', 'mock_schedule')
        publish_resource.manager.update.assert_called_once_with(
            'mock_repo', 'mock_dist', 'mock_schedule', {'iso_schedule': 'data'})

        mock_rev.assert_called_once_with('repo_publish_schedule_resource', kwargs={
            'schedule_id': 'mock_schedule', 'repo_id': 'mock_repo', 'distributor_id': 'mock_dist'})
        mock_resp.assert_called_once_with(publish_resource.manager.update().for_display())
        self.assertTrue(response is mock_resp.return_value)


class TestContentApplicabilityRegenerationView(unittest.TestCase):
    """
    Tests for the ContentApplicabilityRegenerationView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.repositories.regenerate_applicability_for_repos')
    @mock.patch('pulp.server.webservices.views.repositories.tags')
    @mock.patch('pulp.server.webservices.views.repositories.Criteria.from_client_input')
    def test_post_with_expected_content(self, mock_crit, mock_tags, mock_regen):
        """
        Test regenerate content applicability with expected params.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'repo_criteria': {}})
        content_app_regen = ContentApplicabilityRegenerationView()
        try:
            content_app_regen.post(mock_request)
        except pulp_exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raised for a regenerate task')

        self.assertEqual(response.http_status_code, 202)
        mock_regen.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_PROFILE_APPLICABILITY_TYPE, mock_tags.RESOURCE_ANY_ID,
            (mock_crit.return_value.as_dict(),), tags=[mock_tags.action_tag()]
        )

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.repositories.Criteria.from_client_input')
    def test_post_with_invalid_repo_criteria(self, mock_crit):
        """
        Test regenerate content applicability with invalid repo_criteria.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'repo_criteria': 'not a dict'})
        content_app_regen = ContentApplicabilityRegenerationView()
        mock_crit.side_effect = pulp_exceptions.InvalidValue("Invalid repo criteria")
        try:
            content_app_regen.post(mock_request)
        except pulp_exceptions.InvalidValue, response:
            pass
        else:
            raise AssertionError('InvalidValue should be raised if repo_criteria is not valid')

        self.assertEqual(response.http_status_code, 400)
        mock_crit.assert_called_once_with('not a dict')

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.repositories.regenerate_applicability_for_repos')
    def test_post_without_repo_criteria(self, mock_crit):
        """
        Test regenerate content applicability with missing repo_criteria.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'not_repo_criteria': 'data'})
        content_app_regen = ContentApplicabilityRegenerationView()
        mock_crit.side_effect = pulp_exceptions.InvalidValue("Invalid repo criteria")
        try:
            content_app_regen.post(mock_request)
        except pulp_exceptions.MissingValue, response:
            pass
        else:
            raise AssertionError('InvalidValue should be raised if repo_criteria is None')

        self.assertEqual(response.http_status_code, 400)


class TestRepoSyncHistory(unittest.TestCase):
    """
    Tests for RepoSyncHistory.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_no_params(self, mock_factory, mock_resp):
        """
        Get repo sync history without passing any parameters, should run with default values.
        """

        mock_manager = mock_factory.repo_sync_manager.return_value
        mock_request = mock.MagicMock()
        mock_request.GET = {}

        sync_history = RepoSyncHistory()
        response = sync_history.get(mock_request, 'mock_repo')
        mock_manager.sync_history.assert_called_once_with(
            'mock_repo', limit=None, sort='descending', start_date=None, end_date=None
        )
        mock_resp.assert_called_once_with(mock_manager.sync_history.return_value)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_with_params(self, mock_factory, mock_resp):
        """
        Test that params are correctly parsed and passed.
        """

        mock_manager = mock_factory.repo_sync_manager.return_value
        mock_request = mock.MagicMock()
        mock_request.GET = {
            constants.REPO_HISTORY_FILTER_LIMIT: '8',
            constants.REPO_HISTORY_FILTER_SORT: 'ascending',
            constants.REPO_HISTORY_FILTER_START_DATE: 'date',
            constants.REPO_HISTORY_FILTER_END_DATE: 'other_date',
        }

        sync_history = RepoSyncHistory()
        response = sync_history.get(mock_request, 'mock_repo')
        mock_manager.sync_history.assert_called_once_with(
            'mock_repo', limit=8, sort='ascending', start_date='date', end_date='other_date'
        )
        mock_resp.assert_called_once_with(mock_manager.sync_history.return_value)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    def test_get_with_nonint_limit(self):
        """
        Pass an invalid (non-integer) limit parameter.
        """
        mock_request = mock.MagicMock()
        mock_request.GET = {constants.REPO_HISTORY_FILTER_LIMIT: 'not an int'}

        sync_history = RepoSyncHistory()
        try:
            sync_history.get(mock_request, 'mock_repo')
        except pulp_exceptions.InvalidValue, response:
            pass
        else:
            raise AssertionError('InvalidValue should be raised if limit is not an integer')

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0015)


class TestRepoPublishHistory(unittest.TestCase):
    """
    Tests for RepoPublishHistory.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_no_params(self, mock_factory, mock_resp):
        """
        Get the repo publish history without any GET parameters.
        """

        mock_manager = mock_factory.repo_publish_manager.return_value
        mock_request = mock.MagicMock()
        mock_request.GET = {}

        publish_history = RepoPublishHistory()
        response = publish_history.get(mock_request, 'mock_repo', 'mock_dist')
        mock_manager.publish_history.assert_called_once_with(
            'mock_repo', 'mock_dist', limit=None, sort='descending', start_date=None, end_date=None
        )
        mock_resp.assert_called_once_with(mock_manager.publish_history.return_value)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_get_with_params(self, mock_factory, mock_resp):
        """
        Get the repo publish history with all supported GET parameters.
        """

        mock_manager = mock_factory.repo_publish_manager.return_value
        mock_request = mock.MagicMock()
        mock_request.GET = {
            constants.REPO_HISTORY_FILTER_LIMIT: '8',
            constants.REPO_HISTORY_FILTER_SORT: 'ascending',
            constants.REPO_HISTORY_FILTER_START_DATE: 'date',
            constants.REPO_HISTORY_FILTER_END_DATE: 'other',
        }

        publish_history = RepoPublishHistory()
        response = publish_history.get(mock_request, 'mock_repo', 'mock_dist')
        mock_manager.publish_history.assert_called_once_with(
            'mock_repo', 'mock_dist', limit=8, sort='ascending', start_date='date', end_date='other'
        )
        mock_resp.assert_called_once_with(mock_manager.publish_history.return_value)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    def test_get_with_nonint_limit(self):
        """
        Pass an invalid limit (not an integer)
        """

        mock_request = mock.MagicMock()
        mock_request.GET = {constants.REPO_HISTORY_FILTER_LIMIT: 'not an int'}

        publish_history = RepoPublishHistory()
        try:
            publish_history.get(mock_request, 'mock_repo', 'mock_dist')
        except pulp_exceptions.InvalidValue, response:
            pass
        else:
            raise AssertionError('InvalidValue should be raised if limit is not an integer')

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0015)


class TestRepoSync(unittest.TestCase):
    """
    Tests for RepoSync.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.repositories.repo_tasks')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_sync_repo(self, mock_factory, mock_repo_tasks):
        """
        Test that a repo sync task is dispatched.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'override_config': 'mock_conf'})

        sync_repo = RepoSync()
        try:
            sync_repo.post(mock_request, 'mock_repo')
        except pulp_exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raised for sync task')

        mock_factory.repo_query_manager().get_repository.assert_called_once_with('mock_repo')
        mock_repo_tasks.sync_with_auto_publish.assert_called_once_with(
            'mock_repo', 'mock_conf'
        )
        self.assertEqual(response.http_status_code, 202)


class TestRepoPublish(unittest.TestCase):
    """
    Tests for RepoPublish.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.repositories.repo_tasks')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_publish_repo(self, mock_factory, mock_repo_tasks):
        """
        Test that a repo publish task is dispatched.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'override_config': 'mock_conf', 'id': 'mock_dist'})

        publish_repo = RepoPublish()
        try:
            publish_repo.post(mock_request, 'mock_repo')
        except pulp_exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raised for publish task')

        mock_factory.repo_query_manager().get_repository.assert_called_once_with('mock_repo')
        mock_repo_tasks.publish.assert_called_once_with(
            'mock_repo', 'mock_dist', 'mock_conf'
        )
        self.assertEqual(response.http_status_code, 202)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_publish_repo_missing_distributor(self, mock_factory):
        """
        Test that a repo publish requires distributor id in body.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'not_id': 'will_fail'})

        publish_repo = RepoPublish()
        try:
            publish_repo.post(mock_request, 'mock_repo')
        except pulp_exceptions.MissingValue, response:
            pass
        else:
            raise AssertionError('MissingValue should be raised if id for distributor not passed')

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0016)


class TestRepoAssociate(unittest.TestCase):
    """
    Tests for RepoAssociate.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.tags')
    @mock.patch('pulp.server.webservices.views.repositories.associate_from_repo')
    @mock.patch(
        'pulp.server.webservices.views.repositories.UnitAssociationCriteria.from_client_input')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_minimal(self, mock_factory, mock_get_repo, mock_associate, mock_tags):
        """
        Test that a task is created with the minimal body params.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'source_repo_id': 'mock_source_repo'})
        repo_associate = RepoAssociate()

        try:
            repo_associate.post(mock_request, 'mock_dest_repo')
        except pulp_exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raise for an associate task')

        task_tags = [mock_tags.resource_tag(), mock_tags.resource_tag(), mock_tags.action_tag()]
        mock_associate.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE, 'mock_dest_repo',
            ['mock_source_repo', 'mock_dest_repo'],
            {'criteria': None, 'import_config_override': None},
            tags=task_tags
        )
        self.assertEqual(response.http_status_code, 202)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_missing_source_repo(self, mock_factory):
        """
        Test that a 400 is thrown when the source repo is not passed.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'not_source_repo_id': 'mock_source_repo'})
        repo_associate = RepoAssociate()

        try:
            repo_associate.post(mock_request, 'mock_dest_repo')
        except pulp_exceptions.MissingValue, response:
            pass
        else:
            raise AssertionError('MissingValue should be raised if source_repo_id not in body')

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0016)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_invalid_source_repo(self, mock_factory):
        """
        Test that a 400 is thrown when the source repo does not exist.
        """

        source_repo = 'mock_source_repo'

        def mock_get_repo(repo_id):
            """
            Do not raise MissingResource for dest_repo_id, just source_repo_id.
            """
            if repo_id == source_repo:
                raise pulp_exceptions.MissingResource
            return

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'source_repo_id': source_repo})
        mock_factory.repo_query_manager.return_value.get_repository.side_effect = mock_get_repo
        repo_associate = RepoAssociate()

        try:
            repo_associate.post(mock_request, 'mock_dest_repo')
        except pulp_exceptions.InvalidValue, response:
            pass
        else:
            raise AssertionError('InvalidValue should be raised if source_repo_id does not exist')

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0015)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.UnitAssociationCriteria')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_unparsable_criteria(self, mock_factory, mock_crit):
        """
        Test that a helpful exception is raised when criteria passed in body is unparsable.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'source_repo_id': 'mock_repo', 'criteria': 'mock_crit'})
        repo_associate = RepoAssociate()
        mock_crit.from_client_input.side_effect = pulp_exceptions.InvalidValue("Fake value")

        try:
            repo_associate.post(mock_request, 'mock_dest_repo')
        except pulp_exceptions.InvalidValue, response:
            pass
        else:
            raise AssertionError('InvalidValue should be raised if criteria cannot be parsed')

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0015)


class TestRepoUnunassociate(unittest.TestCase):
    """
    Tests for RepoUnunassociate.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.tags')
    @mock.patch('pulp.server.webservices.views.repositories.unassociate_by_criteria')
    @mock.patch(
        'pulp.server.webservices.views.repositories.UnitAssociationCriteria.from_client_input')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_minimal(self, mock_factory, mock_crit, mock_unassociate, mock_tags):
        """
        Test that a task is created with the minimal body params.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({})
        repo_unassociate = RepoUnassociate()

        try:
            repo_unassociate.post(mock_request, 'mock_repo')
        except pulp_exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raise for an unassociate task')

        task_tags = [mock_tags.resource_tag(), mock_tags.action_tag()]
        mock_unassociate.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE, 'mock_repo', ['mock_repo', None],
            tags=task_tags
        )
        self.assertEqual(response.http_status_code, 202)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.UnitAssociationCriteria')
    def test_post_unparsable_criteria(self, mock_crit):
        """
        Test that a helpful exception is thrown when criteria passed in body is unparsable.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'criteria': 'mock_crit'})
        repo_unassociate = RepoUnassociate()
        mock_crit.from_client_input.side_effect = pulp_exceptions.InvalidValue("Fake value")

        try:
            repo_unassociate.post(mock_request, 'mock_repo')
        except pulp_exceptions.InvalidValue, response:
            pass
        else:
            raise AssertionError('InvalidValue should be raised if repo_id cannot be parsed')

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0015)


class TestRepoImportUpload(unittest.TestCase):
    """
    Tests for RepoImportUpload.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.tags')
    @mock.patch('pulp.server.webservices.views.repositories.import_uploaded_unit')
    def test_post_minimal(self, mock_import, mock_tags):
        """
        Test that a task is created with the minimal body params.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'upload_id': 'mock_id', 'unit_type_id': 'mock_type',
                                        'unit_key': 'mock_key'})
        repo_import = RepoImportUpload()

        try:
            repo_import.post(mock_request, 'mock_repo')
        except pulp_exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raise for an import task')

        task_tags = [mock_tags.resource_tag(), mock_tags.action_tag()]
        mock_import.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE, 'mock_repo',
            ['mock_repo', 'mock_type', 'mock_key', None, 'mock_id', None],
            tags=task_tags
        )
        self.assertEqual(response.http_status_code, 202)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    def test_post_missing_required_params(self):
        """
        Test that a missing params is handled correctly.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'upload_id': 'mock_id', 'unit_type_id': 'mock_type',
                                        'not_unit_key': 'irrelevent'})
        repo_import = RepoImportUpload()

        try:
            repo_import.post(mock_request, 'mock_repo')
        except pulp_exceptions.MissingValue, response:
            pass
        else:
            raise AssertionError('MissingValue should be raised when missing required body params.')

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0016)
