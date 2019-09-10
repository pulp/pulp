from operator import itemgetter
import json

from django import http
import mock

from base import (
    assert_auth_CREATE, assert_auth_DELETE, assert_auth_EXECUTE, assert_auth_READ,
    assert_auth_UPDATE
)
from pulp.common import constants, error_codes
from pulp.common.compat import unittest
from pulp.server import exceptions
from pulp.server.controllers import repository as repo_controller
from pulp.server.db import model
from pulp.server.webservices.views import repositories, util, search
from pulp.server.webservices.views.repositories import (
    ContentApplicabilityRegenerationView, HistoryView, RepoAssociate, RepoDistributorResourceView,
    RepoDistributorsView, RepoDistributorsSearchView, RepoImportUpload, RepoImporterResourceView,
    RepoImportersView, RepoPublish, RepoPublishHistory, RepoPublishScheduleResourceView,
    RepoPublishSchedulesView, RepoResourceView, RepoSearch, RepoSync, RepoSyncHistory,
    RepoSyncScheduleResourceView, RepoSyncSchedulesView, RepoUnassociate, RepoUnitSearch,
    ReposView, RepoDownload
)


@mock.patch('pulp.server.webservices.views.repositories.model')
class TestMergeRelatedObjects(unittest.TestCase):
    """
    Tests for merge related objects
    """

    def test_merge_as_expected(self, m_model):
        """
        Test that objects are included in the appropriate repositories.
        """

        def mock_serializer(data):
            """
            Imitate the serialzer by storing the data in .data.
            """
            mock_ret = mock.MagicMock()
            mock_ret.data = data
            return mock_ret

        mock_repos = [{'id': 'mock1'}, {'id': 'mock2'}]
        mock_importers = [{'repo_id': 'mock1', 'id': 'mock_importer1'},
                          {'repo_id': 'mock1', 'id': 'mock_importer2'},
                          {'repo_id': 'mock2', 'id': 'mock_importer2'}]

        m_model.Importer.objects.return_value = mock_importers
        m_model.Importer.SERIALIZER = mock_serializer

        # If this is available, it will be used. Removed after https://pulp.plan.io/issues/780
        del m_model.Importer.find_by_repo_list

        repositories._merge_related_objects('importers', m_model.Importer, mock_repos)
        self.assertTrue(len(mock_repos) == 2)
        self.assertEqual(map(itemgetter('id'), mock_repos), ['mock1', 'mock2'])
        mock1_expected_importers = [{'repo_id': 'mock1', 'id': 'mock_importer1'},
                                    {'repo_id': 'mock1', 'id': 'mock_importer2'}]
        mock2_expected_importers = [{'repo_id': 'mock2', 'id': 'mock_importer2'}]
        mock1_importers = mock_repos[map(itemgetter('id'), mock_repos).index('mock1')]['importers']
        mock2_importers = mock_repos[map(itemgetter('id'), mock_repos).index('mock2')]['importers']
        self.assertEqual(mock1_importers, mock1_expected_importers)
        self.assertEqual(mock2_importers, mock2_expected_importers)

    def test_no_objects(self, m_model):
        """
        Test that merge happens correctly when there are no objects to merge.
        """

        mock_repos = [{'id': 'mock1'}, {'id': 'mock2'}]

        m_model.Importer.objects.return_value = []
        repositories._merge_related_objects('importers', m_model.Importer, mock_repos)

        self.assertTrue(len(mock_repos) == 2)
        self.assertEqual(map(itemgetter('id'), mock_repos), ['mock1', 'mock2'])
        mock1_importers = mock_repos[map(itemgetter('id'), mock_repos).index('mock1')]['importers']
        mock2_importers = mock_repos[map(itemgetter('id'), mock_repos).index('mock2')]['importers']
        self.assertEqual(mock1_importers, [])
        self.assertEqual(mock2_importers, [])


