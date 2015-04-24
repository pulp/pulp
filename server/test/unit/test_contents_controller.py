import copy
import datetime
import os
import shutil
import uuid

from celery.result import AsyncResult
import mock

from pulp.devel import dummy_plugins
from pulp.devel.unit.util import assert_body_matches_async_task
from pulp.server.db.model.repository import Repo, RepoImporter
from pulp.server.db.model import Worker
from pulp.server.webservices.controllers.contents import ContentUnitsSearch
import base
import pulp.server.managers.factory as manager_factory


class TestContentUnitsSearch(base.PulpWebserviceTests):
    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'get_content_unit_collection')
    def test_post_retrieves_collection(self, mock_get_collection):
        status, body = self.post('/v2/content/units/deb/search/', {'criteria': {}})
        self.assertEqual(status, 200)
        self.assertEqual(mock_get_collection.call_count, 1)
        self.assertEqual(mock_get_collection.call_args[0][0], 'deb')

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'get_content_unit_collection')
    def test_get_retrieves_collection(self, mock_get_collection):
        status, body = self.get('/v2/content/units/deb/search/?limit=20')
        self.assertEqual(status, 200)
        self.assertEqual(mock_get_collection.call_count, 1)
        self.assertEqual(mock_get_collection.call_args[0][0], 'deb')

    @mock.patch(
        'pulp.server.webservices.controllers.contents.ContentUnitsCollection.process_unit',
        return_value='ContentUnit')
    @mock.patch(
        'pulp.server.managers.content.query.ContentQueryManager.find_by_criteria',
        return_value=['IAmAContentUnit'])
    def test_post_processes_units(self, mock_find, mock_process_unit):
        status, body = self.post('/v2/content/units/deb/search/', {'criteria': {}})
        self.assertEqual(status, 200)
        mock_process_unit.assert_called_once_with(mock_find.return_value[0])

    @mock.patch(
        'pulp.server.webservices.controllers.contents.ContentUnitsCollection.process_unit',
        return_value='ContentUnit')
    @mock.patch(
        'pulp.server.managers.content.query.ContentQueryManager.find_by_criteria',
        return_value=['IAmAContentUnit'])
    def test_get_processes_units(self, mock_find, mock_process_unit):
        status, body = self.get('/v2/content/units/deb/search/?limit=20')
        self.assertEqual(status, 200)
        mock_process_unit.assert_called_once_with(mock_find.return_value[0])

    @mock.patch(
        'pulp.server.managers.content.query.ContentQueryManager.find_by_criteria',
        return_value=[{'_id': 'foo', '_last_updated': 0}])
    @mock.patch('pulp.server.managers.repo.unit_association_query.RepoUnitAssociationQueryManager.'
                'find_by_criteria')
    def test_add_repo_memberships_criteria(self, mock_find_assoc, mock_find_unit):
        status, body = self.get('/v2/content/units/rpm/search/?include_repos=true')
        self.assertEqual(status, 200)
        criteria = mock_find_assoc.call_args[0][0]
        self.assertEqual(set(criteria.fields), set(('unit_id', 'repo_id')))
        self.assertEqual(criteria.filters['unit_type_id'], 'rpm')
        self.assertEqual(criteria.filters['unit_id'], {'$in': ['foo']})

    @mock.patch(
        'pulp.server.managers.content.query.ContentQueryManager.find_by_criteria',
        return_value=[{'_id': 'foo', '_last_updated': 0}])
    @mock.patch('pulp.server.managers.repo.unit_association_query.RepoUnitAssociationQueryManager.'
                'find_by_criteria')
    def test_add_repo_memberships_get(self, mock_find_assoc, mock_find_unit):
        mock_find_assoc.return_value = [{'unit_id': 'foo', 'repo_id': 'repo1'}]
        status, body = self.get('/v2/content/units/rpm/search/?include_repos=true')
        self.assertEqual(status, 200)
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0].get('repository_memberships'), ['repo1'])

    @mock.patch(
        'pulp.server.managers.content.query.ContentQueryManager.find_by_criteria',
        return_value=[{'_id': 'foo', '_last_updated': 0}])
    @mock.patch('pulp.server.managers.repo.unit_association_query.RepoUnitAssociationQueryManager.'
                'find_by_criteria')
    def test_add_repo_memberships_post(self, mock_find_assoc, mock_find_unit):
        mock_find_assoc.return_value = [{'unit_id': 'foo', 'repo_id': 'repo1'}]
        post_body = {'criteria': {}, 'include_repos': True}
        status, body = self.post('/v2/content/units/rpm/search/', post_body)
        self.assertEqual(status, 200)
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0].get('repository_memberships'), ['repo1'])


class TestContentUnitsSearchNonWeb(base.PulpServerTests):
    def setUp(self):
        super(TestContentUnitsSearchNonWeb, self).setUp()
        self.controller = ContentUnitsSearch()

    @mock.patch('pulp.server.managers.repo.unit_association_query.RepoUnitAssociationQueryManager.'
                'find_by_criteria')
    def test_add_repo_memberships_empty(self, mock_find):
        # make sure it doesn't do a search for associations if there are no
        # units found
        self.controller._add_repo_memberships([], 'rpm')
        self.assertEqual(mock_find.call_count, 0)

    @mock.patch('pulp.server.managers.repo.unit_association_query.RepoUnitAssociationQueryManager.'
                'find_by_criteria')
    def test_add_repo_memberships_(self, mock_find):
        mock_find.return_value = [{'repo_id': 'repo1', 'unit_id': 'unit1'}]

        units = [{'_id': 'unit1'}]
        ret = self.controller._add_repo_memberships(units, 'rpm')

        self.assertEqual(mock_find.call_count, 1)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].get('repository_memberships'), ['repo1'])


class BaseUploadTest(base.PulpWebserviceTests):

    def setUp(self):
        super(BaseUploadTest, self).setUp()
        self.upload_manager = manager_factory.content_upload_manager()

        upload_storage_dir = self.upload_manager._upload_storage_dir()

        if os.path.exists(upload_storage_dir):
            shutil.rmtree(upload_storage_dir)
        os.makedirs(upload_storage_dir)

        dummy_plugins.install()

    def tearDown(self):
        super(BaseUploadTest, self).tearDown()

        dummy_plugins.reset()

    def clean(self):
        super(BaseUploadTest, self).clean()
        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()


class ReservedResourceApplyAsync(object):
    """
    This object allows us to mock the return value of _reserve_resource.apply_async.get().
    """
    def get(self):
        return 'some_queue'
