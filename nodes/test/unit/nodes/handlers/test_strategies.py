
from unittest import TestCase

from mock import Mock, patch

from pulp_node.handlers.strategies import HandlerStrategy
from pulp_node.handlers.reports import SummaryReport
from pulp_node.reports import RepositoryReport
from pulp_node import constants


class TestStrategy(TestCase):

    @patch('pulp_node.handlers.model.Repository.run_synchronization')
    def test_synchronize_repository_reporting(self, fake_synchronization):
        repo_id = '1234'
        added = 300
        updated = 0
        removed = 0
        errors = [
            {'details': {'A': 1, 'B': 2}, 'error_id': 1},
            {'details': {'A': 10, 'B': 20}, 'error_id': 2}
        ]
        sources = {
            'downloads': {
                'content-world': {'total_failed': 2, 'total_succeeded': 100},
                'content-galaxy': {'total_failed': 0, 'total_succeeded': 200}
            },
            'total_sources': 10
        }

        fake_request = Mock()
        fake_request.options = {constants.SKIP_CONTENT_UPDATE_KEYWORD: False}
        fake_request.cancelled.return_value = False
        fake_request.summary = SummaryReport()
        fake_request.summary.repository[repo_id] = RepositoryReport(repo_id)
        fake_synchronization.return_value = {
            'added_count': added,
            'updated_count': updated,
            'removed_count': removed,
            'details': {
                'errors': errors,
                'sources': sources
            }
        }

        # test
        strategy = HandlerStrategy()
        strategy._synchronize_repository(fake_request, repo_id)

        # validation
        expected = {
            'errors': errors,
            'repositories': [
                {
                    'repo_id': repo_id,
                    'action': 'pending',
                    'units': {'updated': updated, 'added': added, 'removed': removed},
                    'sources': sources
                }
            ]}

        self.assertEqual(fake_request.summary.dict(), expected)