class TestReposView(unittest.TestCase):
    """
    Tests for ReposView.
    """

    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._merge_related_objects')
    @mock.patch('pulp.server.webservices.views.repositories.serializers.Repository')
    def test__process_repos_minimal(self, mock_serializer, mock_merge, mock_resp):
        """
        Test _process_repos without optional args, assert that processing was called for each repo.
        """
        doc_1 = mock.MagicMock()
        doc_2 = mock.MagicMock()
        mock_repos = [doc_1, doc_2]

        repositories._process_repos(mock_repos, False, False, False)
        self.assertEqual(mock_merge.call_count, 0)

    @mock.patch('pulp.server.webservices.views.repositories.model')
    @mock.patch('pulp.server.webservices.views.repositories._merge_related_objects')
    @mock.patch('pulp.server.webservices.views.repositories.serializers.Repository')
    def test__process_repos_with_details(self, mock_serial, mock_merge, m_model):
        """
        Test _process_repos with details='true', assert that processing was called for each repo.
        """
        doc_1 = mock.MagicMock()
        doc_2 = mock.MagicMock()
        mock_repos = [doc_1, doc_2]

        repositories._process_repos(mock_repos, True, False, False)
        mock_merge.assert_has_calls([
            mock.call('importers', m_model.Importer, mock_serial().data),
            mock.call('distributors', m_model.Distributor, mock_serial().data)
        ])

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.serializers.Repository')
    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    @mock.patch('pulp.server.webservices.views.repositories.model')
    def test_get_repos_no_options(self, mock_model, mock_process, mock_serial, mock_resp):
        """
        Get repos without passing options.
        """

        mock_repos = [{'mock_repo_1': 'somedata'}, {'mock_repo_2': 'moredata'}]
        mock_model.Repository.objects.return_value = mock_repos
        mock_request = mock.MagicMock()
        mock_request.GET = {}
        repos_view = ReposView()
        response = repos_view.get(mock_request)
        mock_process.assert_called_once_with(mock_model.Repository.objects(), False, False, False)
        mock_resp.assert_called_once_with(mock_process.return_value)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_get_repos_with_details(self, mock_repo_qs, mock_process, mock_resp):
        """
        Get repos with the details shortcut.
        """

        mock_repos = [{'mock_repo_1': 'somedata'}, {'mock_repo_2': 'moredata'}]
        mock_repo_qs.return_value = mock_repos
        mock_request = mock.MagicMock()
        mock_request.GET = http.QueryDict('details=True')
        repos_view = ReposView()
        repos_view.get(mock_request)
        mock_process.assert_called_once_with(mock_repos, True, False, False)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_get_repos_with_false(self, mock_repo_qs, mock_process, mock_resp):
        """
        Get repos with by passing an optional get parameter 'details=false'

        This test seem a little excessive, but this is in response to previous incorrect
        behavior. The string 'false' is actually truthy and was being used incorrectly.
        """

        mock_repos = [{'mock_repo_1': 'somedata'}, {'mock_repo_2': 'moredata'}]
        mock_repo_qs.return_value = mock_repos
        mock_request = mock.MagicMock()
        mock_request.GET = http.QueryDict('details=False')
        repos_view = ReposView()

        repos_view.get(mock_request)
        mock_process.assert_called_once_with(mock_repos, False, False, False)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_get_repos_with_lowercase_boolean(self, mock_repo_qs, mock_process, mock_resp):
        """
        Get repos with lowercase true as a get parameter.
        """

        mock_repos = [{'mock_repo_1': 'somedata'}, {'mock_repo_2': 'moredata'}]
        mock_repo_qs.return_value = mock_repos
        mock_request = mock.MagicMock()
        mock_request.GET = http.QueryDict('details=true')
        repos_view = ReposView()
        repos_view.get(mock_request)
        mock_process.assert_called_once_with(mock_repos, True, False, False)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_get_repos_with_invalid_boolean(self, mock_repo_qs, mock_process, mock_resp):
        """
        Get repos with invalid details get parameter, default to False
        """

        mock_repos = [{'mock_repo_1': 'somedata'}, {'mock_repo_2': 'moredata'}]
        mock_repo_qs.return_value = mock_repos
        mock_request = mock.MagicMock()
        mock_request.GET = {'details': 'yes'}
        repos_view = ReposView()

        repos_view.get(mock_request)
        mock_process.assert_called_once_with(mock_repos, False, False, False)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_get_repos_with_importers(self, mock_repo_qs, mock_process, mock_resp):
        """
        Get repos with importer information.
        """

        mock_repos = [{'mock_repo_1': 'somedata'}, {'mock_repo_2': 'moredata'}]
        mock_repo_qs.return_value = mock_repos
        mock_request = mock.MagicMock()
        mock_request.GET = http.QueryDict('importers=True')
        repos_view = ReposView()
        repos_view.get(mock_request)
        mock_process.assert_called_once_with(mock_repos, False, True, False)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._process_repos')
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_get_repos_with_distributors(self, mock_repo_qs, mock_process, mock_resp):
        """
        Get repos with distributor information.
        """

        mock_repos = [{'mock_repo_1': 'somedata'}, {'mock_repo_2': 'moredata'}]
        mock_repo_qs.return_value = mock_repos
        mock_request = mock.MagicMock()
        mock_request.GET = http.QueryDict('distributors=True')
        repos_view = ReposView()
        repos_view.get(mock_request)
        mock_process.assert_called_once_with(mock_repos, False, False, True)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.generate_redirect_response')
    @mock.patch('pulp.server.webservices.views.repositories.serializers.Repository')
    @mock.patch('pulp.server.webservices.views.repositories.repo_controller')
    def test_post_repos_only_id(self, mock_ctrl, mock_serial, mock_redir, mock_resp):
        """
        Create a repo using the minimal body.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'id': 'mock_repo'})
        mock_serial().data = {'id': 'mock_repo', '_href': '/mock/path/'}

        repos_view = ReposView()
        response = repos_view.post(mock_request)

        expected_kwargs = {
            'display_name': 'mock_repo', 'description': None, 'notes': None,
            'importer_type_id': None, 'importer_repo_plugin_config': None, 'distributor_list': None
        }

        mock_ctrl.create_repo.assert_called_once_with('mock_repo', **expected_kwargs)
        mock_resp.assert_called_once_with(mock_serial().data)
        mock_redir.assert_called_once_with(mock_resp.return_value, '/mock/path/')
        self.assertTrue(response is mock_redir.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.generate_redirect_response')
    @mock.patch('pulp.server.webservices.views.repositories.serializers.Repository')
    @mock.patch('pulp.server.webservices.views.repositories.repo_controller')
    def test_post_repos_all_fields(self, mock_ctrl, mock_serial, mock_redir, mock_resp):
        """
        Create a repo using all allowed fields.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({
            'id': 'mock_repo', 'display_name': 'mock_display', 'description': 'mock_desciption',
            'notes': 'mock_notes', 'importer_type_id': 'mock_importer',
            'importer_config': 'mock_imp_conf', 'distributors': ['dist1']
        })
        expected_kwargs = {
            'display_name': 'mock_display', 'description': 'mock_desciption',
            'notes': 'mock_notes', 'importer_type_id': 'mock_importer',
            'importer_repo_plugin_config': 'mock_imp_conf', 'distributor_list': ['dist1']
        }
        mock_serial().data = {'mock': 'dict', '_href': '/mock/path/'}

        repos_view = ReposView()
        response = repos_view.post(mock_request)

        mock_ctrl.create_repo.assert_called_once_with('mock_repo', **expected_kwargs)
        mock_resp.assert_called_once_with(mock_serial().data)
        mock_redir.assert_called_once_with(mock_resp.return_value, '/mock/path/')
        self.assertTrue(response is mock_redir.return_value)


