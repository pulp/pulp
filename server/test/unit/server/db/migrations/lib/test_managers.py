import mock

from ..... import base
from pulp.devel import mock_plugins
from pulp.plugins.loader import api as plugin_api
from pulp.server.db import models
from pulp.server.db.model.repository import RepoImporter, RepoDistributor
from pulp.server.db.models import TaskStatus
from pulp.server.db.migrations.lib import managers


@mock.patch('pulp.server.db.migrations.lib.managers.get_collection')
@mock.patch('pulp.server.db.model.repository.RepoContentUnit.get_collection')
class RepoManagerTests(base.ResourceReservationTests):
    """
    Legacy tests for the RepoManager methods that were preserved for migrations.
    """

    def setUp(self):
        super(RepoManagerTests, self).setUp()

        plugin_api._create_manager()
        mock_plugins.install()

        # Create the manager instance to test
        self.manager = managers.RepoManager()

    def tearDown(self):
        super(RepoManagerTests, self).tearDown()
        mock_plugins.reset()

    def clean(self):
        super(RepoManagerTests, self).clean()

        models.Repository.drop_collection()
        RepoImporter.get_collection().remove()
        RepoDistributor.get_collection().remove()
        TaskStatus.objects().delete()

    def test_rebuild_content_unit_counts(self, mock_get_assoc_col, mock_get_repo_col):
        # platform migration 0004 has a test for this that uses live data

        repo_col = mock_get_repo_col.return_value
        find = mock_get_assoc_col.return_value.find
        cursor = find.return_value
        cursor.distinct.return_value = ['rpm', 'srpm']
        cursor.count.return_value = 6

        self.manager.rebuild_content_unit_counts(['repo1'])

        # once to get the type_ids, then once more for each of the 2 types
        self.assertEqual(find.call_count, 3)
        find.assert_any_call({'repo_id': 'repo1'})
        find.assert_any_call({'repo_id': 'repo1', 'unit_type_id': 'rpm'})
        find.assert_any_call({'repo_id': 'repo1', 'unit_type_id': 'srpm'})

        self.assertEqual(repo_col.update.call_count, 1)
        repo_col.update.assert_called_once_with(
            {'id': 'repo1'},
            {'$set': {'content_unit_counts': {'rpm': 6, 'srpm': 6}}},
            safe=True
        )

    def test_rebuild_default_all_repos(self, mock_get_assoc_col, mock_get_repo_col):
        repo_col = mock_get_repo_col.return_value
        repo_col.find.return_value = [{'id': 'repo1'}, {'id': 'repo2'}]

        assoc_col = mock_get_assoc_col.return_value
        # don't return any type IDs
        assoc_col.find.return_value.distinct.return_value = []

        self.manager.rebuild_content_unit_counts()

        # makes sure it found these 2 repos and tried to operate on them
        assoc_col.find.assert_any_call({'repo_id': 'repo1'})
        assoc_col.find.assert_any_call({'repo_id': 'repo2'})
        self.assertEqual(assoc_col.find.call_count, 2)


@mock.patch('pulp.server.db.migrations.lib.managers.serializers.Repository')
@mock.patch('pulp.server.db.migrations.lib.managers.models.Repository.objects')
@mock.patch('pulp.server.db.migrations.lib.managers.RepoImporter.get_collection')
class TestRepoMangerFindWithImporterType(base.PulpServerTests):
    """
    Tests for finding repositories by importer type.
    """

    def test_find_with_importer_type(self, mock_importer_coll, mock_repo_qs, mock_repo_ser):
        """
        Ensure that repos are found and importers are placed into them.
        """
        mock_repos = {'repo_id': 'repo-a'}
        mock_importers = [{'id': 'imp1', 'repo_id': 'repo-a'}]
        mock_importer_coll().find.return_value = mock_importers
        mock_repo_ser().data = mock_repos

        repos = managers.RepoManager().find_with_importer_type('mock-imp-type')
        self.assertEqual(1, len(repos))

        self.assertEqual(repos[0]['repo_id'], 'repo-a')
        self.assertEqual(1, len(repos[0]['importers']))
        self.assertEqual(repos[0]['importers'][0]['id'], 'imp1')
