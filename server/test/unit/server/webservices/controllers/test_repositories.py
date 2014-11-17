"""
This module contains tests for the pulp.server.webservices.controllers.repositories module.
"""
from pprint import pformat
import copy
import datetime
import httplib
import re
import traceback
import unittest
import uuid

from bson import ObjectId
from celery.result import AsyncResult
import mock

from .... import base
from pulp.common import dateutils, tags
from pulp.devel import dummy_plugins, mock_plugins
from pulp.devel.unit.server.base import PulpWebservicesTests
from pulp.devel.unit.util import compare_dict, assert_body_matches_async_task
from pulp.plugins.loader import api as plugin_api
from pulp.server.async.tasks import TaskResult
from pulp.server.auth import authorization
from pulp.server.db.connection import PulpCollection
from pulp.server.db.model import criteria
from pulp.server.db.model.consumer import UnitProfile, Consumer, Bind, RepoProfileApplicability
from pulp.server.db.model.criteria import UnitAssociationCriteria, Criteria
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.db.model.repository import (Repo, RepoDistributor, RepoImporter,
                                             RepoPublishResult, RepoSyncResult)
from pulp.server.db.model.resources import Worker
from pulp.server.exceptions import MissingResource, OperationPostponed, PulpException
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.repo.distributor import RepoDistributorManager
from pulp.server.managers.repo.importer import RepoImporterManager
from pulp.server.webservices.controllers import repositories


class ConvertRepoDatesToStringsTests(unittest.TestCase):

    def test_last_unit_added_and_removed(self):
        dt = datetime.datetime.utcnow()
        repo = {'id': 'dummy-1', 'display_name': 'dummy',
                'last_unit_added': dt,
                'last_unit_removed': dt}
        string_date = dateutils.format_iso8601_datetime(
            dateutils.to_utc_datetime(dt, no_tz_equals_local_tz=False))
        repositories._convert_repo_dates_to_strings(repo)
        self.assertEquals(repo['last_unit_added'], string_date)
        self.assertEquals(repo['last_unit_removed'], string_date)

    def test_process_repos_calls_serialize_last_unit_added_and_removed(self):
        repo = {'id': 'dummy-1', 'display_name': 'dummy',
                'last_unit_added': None,
                'last_unit_removed': None}
        repositories._convert_repo_dates_to_strings(repo)
        self.assertEquals(repo['last_unit_added'], None)
        self.assertEquals(repo['last_unit_removed'], None)


class RepoControllersTests(base.PulpWebserviceTests):
    def setUp(self):
        super(RepoControllersTests, self).setUp()
        self.repo_manager = manager_factory.repo_manager()

    def clean(self):
        super(RepoControllersTests, self).clean()
        Repo.get_collection().remove(safe=True)


class ReservedResourceApplyAsync(object):
    """
    This object allows us to mock the return value of _reserve_resource.apply_async.get().
    """

    def get(self):
        return 'some_queue'


class RepoImportUploadTests(RepoControllersTests):
    """
    Test the RepoImportUpload class.
    """
    URL = '/v2/repositories/%s/actions/import_upload/'

    @mock.patch('celery.Task.apply_async')
    @mock.patch('pulp.server.async.tasks.uuid', autospec=True)
    @mock.patch('pulp.server.async.tasks.resources.get_worker_for_reservation')
    @mock.patch('pulp.server.managers.content.upload.ContentUploadManager.import_uploaded_unit')
    def test_POST_returns_report(self, import_uploaded_unit, mock_get_worker_for_reservation,
                                 mock_uuid, mock_apply_async):
        """
        Assert that the POST() method returns the appropriate report dictionary, based on the return
        value of the import_uploaded_unit() method.
        """
        success_flag = True
        summary = 'A summary'
        details = 'Some details'
        upload_report = {'success_flag': success_flag, 'summary': summary, 'details': details}
        import_uploaded_unit.return_value = upload_report
        uuid_list = [uuid.uuid4() for i in range(10)]
        mock_uuid.uuid4.side_effect = copy.deepcopy(uuid_list)
        expected_async_result = AsyncResult(str(uuid_list[0]))
        mock_get_worker_for_reservation.return_value = Worker('some_queue', datetime.datetime.now())
        params = {'upload_id': 'upload_id', 'unit_type_id': 'unit_type_id', 'unit_key': 'unit_key'}

        status, body = self.post(self.URL % 'repo_id', params)
        self.assertEqual(202, status)
        assert_body_matches_async_task(body, expected_async_result)
        expected_args = mock_apply_async.call_args[0][0]
        self.assertTrue('repo_id' in expected_args)
        self.assertTrue('unit_type_id' in expected_args)
        self.assertTrue('unit_key' in expected_args)
        self.assertTrue('upload_id' in expected_args)


class RepoSearchTests(RepoControllersTests):
    @mock.patch.object(repositories.RepoSearch, 'params')
    @mock.patch.object(PulpCollection, 'query')
    def test_basic_search(self, mock_query, mock_params):
        mock_params.return_value = {
            'criteria': {}
        }
        ret = self.post('/v2/repositories/search/')
        self.assertEqual(ret[0], 200)
        self.assertEqual(mock_query.call_count, 1)
        query_arg = mock_query.call_args[0][0]
        self.assertTrue(isinstance(query_arg, criteria.Criteria))
        # one call each for criteria, importers, and distributors
        self.assertEqual(mock_params.call_count, 3)

    @mock.patch.object(PulpCollection, 'query')
    @mock.patch('pulp.server.db.model.criteria.Criteria.from_client_input')
    def test_get_details(self, mock_from_client, mock_query):
        status, body = self.get('/v2/repositories/search/?details=1&limit=2')
        self.assertEqual(status, 200)
        self.assertEquals(mock_from_client.call_count, 1)

        # make sure the non-criteria arguments aren't passed to the criteria
        # constructor
        criteria_args = mock_from_client.call_args[0][0]
        self.assertTrue('limit' in criteria_args)
        self.assertFalse('details' in criteria_args)
        self.assertFalse('importers' in criteria_args)

    @mock.patch.object(repositories.RepoSearch, 'params')
    @mock.patch.object(PulpCollection, 'query')
    def test_return_value(self, mock_query, mock_params):
        """
        make sure the method returns the same stuff that is returned by query()
        """
        mock_params.return_value = {
            'criteria': {}
        }
        mock_query.return_value = [
            {'id': 'repo-1'},
            {'id': 'repo-2'},
        ]
        ret = self.post('/v2/repositories/search/')
        self.assertEqual(ret[0], 200)
        self.assertEqual(ret[1], mock_query.return_value)

    @mock.patch('pulp.server.webservices.controllers.repositories.RepoCollection._process_repos')
    @mock.patch.object(repositories.RepoSearch, 'params')
    @mock.patch.object(PulpCollection, 'query')
    def test_search_with_importers(self, mock_query, mock_params, mock_process_repos):
        mock_params.return_value = {
            'criteria': {},
            'importers': 1,
            'distributors': 0
        }
        ret = self.post('/v2/repositories/search/')
        self.assertEqual(ret[0], 200)
        mock_process_repos.assert_called_once_with([], 1, 0)

    @mock.patch('pulp.server.webservices.controllers.repositories.RepoCollection._process_repos')
    @mock.patch.object(repositories.RepoSearch, 'params')
    @mock.patch.object(PulpCollection, 'query')
    def test_search_with_distributors(self, mock_query, mock_params, mock_process_repos):
        mock_params.return_value = {
            'criteria': {},
            'importers': 0,
            'distributors': 1
        }
        ret = self.post('/v2/repositories/search/')
        self.assertEqual(ret[0], 200)
        mock_process_repos.assert_called_once_with([], 0, 1)

    @mock.patch('pulp.server.webservices.controllers.repositories.RepoCollection._process_repos')
    @mock.patch.object(repositories.RepoSearch, 'params')
    @mock.patch.object(PulpCollection, 'query')
    def test_search_with_both(self, mock_query, mock_params, mock_process_repos):
        mock_params.return_value = {
            'criteria': {},
            'importers': 1,
            'distributors': 1
        }
        ret = self.post('/v2/repositories/search/')
        self.assertEqual(ret[0], 200)
        mock_process_repos.assert_called_once_with([], 1, 1)

    @mock.patch.object(repositories.RepoSearch, 'params', return_value={})
    def test_require_criteria(self, mock_params):
        """
        make sure this raises a MissingValue exception if 'criteria' is not
        passed as a parameter.
        """
        ret = self.post('/v2/repositories/search/')
        self.assertEqual(ret[0], 400)
        value = ret[1]
        self.assertTrue(isinstance(value, dict))
        self.assertTrue('missing_property_names' in value)
        self.assertEqual(value['missing_property_names'], [u'criteria'])

    @mock.patch.object(PulpCollection, 'query')
    def test_get(self, mock_query):
        """
        Make sure that we can do a criteria-based search with GET. Ensures that
        a proper Criteria object is created and passed to the collection's
        query method.
        """
        status, body = self.get(
            '/v2/repositories/search/?field=id&field=display_name&limit=20')
        self.assertEqual(status, 200)
        self.assertEqual(mock_query.call_count, 1)
        generated_criteria = mock_query.call_args[0][0]
        self.assertTrue(isinstance(generated_criteria, criteria.Criteria))
        self.assertEqual(len(generated_criteria.fields), 2)
        self.assertTrue('id' in generated_criteria.fields)
        self.assertTrue('display_name' in generated_criteria.fields)
        self.assertEqual(generated_criteria.limit, 20)
        self.assertTrue(generated_criteria.skip is None)