class TestRepoResourceView(unittest.TestCase):
    """
    Tests for RepoResoureceView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories.serializers.Repository')
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.model')
    def test_get_existing_repo(self, mock_model, mock_resp, mock_serialize):
        """
        Retrieve an existing repository.
        """

        mock_repo = {'mock_repo': 'somedata'}
        mock_model.Repository.objects.get_repo_or_missing_resource.return_value = mock_repo
        mock_request = mock.MagicMock()
        mock_request.GET = {}

        repos_resource = RepoResourceView()
        response = repos_resource.get(mock_request, 'mock_repo')

        mock_serialize.assert_called_once_with(mock_repo)
        mock_resp.assert_called_once_with(mock_serialize().data)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories.model')
    def test_get_nonexisting_repo(self, mock_model):
        """
        Retrieve a nonexisting repository.
        """

        mock_request = mock.MagicMock()
        repos_resource = RepoResourceView()
        mock_model.Repository.objects.get_repo_or_missing_resource.side_effect = \
            exceptions.MissingResource(repo='mock_repo')
        try:
            repos_resource.get(mock_request, 'mock_repo')
        except exceptions.MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised for a nonexisting repository")

        self.assertEqual(response.http_status_code, 404)
        self.assertTrue(response.error_code is error_codes.PLP0009)
        self.assertEqual(response.error_data['resources'], {'repo': 'mock_repo'})

    @mock.patch('__builtin__.sum')
    @mock.patch('pulp.server.webservices.views.repositories.repo_controller')
    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._merge_related_objects')
    @mock.patch('pulp.server.webservices.views.repositories.serializers.Repository')
    @mock.patch('pulp.server.webservices.views.repositories.model')
    def test_get_existing_repo_with_details(self, m_model, m_serialize, m_merge, m_resp,
                                            mock_repo_ctrl, mock_sum):
        mock_repo = mock.MagicMock(spec=model.Repository)
        mock_repo.repo_id = 'mock_repo'
        m_model.Repository.objects.get_repo_or_missing_resource.return_value = mock_repo
        mock_request = mock.MagicMock()
        mock_request.GET = {'details': 'true'}
        m_merge.side_effect = lambda x, y, z: z
        mock_sum.return_value = 30
        mock_repo_ctrl.missing_unit_count.return_value = 10
        serialized_repo = m_serialize.return_value.data

        repos_resource = RepoResourceView()
        response = repos_resource.get(mock_request, 'mock_repo')

        m_serialize.assert_called_once_with(mock_repo)
        m_resp.assert_called_once_with(m_serialize().data)
        self.assertTrue(response is m_resp.return_value)
        self.assertEqual(m_merge.call_count, 2)
        m_merge.assert_has_calls([
            mock.call('importers', m_model.Importer, (m_serialize().data,)),
            mock.call('distributors', m_model.Distributor, (m_serialize().data,)),
        ])
        mock_repo_ctrl.missing_unit_count.assert_called_once_with('mock_repo')
        serialized_repo.__setitem__.assert_any_call(
            'total_repository_units',
            mock_sum.return_value
        )
        serialized_repo.__setitem__.assert_any_call(
            'locally_stored_units',
            serialized_repo.__getitem__.return_value - 10
        )

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._merge_related_objects')
    @mock.patch('pulp.server.webservices.views.repositories.serializers.Repository')
    @mock.patch('pulp.server.webservices.views.repositories.model')
    def test_get_existing_repo_with_details_false(self, mock_model, mock_serialize, mock_merge,
                                                  mock_resp):
        """
        Retrieve an existing repository with details set to false.
        """

        mock_repo = {'mock_repo': 'somedata'}
        mock_model.Repository.objects.get_repo_or_missing_resource.return_value = mock_repo
        mock_request = mock.MagicMock()
        mock_request.GET = {'details': 'false'}
        mock_merge.side_effect = lambda x, y, z: z

        repos_resource = RepoResourceView()
        response = repos_resource.get(mock_request, 'mock_repo')

        mock_serialize.assert_called_once_with(mock_repo)
        mock_resp.assert_called_once_with(mock_serialize().data)
        self.assertTrue(response is mock_resp.return_value)
        self.assertEqual(mock_merge.call_count, 0)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._merge_related_objects')
    @mock.patch('pulp.server.webservices.views.repositories.model')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    @mock.patch('pulp.server.webservices.views.repositories.serializers.Repository')
    def test_get_existing_repo_with_importers(self, mock_serial, mock_factory, mock_model,
                                              mock_merge, mock_resp):
        """
        Retrieve an existing repository with importers.
        """

        mock_repo = mock.MagicMock()
        mock_model.Repository.objects.get_repo_or_missing_resource.return_value = mock_repo
        mock_request = mock.MagicMock()
        mock_request.GET = {'importers': 'true'}
        mock_merge.side_effect = lambda x, y, z: z

        repos_resource = RepoResourceView()
        response = repos_resource.get(mock_request, 'mock_repo')

        mock_serial.assert_called_once_with(mock_repo)
        mock_resp.assert_called_once_with(mock_serial().data)
        self.assertTrue(response is mock_resp.return_value)
        mock_merge.assert_called_once_with('importers', mock_model.Importer, (mock_serial().data,))

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories._merge_related_objects')
    @mock.patch('pulp.server.webservices.views.repositories.serializers.Repository')
    @mock.patch('pulp.server.webservices.views.repositories.model')
    def test_get_existing_repo_with_dists(self, m_model, m_serialize, m_merge, mock_resp):
        """
        Retrieve an existing repository with distributors.
        """

        mock_repo = {'mock_repo': 'somedata'}
        m_model.Repository.objects.get_repo_or_missing_resource.return_value = mock_repo
        mock_request = mock.MagicMock()
        mock_request.GET = {'distributors': 'true'}
        m_merge.side_effect = lambda x, y, z: z

        repos_resource = RepoResourceView()
        response = repos_resource.get(mock_request, 'mock_repo')

        m_serialize.assert_called_once_with(mock_repo)
        mock_resp.assert_called_once_with(m_serialize().data)
        self.assertTrue(response is mock_resp.return_value)
        m_merge.assert_called_once_with('distributors', m_model.Distributor, (m_serialize().data,))

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.repositories.repo_controller')
    @mock.patch('pulp.server.webservices.views.repositories.model')
    def test_delete_existing_repo(self, mock_model, mock_ctrl):
        """
        Dispatch a delete task to remove an existing repository.
        """

        mock_request = mock.MagicMock()
        repos_resource = RepoResourceView()
        try:
            repos_resource.delete(mock_request, 'mock_repo')
        except exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raised for asynchronous delete.')

        mock_model.Repository.objects.get_repo_or_missing_resource.assert_called_once_with(
            'mock_repo')
        mock_ctrl.queue_delete.assert_called_once_with('mock_repo')
        self.assertEqual(response.http_status_code, 202)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.serializers.Repository')
    @mock.patch('pulp.server.webservices.views.repositories.repo_controller')
    @mock.patch('pulp.server.webservices.views.repositories.model')
    def test_put_existing_repo_no_delta(self, mock_model, mock_ctrl, mock_serialize, mock_resp):
        """
        Test update without any data.
        """
        mock_updated_repo = mock.MagicMock()
        mock_report = {'result': mock_updated_repo}
        mock_task_result = mock_ctrl.update_repo_and_plugins.return_value
        mock_task_result.spawned_tasks = False
        mock_task_result.serialize.return_value = mock_report
        mock_repo_obj = mock_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({})

        repos_resource = RepoResourceView()
        response = repos_resource.put(mock_request, 'mock_repo')

        mock_ctrl.update_repo_and_plugins.assert_called_once_with(mock_repo_obj, None, None, None)
        mock_serialize.assert_called_once_with(mock_updated_repo)
        mock_resp.assert_called_once_with({'result': mock_serialize().data})
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.serializers.Repository')
    @mock.patch('pulp.server.webservices.views.repositories.repo_controller')
    @mock.patch('pulp.server.webservices.views.repositories.model')
    def test_put_existing_repo_with_delta(self, mock_model, mock_ctrl, mock_serialize, mock_resp):
        """
        Test update with delta data.
        """

        mock_repo = mock.MagicMock()
        mock_task_result = mock_ctrl.update_repo_and_plugins.return_value
        mock_task_result.spawned_tasks = False
        mock_task_result.serialize.return_value = {'result': mock_repo}

        mock_request = mock.MagicMock()
        mock_data = {'delta': {'description': 'test'}}
        mock_request.body = json.dumps(mock_data)

        repos_resource = RepoResourceView()
        response = repos_resource.put(mock_request, 'mock_repo')

        mock_ctrl.update_repo_and_plugins.assert_called_once_with(
            mock_model.Repository.objects.get_repo_or_missing_resource.return_value,
            mock_data['delta'], None, None
        )
        mock_serialize.assert_called_once_with(mock_repo)
        mock_resp.assert_called_once_with(mock_task_result.serialize.return_value)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.serializers.Repository')
    @mock.patch('pulp.server.webservices.views.repositories.repo_controller')
    @mock.patch('pulp.server.webservices.views.repositories.model')
    def test_put_existing_repo_with_importer(self, mock_model, mock_ctrl, mock_serial, mock_resp):
        """
        Test update with importer config update.
        """

        mock_repo = mock.MagicMock()
        mock_task_result = mock_ctrl.update_repo_and_plugins.return_value
        mock_task_result.spawned_tasks = False
        mock_task_result.serialize.return_value = {'result': mock_repo}

        mock_request = mock.MagicMock()
        mock_data = {'importer_config': 'importer_data'}
        mock_request.body = json.dumps(mock_data)

        repos_resource = RepoResourceView()
        response = repos_resource.put(mock_request, 'mock_repo')

        mock_resp.assert_called_once_with(mock_task_result.serialize.return_value)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.repo_controller')
    @mock.patch('pulp.server.webservices.views.repositories.model')
    def test_put_existing_repo_with_distributor(self, mock_model, mock_ctrl):
        """
        Test update with importer config update.
        """

        mock_task_result = mock_ctrl.update_repo_and_plugins.return_value
        mock_task_result.spawned_tasks = 'distributor'

        mock_request = mock.MagicMock()
        mock_data = {'distributor_configs': 'distributor_data'}
        mock_request.body = json.dumps(mock_data)

        repos_resource = RepoResourceView()

        self.assertRaises(exceptions.OperationPostponed, repos_resource.put,
                          mock_request, 'mock_repo')
        mock_ctrl.update_repo_and_plugins.assert_called_once_with(
            mock_model.Repository.objects.get_repo_or_missing_resource.return_value,
            None, None, 'distributor_data'
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
        self.assertEqual(repo_search.model, model.Repository)
        self.assertEqual(repo_search.optional_bool_fields, ('details', 'importers', 'distributors'))
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

    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory.'
                'repo_unit_association_query_manager')
    @mock.patch('pulp.server.webservices.views.repositories.UnitAssociationCriteria')
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test__generate_response_one_type(self, mock_repo_qs, mock_crit, mock_uqm, mock_resp):
        """
        Test that responses are created using `get_units_by_type` if there is only one type.
        """
        mock_repo_qs.get_repo_or_missing_resource.return_value = 'exists'
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
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test__generate_response_multiple_types(self, mock_repo_qs, mock_crit, mock_uqm, mock_resp):
        """
        Test that responses are created using `get_units` if there are multiple types.
        """
        mock_repo_qs.get_repo_or_missing_resource.return_value = 'exists'
        criteria = mock_crit.from_client_input.return_value
        criteria.type_ids = ['one_type', 'two_types']
        repo_unit_search = RepoUnitSearch()
        repo_unit_search._generate_response('mock_q', {}, repo_id='mock_repo')
        mock_crit.from_client_input.assert_called_once_with('mock_q')
        mock_uqm().get_units.assert_called_once_with('mock_repo', criteria=criteria)
        mock_resp.assert_called_once_with(mock_uqm().get_units.return_value)


class TestRepoImportersView(unittest.TestCase):
    """
    Tests for RepoImportersView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.model.Importer.SERIALIZER')
    @mock.patch('pulp.server.webservices.views.repositories.model.Importer.objects')
    def test_get_importers(self, mock_imp_qs, mock_imp_serializer, mock_resp):
        """
        Get importers for a repository.
        """

        mock_request = mock.MagicMock()
        repo_importers = RepoImportersView()
        response = repo_importers.get(mock_request, 'mock_repo')
        mock_imp_serializer.assert_called_once_with(mock_imp_qs.return_value, multiple=True)
        mock_resp.assert_called_once_with(mock_imp_serializer.return_value.data)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    @mock.patch('pulp.server.webservices.views.repositories.importer_controller')
    @mock.patch('pulp.server.webservices.views.repositories.tags')
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    def test_post_importers(self, mock_factory, mock_tags, mock_importer_ctrl, mock_repo_qs):
        """
        Associate an importer to a repository.
        """
        m_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'importer_type_id': 'mock_type', 'importer_config': 'conf'})
        repo_importers = RepoImportersView()

        try:
            repo_importers.post(mock_request, 'mock_repo')
        except exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError("Associate importer call should raise OperationPostponed")

        self.assertEqual(response.http_status_code, 202)
        mock_importer_ctrl.queue_set_importer.assert_called_once_with(m_repo, 'mock_type', 'conf')


