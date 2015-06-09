from unittest import TestCase

from mock import patch

from pulp.server.managers.consumer.applicability import ApplicabilityRegenerationManager
from pulp.server.managers import factory as managers


class TestApplicabilityRegenerationManager(TestCase):

    @patch('pulp.server.managers.repo.query.RepoQueryManager.find_by_criteria')
    @patch('pulp.server.db.model.consumer.RepoProfileApplicability.get_collection')
    def test_regenerate_applicability_for_repos_batch_size(self, mock_get_collection,
                                                           mock_find_by_criteria):

        managers.initialize()
        applicability_manager = ApplicabilityRegenerationManager()
        repo_criteria = {'filters': None, 'sort': None, 'limit': None,
                         'skip': None, 'fields': None}
        mock_find_by_criteria.return_value = [{'id': 'fake-repo'}]

        applicability_manager.regenerate_applicability_for_repos(repo_criteria)

        # validate that batch size of 5 is used

        mock_get_collection.return_value.find.return_value.batch_size.assert_called_with(5)