class RepoCollectionTests(RepoControllersTests):
    def test_get(self):
        """
        Tests retrieving a list of repositories.
        """

        # Setup
        self.repo_manager.create_repo('dummy-1')
        self.repo_manager.create_repo('dummy-2')

        # Test
        status, body = self.get('/v2/repositories/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(2, len(body))
        self.assertTrue('importers' not in body[0])
        self.assertTrue('_href' in body[0])
        self.assertTrue(body[0]['_href'].find('repositories/dummy-') >= 0)

    def test_get_no_repos(self):
        """
        Tests that an empty list is returned when no repos are present.
        """

        # Test
        status, body = self.get('/v2/repositories/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(0, len(body))

    def test_merge_related_objects(self):
        REPOS = [{'id': 'dummy-1', 'display_name': 'dummy'}]
        IMPORTERS = [{'repo_id': 'dummy-1', 'id': 'importer-1', 'importer_type_id': 1}]

        # mock out these managers so we don't hit the DB
        mock_importer_manager = mock.MagicMock()
        mock_importer_manager.find_by_repo_list.return_value = IMPORTERS
        ret = repositories._merge_related_objects('importers', mock_importer_manager, REPOS)

        self.assertTrue('importers' in ret[0])
        self.assertEqual(len(ret[0]['importers']), 1)
        self.assertEqual(ret[0]['importers'][0]['id'], IMPORTERS[0]['id'])

    @mock.patch('pulp.server.webservices.serialization.link.search_safe_link_obj')
    def test_process_repos_calls_serialize(self, mock_link_obj):
        mock_link_obj.return_value = {}
        REPOS = [{'id': 'dummy-1', 'display_name': 'dummy'}]
        repositories.RepoCollection._process_repos(REPOS)
        mock_link_obj.assert_called_once_with(REPOS[0]['id'])

    @mock.patch('pulp.server.webservices.serialization.link.search_safe_link_obj')
    def test_process_repos_calls_serialize_last_unit_added_and_removed(self, mock_link_obj):
        mock_link_obj.return_value = {}
        dt = datetime.datetime.utcnow()
        REPOS = [{'id': 'dummy-1', 'display_name': 'dummy',
                  'last_unit_added': dt,
                  'last_unit_removed': dt}]
        string_date = dateutils.format_iso8601_datetime(
            dateutils.to_utc_datetime(dt, no_tz_equals_local_tz=False))
        repositories.RepoCollection._process_repos(REPOS)
        self.assertEquals(REPOS[0]['last_unit_added'], string_date)
        self.assertEquals(REPOS[0]['last_unit_removed'], string_date)

        mock_link_obj.assert_called_once_with(REPOS[0]['id'])

    @mock.patch('pulp.server.webservices.serialization.link.search_safe_link_obj',
                return_value={})
    def test_process_repos_without_details(self, mock_link_obj):
        REPOS = [{'id': 'dummy-1', 'display_name': 'dummy'}]
        ret = repositories.RepoCollection._process_repos(REPOS)
        self.assertTrue('importers' not in ret[0])
        self.assertTrue('distributors' not in ret[0])

    @mock.patch('pulp.server.webservices.serialization.link.search_safe_link_obj',
                return_value={})
    @mock.patch.object(repositories, '_merge_related_objects')
    def test_process_repos_with_importers(self, mock_merge_related_objects,
                                          mock_link_obj):
        REPOS = [{'id': 'dummy-1', 'display_name': 'dummy'}]
        repositories.RepoCollection._process_repos(REPOS, importers=True)
        self.assertEqual(mock_merge_related_objects.call_count, 1)
        self.assertEqual(mock_merge_related_objects.call_args[0][0], 'importers')
        self.assertTrue(isinstance(mock_merge_related_objects.call_args[0][1],
                                   RepoImporterManager))

    @mock.patch('pulp.server.webservices.serialization.link.search_safe_link_obj',
                return_value={})
    @mock.patch.object(repositories, '_merge_related_objects')
    def test_process_repos_with_distributors(self, mock_merge_related_objects,
                                             mock_link_obj):
        REPOS = [{'id': 'dummy-1', 'display_name': 'dummy'}]
        repositories.RepoCollection._process_repos(REPOS, distributors=True)
        self.assertEqual(mock_merge_related_objects.call_count, 1)
        self.assertEqual(
            mock_merge_related_objects.call_args[0][0], 'distributors')
        self.assertTrue(isinstance(mock_merge_related_objects.call_args[0][1],
                                   RepoDistributorManager))

    @mock.patch('pulp.server.managers.repo.query.RepoQueryManager.find_all')
    @mock.patch.object(repositories, '_merge_related_objects')
    def test_get_details(self, mock_merge_method, mock_find_all):
        """
        Make sure the GET method calls _merge_related_objects
        """
        mock_merge_method.return_value = [Repo('repo-1', 'Repo 1')]
        mock_find_all.return_value = [Repo('repo-1', 'Repo 1')]
        status, body = self.get('/v2/repositories/?details=1')
        self.assertEqual(200, status)
        self.assertTrue(mock_merge_method.called)

    @mock.patch('pulp.server.managers.repo.query.RepoQueryManager.find_all')
    @mock.patch.object(repositories, '_merge_related_objects')
    def test_get_without_details(
            self, mock_merge_method, mock_find_all):
        """
        Make sure the GET method does not call _merge_related_objects
        """
        mock_find_all.return_value = [Repo('repo-1', 'Repo 1')]
        status, body = self.get('/v2/repositories/')
        self.assertEqual(200, status)
        self.assertFalse(mock_merge_method.called)

    def test_post(self):
        """
        Tests using post to create a repo.
        """

        # Setup
        body = {
            'id': 'repo-1',
            'display_name': 'Repo 1',
            'description': 'Repository',
        }

        # Test
        status, body = self.post('/v2/repositories/', params=body)

        # Verify
        self.assertEqual(201, status)

        self.assertEqual(body['id'], 'repo-1')

        repo = Repo.get_collection().find_one({'id': 'repo-1'})
        self.assertTrue(repo is not None)

    def test_post_bad_data(self):
        """
        Tests a create repo with invalid data.
        """

        # Setup
        body = {'id': 'HA! This looks so totally invalid, but we do allow this ID now :)'}

        # Test
        status, body = self.post('/v2/repositories/', params=body)

        # Verify
        self.assertEqual(400, status)

    def test_post_conflict(self):
        """
        Tests creating a repo with an existing ID.
        """

        # Setup
        self.repo_manager.create_repo('existing')

        body = {'id': 'existing'}

        # Test
        status, body = self.post('/v2/repositories/', params=body)

        # Verify
        self.assertEqual(409, status)


class RepoResourceTestsNoWSGI(PulpWebservicesTests):
    """
    Tests that have been converted to not require a running web.py stack
    """

    @mock.patch('pulp.server.managers.factory.repo_query_manager')
    @mock.patch('pulp.server.tasks.repository.delete', autospec=True)
    def test_delete(self, mock_delete_task, mock_manager_factory):
        repo_distributor = repositories.RepoResource()

        async_task = AsyncResult('foo-id')
        mock_delete_task.apply_async_with_reservation.return_value = async_task
        self.assertRaises(OperationPostponed, repo_distributor.DELETE, "foo-repo")

        # Validate that the check was made to ensure the repo exists
        mock_manager_factory.return_value.get_repository.assert_called_once_with('foo-repo')

        # validate that the task was called with the appropriate tags
        task_tags = ['pulp:repository:foo-repo',
                     'pulp:action:delete']
        mock_delete_task.apply_async_with_reservation. \
            assert_called_once_with(tags.RESOURCE_REPOSITORY_TYPE,
                                    'foo-repo', ['foo-repo', ], tags=task_tags)
        # validate the permissions
        self.validate_auth(authorization.DELETE)

        try:
            repo_distributor.DELETE("foo-repo")
        except OperationPostponed, op:
            self.assertEquals(op.call_report, async_task)

    @mock.patch('pulp.server.managers.factory.repo_query_manager')
    @mock.patch('pulp.server.managers.factory.repo_manager', autospec=True)
    def test_put(self, mock_repo_manager, mock_manager_factory):
        repo_distributor = repositories.RepoResource()
        params = mock.Mock(return_value={
            'delta': 'foo',
            'importer_config': 'bar',
            'distributor_configs': 'baz'
        })
        repo_distributor.params = params
        mock_update_task = mock_repo_manager.return_value.update_repo_and_plugins
        working_result = TaskResult({'repo_id': 'repo-foo'}, error=PulpException("foo"))
        mock_update_task.return_value = working_result
        repo_distributor.ok = mock.Mock()
        repo_distributor.PUT("foo-repo")
        mock_update_task.assert_called_once_with('foo-repo', 'foo', 'bar', 'baz')

        working_result.return_value['_href'] = self.get_mock_uri_path()
        compare_dict(repo_distributor.ok.call_args_list[0][0][0],
                     working_result.serialize())

        self.validate_auth(authorization.UPDATE)

    @mock.patch('pulp.server.managers.factory.repo_query_manager')
    @mock.patch('pulp.server.managers.factory.repo_manager', autospec=True)
    def test_put_with_spawned_raises_operation_postponed(self, mock_repo_manager,
                                                         mock_manager_factory):
        repo_distributor = repositories.RepoResource()
        params = mock.Mock(return_value={
            'delta': 'foo',
            'importer_config': 'bar',
            'distributor_configs': 'baz'
        })
        repo_distributor.params = params
        mock_update_task = mock_repo_manager.return_value.update_repo_and_plugins
        working_result = TaskResult({'repo_id': 'repo-foo'}, error=PulpException("foo"),
                                    spawned_tasks=[{'task_id': 'foo'}])
        mock_update_task.return_value = working_result
        repo_distributor.ok = mock.Mock()

        self.assertRaises(OperationPostponed, repo_distributor.PUT, "foo-repo")
        mock_update_task.assert_called_once_with('foo-repo', 'foo', 'bar', 'baz')
        self.validate_auth(authorization.UPDATE)


class RepoResourceTests(RepoControllersTests):
    def test_get(self):
        """
        Tests retrieving a valid repo.
        """

        # Setup
        self.repo_manager.create_repo('repo-1')

        # Test
        status, body = self.get('/v2/repositories/repo-1/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual('repo-1', body['id'])
        self.assertTrue('_href' in body)
        self.assertTrue(body['_href'].endswith('repositories/repo-1/'))

    @mock.patch('pulp.server.managers.repo.query.RepoQueryManager.find_by_id')
    @mock.patch.object(repositories, '_merge_related_objects')
    def test_get_details(self, mock_merge_method, mock_find_by_id):
        """
        Make sure the GET method calls _merge_related_objects
        """
        repo = Repo('repo-1', 'Repo 1')
        mock_merge_method.return_value = [repo]
        mock_find_by_id.return_value = repo
        status, body = self.get('/v2/repositories/repo-1/?details=1')
        self.assertEqual(200, status)
        self.assertEqual(mock_merge_method.call_count, 2)

    @mock.patch('pulp.server.managers.repo.query.RepoQueryManager.find_by_id')
    @mock.patch.object(repositories, '_merge_related_objects')
    def test_get_without_details(self, mock_merge_method, mock_find_by_id):
        """
        Make sure the GET method does not call _merge_related_objects
        """
        mock_find_by_id.return_value = Repo('repo-1', 'Repo 1')
        status, body = self.get('/v2/repositories/repo-1/')
        self.assertEqual(200, status)
        self.assertEqual(mock_merge_method.call_count, 0)

    @mock.patch('pulp.server.managers.repo.query.RepoQueryManager.find_by_id')
    @mock.patch.object(repositories, '_merge_related_objects')
    def test_get_with_importers(self, mock_merge_method, mock_find_by_id):
        """
        Make sure the GET method calls _merge_related_objects
        """
        repo = Repo('repo-1', 'Repo 1')
        mock_merge_method.return_value = [repo]
        mock_find_by_id.return_value = repo
        status, body = self.get('/v2/repositories/repo-1/?importers=1')
        self.assertEqual(200, status)
        self.assertEqual(mock_merge_method.call_count, 1)
        call_args = mock_merge_method.call_args[0]
        self.assertEqual(call_args[0], 'importers')
        self.assertTrue(hasattr(call_args[1], 'find_by_repo_list'))

    @mock.patch('pulp.server.managers.repo.query.RepoQueryManager.find_by_id')
    @mock.patch.object(repositories, '_merge_related_objects')
    def test_get_with_distributors(self, mock_merge_method, mock_find_by_id):
        """
        Make sure the GET method calls _merge_related_objects
        """
        repo = Repo('repo-1', 'Repo 1')
        mock_merge_method.return_value = [repo]
        mock_find_by_id.return_value = repo
        status, body = self.get('/v2/repositories/repo-1/?distributors=1')
        self.assertEqual(200, status)
        self.assertEqual(mock_merge_method.call_count, 1)
        call_args = mock_merge_method.call_args[0]
        self.assertEqual(call_args[0], 'distributors')
        self.assertTrue(hasattr(call_args[1], 'find_by_repo_list'))

    def test_get_missing_repo(self):
        """
        Tests that a 404 is returned when getting a repo that doesn't exist.
        """

        # Test
        status, body = self.get('/v2/repositories/foo/')

        # Verify
        self.assertEqual(404, status)


class RepoPluginsTests(RepoControllersTests):
    def setUp(self):
        super(RepoPluginsTests, self).setUp()

        plugin_api._create_manager()
        dummy_plugins.install()

        self.importer_manager = manager_factory.repo_importer_manager()
        self.distributor_manager = manager_factory.repo_distributor_manager()
        self.sync_manager = manager_factory.repo_sync_manager()
        self.publish_manager = manager_factory.repo_publish_manager()

    def tearDown(self):
        super(RepoPluginsTests, self).tearDown()
        dummy_plugins.reset()

    def clean(self):
        super(RepoPluginsTests, self).clean()
        RepoImporter.get_collection().remove(safe=True)
        RepoDistributor.get_collection().remove(safe=True)
        RepoSyncResult.get_collection().remove(safe=True)
        RepoPublishResult.get_collection().remove(safe=True)


class RepoImportersTests(RepoPluginsTests):
    def test_get(self):
        """
        Tests getting the list of importers for a valid repo with importers.
        """
        # Setup
        self.repo_manager.create_repo('stuffing')
        self.importer_manager.set_importer('stuffing', 'dummy-importer', {})
        # Test
        status, body = self.get('/v2/repositories/stuffing/importers/')
        # Verify
        self.assertEqual(200, status)
        self.assertEqual(1, len(body))

    def test_get_no_importers(self):
        """
        Tests an empty list is returned for a repo with no importers.
        """
        # Setup
        self.repo_manager.create_repo('potatoes')
        # Test
        status, body = self.get('/v2/repositories/potatoes/importers/')
        # Verify
        self.assertEqual(200, status)
        self.assertEqual(0, len(body))

    def test_get_missing_repo(self):
        """
        Tests getting importers for a repo that doesn't exist.
        """
        # Test
        status, body = self.get('/v2/repositories/not_there/importers/')
        # Verify
        self.assertEqual(404, status)

    @mock.patch('celery.Task.apply_async')
    @mock.patch('pulp.server.async.tasks.uuid', autospec=True)
    @mock.patch('pulp.server.async.tasks.resources.get_worker_for_reservation')
    def test_post(self, mock_get_worker_for_reservation, mock_uuid, mock_apply_async):
        """
        Tests adding an importer to a repo.
        """
        # Setup
        self.repo_manager.create_repo('gravy')
        uuid_list = [uuid.uuid4() for i in range(10)]
        mock_uuid.uuid4.side_effect = copy.deepcopy(uuid_list)
        expected_async_result = AsyncResult(str(uuid_list[0]))
        mock_get_worker_for_reservation.return_value = Worker('some_queue', datetime.datetime.now())

        # Test
        req_body = {
            'importer_type_id': 'dummy-importer',
            'importer_config': {'foo': 'bar'},
        }
        status, body = self.post('/v2/repositories/gravy/importers/', params=req_body)

        # Verify
        self.assertEqual(202, status)
        assert_body_matches_async_task(body, expected_async_result)
        call_args, call_kwargs = mock_apply_async.call_args[0]
        self.assertEqual(call_args, ['gravy', 'dummy-importer'])
        self.assertEqual(call_kwargs, {'repo_plugin_config': {'foo': 'bar'}})

    @mock.patch('pulp.server.async.tasks.resources.get_worker_for_reservation')
    def test_post_missing_repo(self, mock_get_worker_for_reservation):
        """
        Tests adding an importer to a repo that doesn't exist.
        """
        mock_get_worker_for_reservation.return_value = Worker('some_queue', datetime.datetime.now())
        # Test
        req_body = {
            'importer_type_id': 'dummy-importer',
            'importer_config': {'foo': 'bar'},
        }
        status, body = self.post('/v2/repositories/blah/importers/', params=req_body)
        # Verify
        self.assertEqual(202, status)

    def test_post_bad_request_missing_data(self):
        """
        Tests adding an importer but not specifying the required data.
        """
        # Setup
        self.repo_manager.create_repo('icecream')
        # Test
        status, body = self.post('/v2/repositories/icecream/importers/', params={})
        # Verify
        self.assertEqual(400, status)

    @mock.patch('pulp.server.async.tasks.resources.get_worker_for_reservation')
    def test_post_bad_request_invalid_data(self, mock_get_worker_for_reservation):
        """
        Tests adding an importer but specifying incorrect metadata.
        """
        # Setup
        self.repo_manager.create_repo('walnuts')
        req_body = {
            'importer_type_id': 'not-a-real-importer'
        }
        mock_get_worker_for_reservation.return_value = Worker('some_queue', datetime.datetime.now())
        # Test
        status, body = self.post('/v2/repositories/walnuts/importers/', params=req_body)
        # Verify
        self.assertEqual(202, status)


class RepoImporterTests(RepoPluginsTests):
    def test_get(self):
        """
        Tests getting an importer that exists.
        """
        # Setup
        self.repo_manager.create_repo('pie')
        self.importer_manager.set_importer('pie', 'dummy-importer', {})
        # Test
        status, body = self.get('/v2/repositories/pie/importers/dummy-importer/')
        # Verify
        self.assertEqual(200, status)
        self.assertEqual(body['id'], 'dummy-importer')

    def test_get_missing_repo(self):
        """
        Tests getting the importer for a repo that doesn't exist.
        """
        # Test
        status, body = self.get('/v2/repositories/not-there/importers/irrelevant')
        # Verify
        self.assertEqual(404, status)

    def test_get_missing_importer(self):
        """
        Tests getting the importer for a repo that doesn't have one.
        """
        # Setup
        self.repo_manager.create_repo('cherry_pie')
        # Test
        status, body = self.get('/v2/repositories/cherry_pie/importers/not_there/')
        # Verify
        self.assertEqual(404, status)

    @mock.patch('celery.Task.apply_async')
    @mock.patch('pulp.server.async.tasks.uuid', autospec=True)
    @mock.patch('pulp.server.async.tasks.resources.get_worker_for_reservation')
    def test_delete(self, mock_get_worker_for_reservation, mock_uuid, mock_apply_async):
        """
        Tests removing an importer from a repo.
        """
        # Setup
        repo_id = 'blueberry_pie'
        self.repo_manager.create_repo(repo_id)
        self.importer_manager.set_importer(repo_id, 'dummy-importer', {})
        uuid_list = [uuid.uuid4() for i in range(10)]
        mock_uuid.uuid4.side_effect = copy.deepcopy(uuid_list)
        mock_get_worker_for_reservation.return_value = Worker('some_queue', datetime.datetime.now())

        # Test
        status, body = self.delete('/v2/repositories/blueberry_pie/importers/dummy-importer/')

        # Verify
        self.assertEqual(202, status)
        self.assertEqual(body['spawned_tasks'][0]['task_id'], str(uuid_list[0]))
        call_args = mock_apply_async.call_args[0]
        self.assertTrue([repo_id] in call_args)

    @mock.patch('pulp.server.async.tasks.resources.get_worker_for_reservation')
    def test_delete_missing_repo(self, mock_get_worker_for_reservation):
        """
        Tests deleting the importer from a repo that doesn't exist.
        """
        mock_get_worker_for_reservation.return_value = Worker('some_queue', datetime.datetime.now())
        # Test
        status, body = self.delete('/v2/repositories/bad_pie/importers/dummy-importer/')
        # Verify
        self.assertEqual(202, status)

    @mock.patch('pulp.server.async.tasks.resources.get_worker_for_reservation')
    def test_delete_missing_importer(self, mock_get_worker_for_reservation):
        """
        Tests deleting an importer from a repo that doesn't have one.
        """
        # Setup
        self.repo_manager.create_repo('apple_pie')
        mock_get_worker_for_reservation.return_value = Worker('some_queue', datetime.datetime.now())
        # Test
        status, body = self.delete('/v2/repositories/apple_pie/importers/dummy-importer/')
        # Verify
        self.assertEqual(202, status)

    @mock.patch('celery.Task.apply_async')
    @mock.patch('pulp.server.async.tasks.uuid', autospec=True)
    @mock.patch('pulp.server.async.tasks.resources.get_worker_for_reservation')
    def test_update_importer_config(self, mock_get_worker_for_reservation, mock_uuid,
                                    mock_apply_async):
        """
        Tests successfully updating an importer's config.
        """
        # Setup
        repo_id = 'pumpkin_pie'
        self.repo_manager.create_repo(repo_id)
        self.importer_manager.set_importer(repo_id, 'dummy-importer', {})
        uuid_list = [uuid.uuid4() for i in range(10)]
        mock_uuid.uuid4.side_effect = copy.deepcopy(uuid_list)
        mock_get_worker_for_reservation.return_value = Worker('some_queue', datetime.datetime.now())
        # Test
        new_config = {'importer_config': {'ice_cream': True}}
        status, body = self.put('/v2/repositories/pumpkin_pie/importers/dummy-importer/',
                                params=new_config)
        # Verify
        self.assertEqual(202, status)
        self.assertEqual(body['spawned_tasks'][0]['task_id'], str(uuid_list[0]))
        call_args, call_kwargs = mock_apply_async.call_args[0]
        self.assertTrue(repo_id in call_args)
        self.assertEqual(call_kwargs['importer_config'], {'ice_cream': True})

    @mock.patch('pulp.server.async.tasks.resources.get_worker_for_reservation')
    def test_update_missing_repo(self, mock_get_worker_for_reservation):
        """
        Tests updating an importer config on a repo that doesn't exist.
        """
        mock_get_worker_for_reservation.return_value = Worker('some_queue', datetime.datetime.now())
        # Test
        status, body = self.put('/v2/repositories/foo/importers/dummy-importer/',
                                params={'importer_config': {}})
        # Verify
        self.assertEqual(202, status)

    @mock.patch('pulp.server.async.tasks.resources.get_worker_for_reservation')
    def test_update_missing_importer(self, mock_get_worker_for_reservation):
        """
        Tests updating a repo that doesn't have an importer.
        """
        # Setup
        self.repo_manager.create_repo('pie')
        mock_get_worker_for_reservation.return_value = Worker('some_queue', datetime.datetime.now())
        # Test
        status, body = self.put('/v2/repositories/pie/importers/dummy-importer/',
                                params={'importer_config': {}})
        # Verify
        self.assertEqual(202, status)

    def test_update_bad_request(self):
        """
        Tests updating with incorrect parameters.
        """
        # Setup
        self.repo_manager.create_repo('pie')
        self.importer_manager.set_importer('pie', 'dummy-importer', {})
        # Test
        status, body = self.put('/v2/repositories/pie/importers/dummy-importer/', params={})
        # Verify
        self.assertEqual(400, status)


class RepoDistributorsTests(RepoPluginsTests):
    def test_get_distributors(self):
        """
        Tests retrieving all distributors for a repo.
        """
        # Setup
        self.repo_manager.create_repo('coffee')
        self.distributor_manager.add_distributor('coffee', 'dummy-distributor', {}, True,
                                                 distributor_id='dist-1')
        self.distributor_manager.add_distributor('coffee', 'dummy-distributor', {}, True,
                                                 distributor_id='dist-2')
        # Test
        status, body = self.get('/v2/repositories/coffee/distributors/')
        # Verify
        self.assertEqual(200, status)
        self.assertEqual(2, len(body))

    def test_get_distributors_no_distributors(self):
        """
        Tests retrieving distributors for a repo that has none.
        """
        # Setup
        self.repo_manager.create_repo('dark-roast')
        # Test
        status, body = self.get('/v2/repositories/dark-roast/distributors/')
        # Verify
        self.assertEqual(200, status)
        self.assertEqual(0, len(body))

    def test_get_distributors_missing_repo(self):
        """
        Tests retrieving distributors for a repo that doesn't exist.
        """
        # Test
        status, body = self.get('/v2/repositories/not-there/distributors/')
        # Verify
        self.assertEqual(404, status)

    def test_create_distributor(self):
        """
        Tests creating a distributor on a repo.
        """

        # Setup
        self.repo_manager.create_repo('tea')

        req_body = {
            'distributor_type_id': 'dummy-distributor',
            'distributor_config': {'a': 'b'},
        }

        # Test
        status, body = self.post('/v2/repositories/tea/distributors/', params=req_body)

        # Verify
        self.assertEqual(201, status)
        self.assertEqual(body['repo_id'], 'tea')
        self.assertEqual(body['config'], req_body['distributor_config'])
        self.assertEqual(body['auto_publish'], False)
        self.assertTrue('id' in body)

    def test_create_distributor_missing_repo(self):
        """
        Tests creating a distributor on a repo that doesn't exist.
        """

        # Test
        req_body = {
            'distributor_type_id': 'dummy-distributor',
            'distributor_config': {'a': 'b'},
        }
        status, body = self.post('/v2/repositories/not_there/distributors/', params=req_body)

        # Verify
        self.assertEqual(404, status)

    def test_create_distributor_invalid_data(self):
        """
        Tests creating a distributor but not passing in all the required data.
        """

        # Setup
        self.repo_manager.create_repo('invalid')

        # Test
        status, body = self.post('/v2/repositories/invalid/distributors/', params={})

        # Verify
        self.assertEqual(400, status)


class RepoDistributorTestsNoWSGI(PulpWebservicesTests):
    """
    Tests that have been converted to not require a running web.py stack
    """

    @mock.patch('pulp.server.managers.factory.repo_distributor_manager')
    @mock.patch('pulp.server.tasks.repository.distributor_delete', autospec=True)
    def test_delete(self, mock_delete_task, mock_manager_factory):
        repo_distributor = repositories.RepoDistributor()

        async_task = AsyncResult('foo-id')
        mock_delete_task.apply_async_with_reservation.return_value = async_task
        self.assertRaises(OperationPostponed, repo_distributor.DELETE,
                          "foo-repo", "foo-distributor")
        task_tags = ['pulp:repository:foo-repo',
                     'pulp:repository_distributor:foo-distributor',
                     'pulp:action:remove_distributor']
        mock_delete_task.apply_async_with_reservation.assert_called_once_with(
            tags.RESOURCE_REPOSITORY_TYPE, 'foo-repo',
            ['foo-repo', 'foo-distributor'], tags=task_tags)

        # validate the permissions
        self.validate_auth(authorization.UPDATE)

        try:
            repo_distributor.DELETE("foo-repo", "foo-distributor")
        except OperationPostponed, op:
            self.assertEquals(op.call_report, async_task)

    @mock.patch('pulp.server.managers.factory.repo_distributor_manager')
    @mock.patch('pulp.server.tasks.repository.distributor_update', autospec=True)
    def test_put(self, mock_update_task, mock_manager):
        repo_distributor = repositories.RepoDistributor()
        new_config = {'key': 'updated'}
        repo_distributor.params = mock.Mock(return_value={'distributor_config': new_config,
                                                          'delta': {}})

        async_task = AsyncResult('foo-id')
        mock_update_task.apply_async_with_reservation.return_value = async_task
        self.assertRaises(OperationPostponed, repo_distributor.PUT, "foo-repo", "foo-distributor")

        task_tags = ['pulp:repository:foo-repo',
                     'pulp:repository_distributor:foo-distributor',
                     'pulp:action:update_distributor']
        mock_update_task.apply_async_with_reservation.assert_called_once_with(
            tags.RESOURCE_REPOSITORY_TYPE, 'foo-repo',
            ['foo-repo', 'foo-distributor', new_config, {}], tags=task_tags)

        # validate the permissions
        self.validate_auth(authorization.UPDATE)

        try:
            repo_distributor.PUT("foo-repo", "foo-distributor")
        except OperationPostponed, op:
            self.assertEquals(op.call_report, async_task)

    @mock.patch('pulp.server.tasks.repository.distributor_update', autospec=True)
    def test_put_missing_config_raises_exception(self, mock_update_task):
        repo_distributor = repositories.RepoDistributor()
        repo_distributor.params = mock.Mock(return_value={'distributor_config': None})
        self.assertRaises(MissingResource, repo_distributor.PUT, 'foo', 'bar')


class RepoDistributorTests(RepoPluginsTests):
    def test_get(self):
        """
        Tests getting a single repo distributor.
        """

        # Setup
        self.repo_manager.create_repo('repo')
        self.distributor_manager.add_distributor('repo', 'dummy-distributor', {}, True, 'dist-1')

        # Test
        status, body = self.get('/v2/repositories/repo/distributors/dist-1/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(body['id'], 'dist-1')

    def test_get_missing_distributor(self):
        """
        Tests getting a distributor that doesn't exist.
        """

        # Setup
        self.repo_manager.create_repo('repo-1')

        # Test
        status, body = self.get('/v2/repositories/repo-1/distributors/foo/')

        # Verify
        self.assertEqual(404, status)


class RepoSyncHistoryTests(RepoPluginsTests):
    def test_get(self):
        """
        Tests getting sync history for a repo.
        """

        # Setup
        self.repo_manager.create_repo('sync-test')
        for i in range(0, 10):
            self.add_success_result('sync-test', i)

        # Test
        status, body = self.get('/v2/repositories/sync-test/history/sync/')

        # Verify. Confirm all 10 entries are returned.
        self.assertEqual(200, status)
        self.assertEqual(10, len(body))

    def test_get_no_entries(self):
        """
        Tests getting sync history entries for a repo that exists but hasn't been syncced.
        """

        # Setup
        self.repo_manager.create_repo('boring')

        # Test
        status, body = self.get('/v2/repositories/boring/history/sync/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(0, len(body))

    def test_get_missing_repo(self):
        """
        Tests getting sync history for a repo that doesn't exist.
        """

        # Test
        status, body = self.get('/v2/repositories/no/history/sync/')

        # Verify
        self.assertEqual(404, status)

    def test_get_bad_limit(self):
        """
        Tests getting with an invalid limit query parameter.
        """

        # Setup
        self.repo_manager.create_repo('sync-test')
        self.add_success_result('sync-test', 0)

        # Test
        status, body = self.get('/v2/repositories/sync-test/history/sync/?limit=unparsable')

        # Verify
        self.assertEqual(400, status)

    def add_success_result(self, repo_id, offset):
        started = datetime.datetime.now(dateutils.local_tz())
        completed = started + datetime.timedelta(days=offset)
        r = RepoSyncResult.expected_result(repo_id, 'foo', 'bar',
                                           dateutils.format_iso8601_datetime(started),
                                           dateutils.format_iso8601_datetime(completed), 1, 1, 1,
                                           '', '', RepoSyncResult.RESULT_SUCCESS)
        RepoSyncResult.get_collection().save(r, safe=True)


class RepoPublishHistoryTests(RepoPluginsTests):
    def test_get(self):
        """
        Tests getting the publish history for a repo.
        """

        # Setup
        self.repo_manager.create_repo('pub-test')
        self.distributor_manager.add_distributor('pub-test', 'dummy-distributor', {}, True,
                                                 distributor_id='dist-1')
        for i in range(0, 10):
            self._add_success_result('pub-test', 'dist-1', i)

        # Test
        status, body = self.get('/v2/repositories/pub-test/history/publish/dist-1/')

        # Verify. Confirm all 10 entries are returned.
        self.assertEqual(200, status)
        self.assertEqual(10, len(body))

    def test_get_no_entries(self):
        """
        Tests an empty list is returned for a distributor that has not published.
        """

        # Setup
        self.repo_manager.create_repo('foo')
        self.distributor_manager.add_distributor('foo', 'dummy-distributor', {}, True,
                                                 distributor_id='empty')

        # Test
        status, body = self.get('/v2/repositories/foo/history/publish/empty/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(0, len(body))

    def test_get_missing_repo(self):
        """
        Tests getting history for a repo that doesn't exist.
        """

        # Test
        status, body = self.get('/v2/repositories/foo/history/publish/irrlevant/')

        # Verify
        self.assertEqual(404, status)

    def test_get_missing_distributor(self):
        """
        Tests getting history for a distributor that doesn't exist on the repo.
        """

        # Setup
        self.repo_manager.create_repo('foo')

        # Test
        status, body = self.get('/v2/repositories/foo/history/publish/irrlevant/')

        # Verify
        self.assertEqual(404, status)

    def test_get_bad_limit(self):
        """
        Tests getting with an invalid limit query parameter.
        """

        # Test
        status, body = self.get('/v2/repositories/foo/history/publish/empty/?limit=unparsable')

        # Verify
        self.assertEqual(400, status)

    def _add_success_result(self, repo_id, distributor_id, offset):
        started = datetime.datetime.now(dateutils.local_tz())
        completed = started + datetime.timedelta(days=offset)
        r = RepoPublishResult.expected_result(repo_id, distributor_id, 'bar',
                                              dateutils.format_iso8601_datetime(started),
                                              dateutils.format_iso8601_datetime(completed), '', '',
                                              RepoPublishResult.RESULT_SUCCESS)
        RepoPublishResult.get_collection().save(r, safe=True)


class RepoUnitAssociationQueryTests(RepoControllersTests):
    def setUp(self):
        super(RepoUnitAssociationQueryTests, self).setUp()
        self.repo_manager.create_repo('repo-1')

        self.association_query_mock = mock.Mock()
        manager_factory._INSTANCES[
            manager_factory.TYPE_REPO_ASSOCIATION_QUERY] = self.association_query_mock

    def clean(self):
        super(RepoUnitAssociationQueryTests, self).clean()
        manager_factory.reset()

    def test_post_single_type(self):
        """
        Passes in a full query document to test the parsing into criteria.
        """

        # Setup
        self.association_query_mock.get_units_by_type.return_value = []

        query = {
            'type_ids': ['rpm'],
            'filters': {
                'unit': {'key': {'$in': 'zsh'}},
                'association': {'owner_type': 'importer'}
            },
            'sort': {
                'unit': [['name', 'ascending'], ['version', '-1']],
                'association': [['created', '-1'], ['updated', '1']]
            },
            'limit': '100',
            'skip': '200',
            'fields': {
                'unit': ['name', 'version', 'arch'],
                'association': ['created']
            },
            'remove_duplicates': 'True'
        }

        params = {'criteria': query}
        status, body = self.post('/v2/repositories/repo-1/search/units/', params=params)

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(0, self.association_query_mock.get_units_across_types.call_count)
        self.assertEqual(1, self.association_query_mock.get_units_by_type.call_count)

        criteria = self.association_query_mock.get_units_by_type.call_args[1]['criteria']
        self.assertTrue(isinstance(criteria, UnitAssociationCriteria))
        self.assertEqual(query['type_ids'], criteria.type_ids)
        self.assertEqual(query['filters']['association'], criteria.association_filters)
        self.assertEqual(query['filters']['unit'], criteria.unit_filters)
        self.assertEqual([('created', UnitAssociationCriteria.SORT_DESCENDING),
                          ('updated', UnitAssociationCriteria.SORT_ASCENDING)],
                         criteria.association_sort)
        self.assertEqual([('name', UnitAssociationCriteria.SORT_ASCENDING),
                          ('version', UnitAssociationCriteria.SORT_DESCENDING)], criteria.unit_sort)
        self.assertEqual(int(query['limit']), criteria.limit)
        self.assertEqual(int(query['skip']), criteria.skip)
        self.assertEqual(query['fields']['unit'], criteria.unit_fields)
        self.assertEqual(query['fields']['association'] + ['unit_id', 'unit_type_id'],
                         criteria.association_fields)
        self.assertEqual(bool(query['remove_duplicates']), criteria.remove_duplicates)

    def test_post_multiple_type(self):
        """
        Passes in a multiple typed query to ensure the correct manager method is called.
        """

        # Setup
        self.association_query_mock.get_units_across_types.return_value = []

        query = {'type_ids': ['rpm', 'errata']}

        params = {'criteria': query}
        status, body = self.post('/v2/repositories/repo-1/search/units/', params=params)

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(0, self.association_query_mock.get_units_by_type.call_count)
        self.assertEqual(1, self.association_query_mock.get_units_across_types.call_count)
        self.assertTrue(
            isinstance(self.association_query_mock.get_units_across_types.call_args[1]['criteria'],
                       UnitAssociationCriteria))

    def test_post_missing_query(self):
        # Test
        status, body = self.post('/v2/repositories/repo-1/search/units/')

        # Verify
        self.assertEqual(status, 400)

    def test_post_bad_query(self):
        # Test
        params = {'criteria': {'limit': 'fus'}}
        status, body = self.post('/v2/repositories/repo-1/search/units/', params=params)

        # Verify
        self.assertEqual(400, status)


class DependencyResolutionTests(RepoControllersTests):
    @mock.patch(
        'pulp.server.managers.repo.dependency.DependencyManager.resolve_dependencies_by_criteria')
    def test_post(self, mock_resolve_method):
        # Setup
        mock_resolve_method.return_value = ['foo']

        # Test
        status, body = self.post('/v2/repositories/repo/actions/resolve_dependencies/')

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(1, mock_resolve_method.call_count)

    @mock.patch(
        'pulp.server.managers.repo.dependency.DependencyManager.resolve_dependencies_by_criteria')
    def test_post_bad_criteria(self, mock_resolve_method):
        # Setup
        mock_resolve_method.return_value = ['foo']
        body = {
            'criteria': 'bar'
        }

        # Test
        status, body = self.post('/v2/repositories/repo/actions/resolve_dependencies/', params=body)

        # Verify
        self.assertEqual(400, status)
        self.assertEqual(0, mock_resolve_method.call_count)

    @mock.patch.object(base.PulpWebserviceTests, 'HEADERS', spec=dict)
    def test_post_auth_required(self, mock_headers):
        """
        Test that when the proper authentication information is missing, the server returns a 401
        error when RepoResolveDependencies.POST is called
        """
        call_status, call_body = self.post('/v2/repositories/repo/actions/resolve_dependencies/')
        self.assertEqual(401, call_status)


class RepoAssociateTests(RepoControllersTests):
    def setUp(self):
        super(RepoAssociateTests, self).setUp()
        self.repo_manager.create_repo('source-repo-1')
        self.repo_manager.create_repo('dest-repo-1')

        self.association_manager_dummy = dummy_plugins.DummyObject()
        manager_factory._INSTANCES[manager_factory.TYPE_REPO_ASSOCIATION] = \
            self.association_manager_dummy

    def clean(self):
        super(RepoAssociateTests, self).clean()
        manager_factory.reset()

    def test_post_missing_source_repo_id(self):
        status, body = self.post('/v2/repositories/dest-repo-1/actions/associate/')

        self.assertEqual(400, status)

    def test_post_invalid_dest_repo(self):
        params = {'source_repo_id': 'source-repo-1', 'criteria': {}, }

        status, body = self.post('/v2/repositories/fake/actions/associate/', params=params)

        self.assertEqual(404, status)

    def test_post_invalid_source_repo(self):
        params = {'source_repo_id': 'fake', 'criteria': {}, }

        status, body = self.post('/v2/repositories/dest-repo-1/actions/associate/', params=params)

        self.assertEqual(400, status)

    def test_post_unparsable_criteria(self):
        # Test
        params = {'source_repo_id': 'source-repo-1', 'criteria': 'unparsable'}
        status, body = self.post('/v2/repositories/dest-repo-1/actions/associate/', params=params)

        # Verify
        self.assertEqual(400, status)


# scheduled sync rest api ------------------------------------------------------

class ScheduledSyncTests(RepoPluginsTests):
    def setUp(self):
        super(ScheduledSyncTests, self).setUp()

        self.repo_id = 'scheduled-repo'
        self.repo_manager.create_repo(self.repo_id)
        self.importer_manager.set_importer(self.repo_id, 'dummy-importer', {})

    def clean(self):
        super(ScheduledSyncTests, self).clean()
        ScheduledCall.get_collection().remove(safe=True)

    def tearDown(self):
        super(ScheduledSyncTests, self).tearDown()

    @property
    def collection_uri_path(self):
        return '/v2/repositories/%s/importers/dummy-importer/schedules/sync/' % self.repo_id

    def resource_uri_path(self, schedule_id):
        return self.collection_uri_path + schedule_id + '/'

    def test_get_empty_sync_schedules(self):
        try:
            self.get(self.collection_uri_path)
        except:
            self.fail(traceback.format_exc())

    def test_create_sync_schedule(self):
        params = {'schedule': 'P1DT'}
        status, body = self.post(self.collection_uri_path, params)
        self.assertTrue(status == httplib.CREATED, '\n'.join((str(status), pformat(body))))
        for field in ('_id', '_href', 'schedule', 'failure_threshold', 'enabled',
                      'consecutive_failures', 'remaining_runs', 'first_run',
                      'last_run_at', 'next_run', 'args', 'kwargs'):
            self.assertTrue(field in body, 'missing field: %s' % field)

    def test_create_missing_schedule(self):
        status, body = self.post(self.collection_uri_path, {})
        self.assertTrue(status == httplib.BAD_REQUEST)

    def test_get_scheduled_sync(self):
        status, body = self.post(self.collection_uri_path, {'schedule': 'PT2S'})
        self.assertTrue(status == httplib.CREATED)

        status, body = self.get(self.resource_uri_path(body['_id']))
        self.assertTrue(status == httplib.OK)

    def test_delete_schedule(self):
        status, body = self.post(self.collection_uri_path, {'schedule': 'P1DT'})
        self.assertTrue(status == httplib.CREATED)
        schedule_id = body['_id']

        status, body = self.delete(self.resource_uri_path(schedule_id))
        self.assertTrue(status == httplib.OK)
        self.assertTrue(body is None)

    def test_delete_schedule_does_not_exist(self):
        """
        make sure it doesn't return an error if the schedule doesn't exist. That's
        what the client wanted anyway!
        """
        status, body = self.delete(self.resource_uri_path(str(ObjectId())))
        self.assertTrue(status == httplib.OK, msg=status)

    def test_delete_invalid_schedule_id(self):
        status, body = self.delete(self.resource_uri_path('not-there'))
        self.assertTrue(status == httplib.BAD_REQUEST, msg=status)

    def test_update_schedule(self):
        schedule = {'schedule': 'PT1H',
                    'failure_threshold': 2,
                    'enabled': True}
        status, body = self.post(self.collection_uri_path, schedule)
        self.assertTrue(status == httplib.CREATED)
        for key in schedule:
            self.assertTrue(schedule[key] == body[key], key)

        schedule_id = body['_id']
        updates = {'schedule': 'PT2H',
                   'failure_threshold': 3,
                   'enabled': False,
                   'override_config': {'key': 'value'}}
        status, body = self.put(self.resource_uri_path(schedule_id), updates)
        self.assertTrue(status == httplib.OK, '\n'.join((str(status), pformat(body))))
        self.assertTrue(schedule_id == body['_id'])
        self.assertEqual(body['schedule'], updates['schedule'])
        self.assertEqual(body['failure_threshold'], updates['failure_threshold'])
        self.assertEqual(body['enabled'], updates['enabled'])
        self.assertEqual(body['kwargs']['overrides'], updates['override_config'])


# scheduled publish api --------------------------------------------------------

class ScheduledPublishTests(RepoPluginsTests):
    def setUp(self):
        super(ScheduledPublishTests, self).setUp()
        self.repo_id = 'scheduled-repo'
        self.repo_manager.create_repo(self.repo_id)
        self.distributor_manager.add_distributor(self.repo_id, 'dummy-distributor', {}, True,
                                                 distributor_id='dist')

    def clean(self):
        super(ScheduledPublishTests, self).clean()
        ScheduledCall.get_collection().remove(safe=True)

    def tearDown(self):
        super(ScheduledPublishTests, self).tearDown()

    @property
    def collection_uri_path(self):
        return '/v2/repositories/%s/distributors/dist/schedules/publish/' % self.repo_id

    def resource_uri_path(self, schedule_id):
        return self.collection_uri_path + schedule_id + '/'

    def test_get_empty_schedule_list(self):
        status, body = self.get(self.collection_uri_path)
        self.assertTrue(status == httplib.OK)

    def test_create_publish_schedule(self):
        params = {'schedule': 'P1DT'}
        status, body = self.post(self.collection_uri_path, params)
        self.assertTrue(status == httplib.CREATED, '\n'.join((str(status), pformat(body))))
        self.assertTrue(params['schedule'] == body['schedule'])
        for field in ('_id', '_href', 'schedule', 'failure_threshold', 'enabled',
                      'consecutive_failures', 'remaining_runs', 'first_run',
                      'last_run_at', 'next_run', 'args', 'kwargs'):
            self.assertTrue(field in body, 'missing field: %s' % field)

    def test_create_missing_schedule(self):
        status, body = self.post(self.collection_uri_path, {})
        self.assertTrue(status == httplib.BAD_REQUEST)

    def test_get_scheduled_sync(self):
        status, body = self.post(self.collection_uri_path, {'schedule': 'PT2S'})
        self.assertTrue(status == httplib.CREATED)

        status, body = self.get(self.resource_uri_path(body['_id']))
        self.assertTrue(status == httplib.OK)

    def test_delete_schedule(self):
        status, body = self.post(self.collection_uri_path, {'schedule': 'P1DT'})
        self.assertTrue(status == httplib.CREATED)
        schedule_id = body['_id']

        status, body = self.delete(self.resource_uri_path(schedule_id))
        self.assertTrue(status == httplib.OK)
        self.assertTrue(body is None)

    def test_delete_non_existent(self):
        """
        make sure it doesn't return an error if the schedule doesn't exist. That's
        what the client wanted anyway!
        """
        status, body = self.delete(self.resource_uri_path(str(ObjectId())))
        self.assertTrue(status == httplib.OK)

    def test_delete_invalid_schedule_id(self):
        status, body = self.delete(self.resource_uri_path('not-there'))
        self.assertTrue(status == httplib.BAD_REQUEST)

    def test_update_schedule(self):
        schedule = {'schedule': 'PT1H',
                    'failure_threshold': 2,
                    'enabled': True}
        status, body = self.post(self.collection_uri_path, schedule)
        self.assertTrue(status == httplib.CREATED)
        for key in schedule:
            self.assertTrue(schedule[key] == body[key], key)

        schedule_id = body['_id']
        updates = {'schedule': 'PT2H',
                   'failure_threshold': 3,
                   'enabled': False,
                   'override_config': {'key': 'value'}}
        status, body = self.put(self.resource_uri_path(schedule_id), updates)
        self.assertTrue(status == httplib.OK, '\n'.join((str(status), pformat(body))))
        self.assertTrue(schedule_id == body['_id'])
        self.assertEqual(body['schedule'], updates['schedule'])
        self.assertEqual(body['failure_threshold'], updates['failure_threshold'])
        self.assertEqual(body['enabled'], updates['enabled'])
        self.assertEqual(body['kwargs']['overrides'], updates['override_config'])


class UnitCriteriaTests(unittest.TestCase):
    def test_parse_criteria(self):
        # Setup
        query = {
            'type_ids': ['rpm'],
            'filters': {
                'unit': {'$and': [
                    {'$regex': '^p.*'},
                    {'$not': 'ython$'},
                ]},
                'association': {'created': {'$gt': 'now'}},
            },

            'limit': 100,
            'skip': 200,
            'fields': {
                'unit': ['name', 'version'],
                'association': ['created'],
            },
            'remove_duplicates': True,
        }

        # Test
        criteria = UnitAssociationCriteria.from_client_input(query)

        # Verify
        self.assertEqual(criteria.type_ids, ['rpm'])
        self.assertEqual(criteria.association_filters, {'created': {'$gt': 'now'}})
        self.assertEqual(criteria.limit, 100)
        self.assertEqual(criteria.skip, 200)
        self.assertEqual(criteria.unit_fields, ['name', 'version'])
        self.assertEqual(criteria.association_fields, ['created', 'unit_id', 'unit_type_id'])
        self.assertEqual(criteria.remove_duplicates, True)

        #   Check the special $not handling in the unit filter
        self.assertTrue('$and' in criteria.unit_filters)
        and_list = criteria.unit_filters['$and']

        self.assertTrue('$regex' in and_list[0])
        self.assertEqual(and_list[0]['$regex'], '^p.*')

        self.assertTrue('$not' in and_list[1])
        self.assertEqual(and_list[1]['$not'], re.compile('ython$'))


class TestRepoApplicabilityRegeneration(base.PulpWebserviceTests):
    CONSUMER_IDS = ['consumer-1', 'consumer-2']
    FILTER = {'id': {'$in': CONSUMER_IDS}}
    SORT = [{'id': 1}]
    CONSUMER_CRITERIA = Criteria(filters=FILTER, sort=SORT)
    PROFILE = [{'name': 'zsh', 'version': '1.0'}, {'name': 'ksh', 'version': '1.0'}]
    REPO_IDS = ['repo-1', 'repo-2']
    REPO_FILTER = {'id': {'$in': REPO_IDS}}
    REPO_CRITERIA = Criteria(filters=REPO_FILTER, sort=[{'id': 1}])
    YUM_DISTRIBUTOR_ID = 'yum_distributor'

    PATH = '/v2/repositories/actions/content/regenerate_applicability/'

    def setUp(self):
        base.PulpWebserviceTests.setUp(self)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()
        RepoProfileApplicability.get_collection().remove()
        plugin_api._create_manager()
        mock_plugins.install()

        yum_profiler, cfg = plugin_api.get_profiler_by_type('rpm')
        yum_profiler.calculate_applicable_units = \
            mock.Mock(side_effect=lambda p, r, c, x: {'rpm': ['rpm-1', 'rpm-2'],
                                                      'erratum': ['errata-1', 'errata-2']})

    def tearDown(self):
        base.PulpWebserviceTests.tearDown(self)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()
        RepoProfileApplicability.get_collection().remove()
        mock_plugins.reset()

    def populate_repos(self):
        repo_manager = manager_factory.repo_manager()
        distributor_manager = manager_factory.repo_distributor_manager()
        # Create repos and add distributor
        for repo_id in self.REPO_IDS:
            repo_manager.create_repo(repo_id)
            distributor_manager.add_distributor(
                repo_id,
                'mock-distributor',
                {},
                True,
                self.YUM_DISTRIBUTOR_ID)

    def populate_bindings(self):
        self.populate_repos()
        bind_manager = manager_factory.consumer_bind_manager()
        # Add bindings for the given repos and consumers
        for consumer_id in self.CONSUMER_IDS:
            for repo_id in self.REPO_IDS:
                bind_manager.bind(consumer_id, repo_id, self.YUM_DISTRIBUTOR_ID, False, {})

    def populate(self):
        manager = manager_factory.consumer_manager()
        for consumer_id in self.CONSUMER_IDS:
            manager.register(consumer_id)
        manager = manager_factory.consumer_profile_manager()
        for consumer_id in self.CONSUMER_IDS:
            manager.create(consumer_id, 'rpm', self.PROFILE)

    @mock.patch('pulp.server.async.tasks.resources.get_worker_for_reservation')
    def test_regenerate_applicability(self, mock_get_worker_for_reservation):
        # Setup
        mock_get_worker_for_reservation.return_value = Worker('some_queue', datetime.datetime.now())
        self.populate()
        self.populate_bindings()
        # Test
        request_body = dict(repo_criteria={'filters': self.REPO_FILTER})
        status, body = self.post(self.PATH, request_body)
        # Verify
        self.assertEquals(status, 202)
        self.assertTrue('task_id' in body['spawned_tasks'][0])

    @mock.patch('pulp.server.async.tasks.resources.get_worker_for_reservation')
    def test_regenerate_applicability_no_consumer(self, mock_get_worker_for_reservation):
        # Test
        mock_get_worker_for_reservation.return_value = Worker('some_queue', datetime.datetime.now())
        request_body = dict(repo_criteria={'filters': self.REPO_FILTER})
        status, body = self.post(self.PATH, request_body)
        # Verify
        self.assertEquals(status, 202)
        self.assertTrue('task_id' in body['spawned_tasks'][0])

    @mock.patch('pulp.server.async.tasks.resources.get_worker_for_reservation')
    def test_regenerate_applicability_no_bindings(self, mock_get_worker_for_reservation):
        # Setup
        mock_get_worker_for_reservation.return_value = Worker('some_queue', datetime.datetime.now())
        self.populate()
        # Test
        request_body = dict(repo_criteria={'filters': self.REPO_FILTER})
        status, body = self.post(self.PATH, request_body)
        # Verify
        self.assertEquals(status, 202)
        self.assertTrue('task_id' in body['spawned_tasks'][0])

    def test_regenerate_applicability_no_criteria(self):
        # Setup
        self.populate()
        # Test
        request_body = {}
        status, body = self.post(self.PATH, request_body)
        # Verify
        self.assertEquals(status, 400)
        self.assertTrue('missing_property_names' in body)
        self.assertTrue(body['missing_property_names'] == ['repo_criteria'])
        self.assertFalse('task_id' in body)

    def test_regenerate_applicability_wrong_criteria(self):
        # Setup
        self.populate()
        # Test
        request_body = dict(repo_criteria='foo')
        status, body = self.post(self.PATH, request_body)
        # Verify
        self.assertEquals(status, 400)
        self.assertTrue('property_names' in body)
        self.assertTrue(body['property_names'] == ['repo_criteria'])
        self.assertFalse('task_id' in body)