class TestRepoImporterResourceView(unittest.TestCase):
    """
    Tests for RepoImporterResourceView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.importer_controller.get_valid_importer')
    @mock.patch('pulp.server.webservices.views.repositories.model.Importer.SERIALIZER')
    def test_get_importer(self, mock_imp_serializer, mock_validate, mock_resp):
        """
        Get an importer for a repository.
        """

        mock_request = mock.MagicMock()
        repo_importer = RepoImporterResourceView()
        response = repo_importer.get(mock_request, 'mock_repo', 'mock_importer')
        mock_validate.assert_called_once_with('mock_repo', 'mock_importer')
        mock_imp_serializer.assert_called_once_with(mock_validate.return_value)
        mock_resp.assert_called_once_with(mock_imp_serializer.return_value.data)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.repositories.importer_controller')
    def test_delete_importer(self, mock_importer_ctrl):
        """
        Disassociate an importer from a repository.
        """

        mock_request = mock.MagicMock()
        repo_importer = RepoImporterResourceView()
        try:
            repo_importer.delete(mock_request, 'mock_repo', 'mock_importer')
        except exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError("OperationPostponed should be raised for delete task")

        self.assertEqual(response.http_status_code, 202)
        mock_importer_ctrl.queue_remove_importer.assert_called_once_with('mock_repo',
                                                                         'mock_importer')

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.importer_controller')
    def test_put_update_importer(self, mock_imp_ctrl):
        """
        Update an importer with all required params.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'importer_config': 'test'})
        repo_importer = RepoImporterResourceView()
        try:
            repo_importer.put(mock_request, 'mock_repo', 'mock_importer')
        except exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError("OperationPostponed should be raised for update importer task")

        mock_imp_ctrl.queue_update_importer_config.assert_called_once_with('mock_repo',
                                                                           'mock_importer', 'test')
        self.assertEqual(response.http_status_code, 202)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.importer_controller')
    def test_put_no_importer_conf(self, mock_importer_ctrl):
        """
        Update an importer with the importer config missing from the request body.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'not_importer_config': 'will fail'})
        repo_importer = RepoImporterResourceView()
        try:
            repo_importer.put(mock_request, 'mock_repo', 'mock_importer')
        except exceptions.MissingValue, response:
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
        except exceptions.UnsupportedValue, response:
            pass
        else:
            raise AttributeError("UnsupportedValue should be raised with extra fields in body")

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0017)


@mock.patch('pulp.server.webservices.views.repositories.manager_factory.repo_sync_schedule_manager')
@mock.patch('pulp.server.webservices.views.repositories.importer_controller.get_valid_importer')
class TestRepoSyncScheduleResourceView(unittest.TestCase):
    """
    Tests for the RepoSyncScheduleResourceView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.repositories.RepoSyncScheduleResourceView._get')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    def test_get_sync_schedule(self, mock_rev, mock_get, m_validate, mock_manager):
        """
        Retrieve a single schedule.
        """

        mock_request = mock.MagicMock()
        sync_resource = RepoSyncScheduleResourceView()
        response = sync_resource.get(mock_request, 'mock_repo', 'mock_importer', 'mock_schedule')
        mock_rev.assert_called_once_with('repo_sync_schedule_resource', kwargs={
            'importer_id': 'mock_importer', 'schedule_id': 'mock_schedule', 'repo_id': 'mock_repo'})
        mock_get.assert_called_once_with('mock_schedule', mock_rev.return_value)
        self.assertTrue(response is mock_get.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.repositories.generate_json_response')
    def test_delete_sync_schedule(self, mock_resp, m_validate, mock_manager):
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
    def test_delete_sync_schedule_invalid_schedule(self, m_validate, mock_manager):
        """
        Attempt to delete a scheduled sync passing an invalid schedule id.
        """

        mock_request = mock.MagicMock()
        selfmanager = mock_manager.return_value
        selfmanager.delete.side_effect = exceptions.InvalidValue('InvalidValue')
        sync_resource = RepoSyncScheduleResourceView()
        try:
            sync_resource.delete(mock_request, 'mock_repo', 'mock_importer', 'mock_schedule')
        except exceptions.MissingResource, response:
            pass
        else:
            raise AssertionError("MissingResource should be raised if url param is invalid")

        self.assertEqual(response.http_status_code, 404)
        self.assertTrue(response.error_code is error_codes.PLP0009)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.generate_json_response')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    def test_update_sync_sched_no_sched_param(self, mock_rev, mock_resp, m_validate, mock_manager):
        """
        Attempt to update a schedueld sync while missing the required schedule parameter.
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
    def test_update_sync_sched_with_req_params(self, mock_rev, mock_resp, m_validate, mock_manager):
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
    @mock.patch('pulp.server.webservices.views.repositories.model')
    def test_get(self, m_model, m_resp):
        """
        Test that distributors are retrieved and serialized.
        """
        repo_dist = RepoDistributorsView()
        response = repo_dist.get(mock.MagicMock(), 'mock_repo')

        m_model.Distributor.SERIALIZER.assert_called_once_with(
            m_model.Distributor.objects.return_value, multiple=True)
        m_resp.assert_called_once_with(m_model.Distributor.SERIALIZER.return_value.data)
        self.assertTrue(response is m_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth', new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.repositories.generate_redirect_response')
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.model.Distributor.SERIALIZER')
    @mock.patch('pulp.server.webservices.views.repositories.dist_controller')
    def test_post_as_expected(self, m_dist_cont, m_serial, mock_resp, mock_redir):
        """
        Associate a distributor to a repository with minimal options.
        """

        mock_dist = {'id': 'mock_distributor'}
        m_dist_cont.add_distributor.return_value = mock_dist
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'distributor_type_id': 'fake', 'distributor_config': {}})
        m_dist_cont.add_distributor.return_value = {'_href': '/mock/url/'}

        repo_dist = RepoDistributorsView()
        response = repo_dist.post(mock_request, 'mock_repo')

        m_serial.assert_called_once_with(m_dist_cont.add_distributor.return_value)
        mock_resp.assert_called_once_with(m_serial.return_value.data)
        mock_redir.assert_called_once_with(
            mock_resp.return_value, m_serial.return_value.data['_href'])
        self.assertTrue(response is mock_redir.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth', new=assert_auth_CREATE())
    def test_post_missing_dist_type(self):
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'distributor_config': {}})

        repo_dist = RepoDistributorsView()
        self.assertRaises(exceptions.MissingValue, repo_dist.post, mock_request, 'mock_repo')


class TestRepoDistributorsSearchView(unittest.TestCase):
    """
    Tests for distributor searching.
    """

    def test_view(self):
        """
        Assert that the search view has the expected attributes.
        """
        view = RepoDistributorsSearchView()
        self.assertTrue(isinstance(view, search.SearchView))
        self.assertTrue(RepoDistributorsSearchView.model is model.Distributor)
        self.assertEqual(RepoDistributorsSearchView.response_builder,
                         util.generate_json_response_with_pulp_encoder)


@mock.patch('pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
@mock.patch('pulp.server.webservices.views.repositories.dist_controller')
@mock.patch('pulp.server.webservices.views.repositories.model')
class TestRepoDistributorResourceView(unittest.TestCase):
    """
    Tests for RepoDistributorResourceView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    def test_get_distributor(self, m_model, m_dist_cont, m_resp):
        """
        Get a distributor for a repository.
        """
        mock_request = mock.MagicMock()
        repo_dist = RepoDistributorResourceView()
        response = repo_dist.get(mock_request, 'mock_repo', 'mock_distributor')

        m_model.Distributor.SERIALIZER.assert_called_once_with(
            m_model.Distributor.objects.get_or_404.return_value)
        m_resp.assert_called_once_with(m_model.Distributor.SERIALIZER.return_value.data)
        self.assertTrue(response is m_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    def test_delete_distributor(self, m_model, m_dist_cont, m_resp):
        """
        Disassociate a distributor from a repository.
        """

        mock_request = mock.MagicMock()
        repo_dist = RepoDistributorResourceView()

        try:
            repo_dist.delete(mock_request, 'mock_repo', 'mock_distributor')
        except exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError("OperationPostponed should be raised for delete task")

        self.assertEqual(response.http_status_code, 202)
        m_dist_cont.queue_delete.assert_called_once_with(
            m_model.Distributor.objects.get_or_404.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    def test_put_update_distributor(self, m_model, m_dist_cont, m_resp):
        """
        Test that a distributor update task is queued.
        """
        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'distributor_config': 'm_conf', 'delta': 'm_delta'})
        repo_distributor = RepoDistributorResourceView()
        try:
            repo_distributor.put(mock_request, 'mock_repo', 'mock_distributor')
        except exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError("OperationPostponed should be raised for update distributor task")

        self.assertEqual(response.http_status_code, 202)
        m_dist_cont.queue_update.assert_called_once_with(
            m_model.Distributor.objects.get_or_404.return_value, 'm_conf', 'm_delta')


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

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth', new=assert_auth_CREATE())
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

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth', new=assert_auth_CREATE())
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
        except exceptions.UnsupportedValue, response:
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
    @mock.patch('pulp.server.webservices.views.repositories.model.Distributor.objects')
    @mock.patch('pulp.server.webservices.views.repositories.RepoPublishScheduleResourceView._get')
    @mock.patch(
        'pulp.server.webservices.views.repositories.manager_factory.repo_publish_schedule_manager')
    @mock.patch('pulp.server.webservices.views.repositories.reverse')
    def test_get_publish_schedule(self, mock_rev, mock_manager, mock_get, m_dist_qs):
        """
        Test retrieval of a single scheduled publish.
        """

        mock_request = mock.MagicMock()
        publish_resource = RepoPublishScheduleResourceView()
        response = publish_resource.get(mock_request, 'repo', 'dist', 'mock_schedule')

        mock_rev.assert_called_once_with('repo_publish_schedule_resource', kwargs={
            'schedule_id': 'mock_schedule', 'repo_id': 'repo', 'distributor_id': 'dist'})
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
        selfmanager.delete.side_effect = exceptions.InvalidValue('InvalidValue')
        publish_resource = RepoPublishScheduleResourceView()
        try:
            publish_resource.delete(mock_request, 'mock_repo', 'mock_importer', 'mock_schedule')
        except exceptions.MissingResource, response:
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

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth', new=assert_auth_CREATE())
    @mock.patch(('pulp.server.managers.consumer.applicability.ApplicabilityRegenerationManager.'
                'queue_regenerate_applicability_for_repos'))
    @mock.patch('pulp.server.webservices.views.repositories.tags')
    @mock.patch('pulp.server.webservices.views.repositories.Criteria.from_client_input')
    def test_post_with_expected_content(self, mock_crit, mock_tags, mock_regen):
        """
        Test regenerate content applicability with expected params.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'repo_criteria': {}, 'parallel': True})
        content_app_regen = ContentApplicabilityRegenerationView()
        try:
            content_app_regen.post(mock_request)
        except exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raised for a regenerate task')

        self.assertEqual(response.http_status_code, 202)
        mock_regen.assert_called_once_with(mock_crit.return_value.as_dict())

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth', new=assert_auth_CREATE())
    @mock.patch('pulp.server.webservices.views.repositories.Criteria.from_client_input')
    def test_post_with_invalid_repo_criteria(self, mock_crit):
        """
        Test regenerate content applicability with invalid repo_criteria.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'repo_criteria': 'not a dict'})
        content_app_regen = ContentApplicabilityRegenerationView()
        mock_crit.side_effect = exceptions.InvalidValue("Invalid repo criteria")
        try:
            content_app_regen.post(mock_request)
        except exceptions.InvalidValue, response:
            pass
        else:
            raise AssertionError('InvalidValue should be raised if repo_criteria is not valid')

        self.assertEqual(response.http_status_code, 400)
        mock_crit.assert_called_once_with('not a dict')

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth', new=assert_auth_CREATE())
    @mock.patch(('pulp.server.managers.consumer.applicability.ApplicabilityRegenerationManager.'
                'queue_regenerate_applicability_for_repos'))
    def test_post_without_repo_criteria(self, mock_crit):
        """
        Test regenerate content applicability with missing repo_criteria.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'not_repo_criteria': 'data'})
        content_app_regen = ContentApplicabilityRegenerationView()
        mock_crit.side_effect = exceptions.InvalidValue("Invalid repo criteria")
        try:
            content_app_regen.post(mock_request)
        except exceptions.MissingValue, response:
            pass
        else:
            raise AssertionError('InvalidValue should be raised if repo_criteria is None')

        self.assertEqual(response.http_status_code, 400)


class TestHistoryView(unittest.TestCase):
    """
    Tests for the HistoryView base class.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.HistoryView._process_entries')
    @mock.patch('pulp.server.webservices.views.repositories.HistoryView.get_history_func')
    @mock.patch('pulp.server.webservices.views.repositories.HistoryView._get_and_validate_params')
    def test_get(self, mock_get_and_validate, mock_get_history, mock_process, mock_resp):
        """
        Ensure that params are retrieved, validated, and used to retrieve history.
        """
        history = HistoryView()
        mock_request = mock.MagicMock()
        mock_get_and_validate.return_value = ('mock_start', 'mock_end', 'mock_sort', 'mock_limit')
        result = history.get(mock_request)
        mock_get_and_validate.assert_called_once_with(mock_request.GET)

        mock_get_history.assert_called_once_with('mock_start', 'mock_end')
        mock_process.assert_called_once_with(mock_get_history(), 'mock_sort', 'mock_limit')
        mock_resp.assert_called_once_with(mock_process.return_value)
        self.assertTrue(result is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch(
        'pulp.server.webservices.views.repositories.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.repositories.HistoryView._process_entries')
    @mock.patch('pulp.server.webservices.views.repositories.HistoryView.get_history_func')
    @mock.patch('pulp.server.webservices.views.repositories.HistoryView._get_and_validate_params')
    def test_get_no_sort(self, mock_validate, mock_get_history, mock_process, mock_resp):
        """
        Ensure that if sort is not passed, it defaults to descending.
        """
        history = HistoryView()
        mock_request = mock.MagicMock()
        mock_validate.return_value = ('mock_start', 'mock_end', None, 'mock_limit')
        result = history.get(mock_request)
        mock_validate.assert_called_once_with(mock_request.GET)
        mock_get_history.assert_called_once_with('mock_start', 'mock_end')
        mock_process.assert_called_once_with(mock_get_history.return_value,
                                             constants.SORT_DESCENDING, 'mock_limit')
        mock_resp.assert_called_once_with(mock_process.return_value)
        self.assertTrue(result is mock_resp.return_value)

    def test_process_entries(self):
        """
        Ensure that results are limited and sorted.
        """
        mock_cursor = mock.MagicMock()
        history = HistoryView()
        result = history._process_entries(mock_cursor, constants.SORT_DESCENDING, 3)
        mock_cursor.sort.assert_called_once_with('_id', direction=-1)
        mock_cursor.limit.assert_called_once_with(3)
        self.assertTrue(isinstance(result, list))

    def test_get_and_validiate_params_valid_empty(self):
        """
        Test getting params from an empty dictionary.
        """
        get_params = {}
        history = HistoryView()
        args = history._get_and_validate_params(get_params)
        self.assertEqual(args, (None, None, None, None))

    @mock.patch('pulp.server.webservices.views.repositories.dateutils.parse_iso8601_datetime')
    def test_get_and_validate_params_valid_all_values(self, mock_parse_date):
        """
        Test getting and validating all allowed params.
        """
        get_params = {
            constants.REPO_HISTORY_FILTER_SORT: constants.SORT_ASCENDING,
            constants.REPO_HISTORY_FILTER_START_DATE: 'mock_start',
            constants.REPO_HISTORY_FILTER_END_DATE: 'mock_end',
            constants.REPO_HISTORY_FILTER_LIMIT: '3'
        }
        history = HistoryView()
        args = history._get_and_validate_params(get_params)
        mock_parse_date.assert_has_calls([mock.call('mock_start'), mock.call('mock_end')])
        self.assertEqual(args, ('mock_start', 'mock_end', 'ascending', 3))

    @mock.patch('pulp.server.webservices.views.repositories.dateutils.parse_iso8601_datetime')
    def test_validate_get_params_invalid_all_values(self, mock_parse_date):
        """
        Test that each value is added to the list of invalid values.
        """
        get_params = {
            constants.REPO_HISTORY_FILTER_SORT: 'mock_sort',
            constants.REPO_HISTORY_FILTER_START_DATE: 'mock_start',
            constants.REPO_HISTORY_FILTER_END_DATE: 'mock_end',
            constants.REPO_HISTORY_FILTER_LIMIT: 'three'
        }
        history = HistoryView()
        mock_parse_date.side_effect = ValueError
        try:
            history._get_and_validate_params(get_params)
        except exceptions.InvalidValue, response:
            pass
        else:
            raise AssertionError('InvalidValue should be raised when params are invalid.')

        self.assertEqual(response.property_names, ['limit', 'sort', 'start_date', 'end_date'])
        mock_parse_date.assert_has_calls([mock.call('mock_start'), mock.call('mock_end')])

    def test_get_and_validate_limit_less_than_one(self):
        """
        Limit is invalid even if it as an integer if it is below 1.
        """
        get_params = {constants.REPO_HISTORY_FILTER_LIMIT: '-1'}
        history = HistoryView()
        try:
            history._get_and_validate_params(get_params)
        except exceptions.InvalidValue, response:
            pass
        else:
            raise AssertionError('InvalidValue should be raised when params are invalid.')
        self.assertEqual(response.property_names, ['limit'])

    def test_not_implemented_get_history_func(self):
        """
        If a new history function does not define get_history_func, raise NotImplementedError.
        """
        view = HistoryView()
        self.assertRaises(NotImplementedError, view.get_history_func)


class TestRepoSyncHistory(unittest.TestCase):
    """
    Tests for RepoSyncHistory.
    """

    def test_get_history(self):
        """
        Ensure that RepoSyncHistory is configured correctly.
        """
        repo_sync_history = RepoSyncHistory()
        self.assertTrue(repo_sync_history.get_history_func is repo_controller.sync_history)


class TestRepoPublishHistory(unittest.TestCase):
    """
    Tests for RepoPublishHistory.
    """
    def test_get_history(self):
        """
        Ensure that RepoPublishHistory is configured correctly.
        """
        repo_publish_history = RepoPublishHistory()
        self.assertTrue(repo_publish_history.get_history_func is repo_controller.publish_history)


class TestRepoSync(unittest.TestCase):
    """
    Tests for RepoSync.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    @mock.patch('pulp.server.webservices.views.repositories.repo_controller')
    def test_post_sync_repo(self, mock_repo_ctrl, mock_repo_qs):
        """
        Test that a repo sync task is dispatched.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'override_config': 'mock_conf'})

        sync_repo = RepoSync()
        try:
            sync_repo.post(mock_request, 'mock_repo')
        except exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raised for sync task')

        mock_repo_qs.get_repo_or_missing_resource.assert_called_once_with('mock_repo')
        mock_repo_ctrl.queue_sync_with_auto_publish.assert_called_once_with(
            'mock_repo', 'mock_conf'
        )
        self.assertEqual(response.http_status_code, 202)


class TestRepoPublish(unittest.TestCase):
    """
    Tests for RepoPublish.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.repositories.repo_controller')
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_post_publish_repo(self, mock_repo_qs, mock_repo_ctrl):
        """
        Test that a repo publish task is dispatched.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'override_config': 'mock_conf', 'id': 'mock_dist'})

        publish_repo = RepoPublish()
        try:
            publish_repo.post(mock_request, 'mock_repo')
        except exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raised for publish task')

        mock_repo_qs.get_repo_or_missing_resource.assert_called_once_with('mock_repo')
        mock_repo_ctrl.queue_publish.assert_called_once_with('mock_repo', 'mock_dist', 'mock_conf')
        self.assertEqual(response.http_status_code, 202)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.repositories.manager_factory')
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_post_publish_repo_missing_distributor(self, mock_repo_qs, mock_factory):
        """
        Test that a repo publish requires distributor id in body.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'not_id': 'will_fail'})

        publish_repo = RepoPublish()
        try:
            publish_repo.post(mock_request, 'mock_repo')
        except exceptions.MissingValue, response:
            pass
        else:
            raise AssertionError('MissingValue should be raised if id for distributor not passed')

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0016)


class TestRepoDownload(unittest.TestCase):
    """Tests for RepoDownload."""

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.repositories.repo_controller')
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_post_download_repo(self, mock_repo_qs, mock_repo_controller):
        """Test that a repo download task is dispatched."""
        # Setup
        download_repo = RepoDownload()

        # Tests
        with self.assertRaises(exceptions.OperationPostponed) as cm:
            download_repo.post(mock.Mock(body=None), 'mock_repo')
        self.assertEqual(cm.exception.http_status_code, 202)
        mock_repo_qs.get_repo_or_missing_resource.assert_called_once_with('mock_repo')
        mock_repo_controller.queue_download_repo.assert_called_once_with(
            'mock_repo',
            verify_all_units=False
        )

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.repositories.repo_controller')
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_post_download_repo_verify(self, mock_repo_qs, mock_repo_controller):
        """Test that a repo download task is dispatched with verify_all_units."""
        # Setup
        mock_request = mock.Mock(body=json.dumps({'verify_all_units': True}))
        download_repo = RepoDownload()

        # Tests
        with self.assertRaises(exceptions.OperationPostponed) as cm:
            download_repo.post(mock_request, 'mock_repo')
        self.assertEqual(cm.exception.http_status_code, 202)
        mock_repo_qs.get_repo_or_missing_resource.assert_called_once_with('mock_repo')
        mock_repo_controller.queue_download_repo.assert_called_once_with(
            'mock_repo',
            verify_all_units=True
        )

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.repositories.repo_controller')
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_post_download_repo_bad_request(self, mock_repo_qs, mock_repo_controller):
        """Test that a repo download call with a bad request results in a 400."""
        # Setup
        mock_request = mock.Mock(body=json.dumps({'verify_all_units': 'please'}))
        download_repo = RepoDownload()

        # Tests
        with self.assertRaises(exceptions.PulpCodedValidationException) as cm:
            download_repo.post(mock_request, 'mock_repo')
        self.assertEqual(error_codes.PLP1010, cm.exception.error_code)
        self.assertEqual(cm.exception.http_status_code, 400)
        mock_repo_qs.get_repo_or_missing_resource.assert_called_once_with('mock_repo')
        self.assertEqual(0, mock_repo_controller.queue_download_repo.call_count)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_EXECUTE())
    @mock.patch('pulp.server.webservices.views.repositories.repo_controller')
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_post_download_repo_missing_repo(self, mock_repo_qs, mock_repo_controller):
        """Test that a repo download call with an invalid repo id results in a 404."""
        # Setup
        mock_repo_qs.get_repo_or_missing_resource.side_effect = exceptions.MissingResource
        download_repo = RepoDownload()

        # Tests
        with self.assertRaises(exceptions.MissingResource) as cm:
            download_repo.post(mock.Mock(body=None), 'mock_repo')
        self.assertEqual(cm.exception.http_status_code, 404)
        mock_repo_qs.get_repo_or_missing_resource.assert_called_once_with('mock_repo')
        self.assertEqual(0, mock_repo_controller.queue_download_repo.call_count)


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
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_post_minimal(self, mock_repo_qs, mock_crit, mock_associate, mock_tags):
        """
        Test that a task is created with the minimal body params.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'source_repo_id': 'mock_source_repo'})
        repo_associate = RepoAssociate()

        try:
            repo_associate.post(mock_request, 'mock_dest_repo')
        except exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raise for an associate task')

        task_tags = [mock_tags.resource_tag(), mock_tags.resource_tag(), mock_tags.action_tag()]
        mock_associate.apply_async_with_reservation_list.assert_called_once_with(
            [(mock_tags.RESOURCE_REPOSITORY_TYPE, 'mock_dest_repo')],
            ['mock_source_repo', 'mock_dest_repo'],
            {'criteria': mock_crit.return_value.to_dict.return_value,
             'import_config_override': None}, tags=task_tags
        )
        self.assertEqual(response.http_status_code, 202)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_post_missing_source_repo(self, mock_repo_qs):
        """
        Test that a 400 is thrown when the source repo is not passed.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'not_source_repo_id': 'mock_source_repo'})
        repo_associate = RepoAssociate()

        try:
            repo_associate.post(mock_request, 'mock_dest_repo')
        except exceptions.MissingValue, response:
            pass
        else:
            raise AssertionError('MissingValue should be raised if source_repo_id not in body')

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0016)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_post_invalid_source_repo(self, mock_repo_qs):
        """
        Test that a 400 is thrown when the source repo does not exist.
        """

        source_repo = 'mock_source_repo'

        def mock_get_repo(repo_id):
            """
            Do not raise MissingResource for dest_repo_id, just source_repo_id.
            """
            if repo_id == source_repo:
                raise exceptions.MissingResource
            return

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'source_repo_id': source_repo})
        mock_repo_qs.get_repo_or_missing_resource.side_effect = mock_get_repo
        repo_associate = RepoAssociate()

        try:
            repo_associate.post(mock_request, 'mock_dest_repo')
        except exceptions.InvalidValue, response:
            pass
        else:
            raise AssertionError('InvalidValue should be raised if source_repo_id does not exist')

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0015)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_UPDATE())
    @mock.patch('pulp.server.webservices.views.repositories.UnitAssociationCriteria')
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_post_unparsable_criteria(self, mock_repo_qs, mock_crit):
        """
        Test that a helpful exception is raised when criteria passed in body is unparsable.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({'source_repo_id': 'mock_repo', 'criteria': 'mock_crit'})
        repo_associate = RepoAssociate()
        mock_crit.from_client_input.side_effect = exceptions.InvalidValue("Fake value")

        try:
            repo_associate.post(mock_request, 'mock_dest_repo')
        except exceptions.InvalidValue, response:
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
    @mock.patch('pulp.server.webservices.views.repositories.model.Repository.objects')
    def test_post_minimal(self, mock_repo_qs, mock_factory, mock_crit, mock_unassociate, mock_tags):
        """
        Test that a task is created with the minimal body params.
        """

        mock_request = mock.MagicMock()
        mock_request.body = json.dumps({})
        repo_unassociate = RepoUnassociate()

        try:
            repo_unassociate.post(mock_request, 'mock_repo')
        except exceptions.OperationPostponed, response:
            pass
        else:
            raise AssertionError('OperationPostponed should be raise for an unassociate task')

        task_tags = [mock_tags.resource_tag(), mock_tags.action_tag()]
        mock_unassociate.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE, 'mock_repo',
            ['mock_repo', mock_crit.return_value.to_dict.return_value], tags=task_tags
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
        mock_crit.from_client_input.side_effect = exceptions.InvalidValue("Fake value")

        try:
            repo_unassociate.post(mock_request, 'mock_repo')
        except exceptions.InvalidValue, response:
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
        except exceptions.OperationPostponed, response:
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
        except exceptions.MissingValue, response:
            pass
        else:
            raise AssertionError('MissingValue should be raised when missing required body params.')

        self.assertEqual(response.http_status_code, 400)
        self.assertTrue(response.error_code is error_codes.PLP0016)
