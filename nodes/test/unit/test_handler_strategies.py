# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


from unittest import TestCase
from mock import Mock, patch

from pulp_node.handlers.strategies import *
from pulp_node.error import *
from pulp_node.handlers.reports import SummaryReport, HandlerProgress


class TestConduit:

    update_progress = Mock()


class TestRepo:

    def __init__(self, repo_id):
        self.repo_id = repo_id



REPO_ID = 'foo'
TYPE_ID = 'random_importer'
CONDUIT = TestConduit()
BINDING = dict(repo_id=REPO_ID, details={})


class TestBase(TestCase):

    def test_abstract(self):
        # Setup
        progress = HandlerProgress(CONDUIT)
        summary = SummaryReport()
        # Test
        strategy = HandlerStrategy(progress, summary)
        # Verify
        self.assertEqual(strategy.progress_report, progress)
        self.assertEqual(strategy.progress_report.conduit, CONDUIT)
        self.assertEqual(strategy.summary_report, summary)
        self.assertRaises(NotImplementedError, strategy._synchronize, None)

    @patch('pulp_node.handlers.validation.Validator.validate', side_effect=ValueError())
    def test_synchronize_validation_exception(self, *unused):
        # Setup
        progress = HandlerProgress(CONDUIT)
        summary = SummaryReport()
        # Test
        strategy = HandlerStrategy(progress, summary)
        strategy.synchronize([], {})
        # Verify
        self.assertEqual(len(summary.errors), 1)
        self.assertEqual(summary.errors[0].error_id, CaughtException.ERROR_ID)

    @patch('pulp_node.handlers.validation.Validator.validate', side_effect=ImporterNotInstalled(REPO_ID, TYPE_ID))
    def test_synchronize_validation_node_error(self, *unused):
        # Setup
        progress = HandlerProgress(CONDUIT)
        summary = SummaryReport()
        # Test
        strategy = HandlerStrategy(progress, summary)
        strategy.synchronize([], {})
        # Verify
        self.assertEqual(len(summary.errors), 1)
        self.assertEqual(summary.errors[0].error_id, ImporterNotInstalled.ERROR_ID)

    @patch('pulp_node.handlers.model.RepositoryOnChild.fetch', side_effect=ValueError())
    def test_synchronize_merge_exception(self, *unused):
        # Setup
        progress = HandlerProgress(CONDUIT)
        summary = SummaryReport()
        # Test
        strategy = HandlerStrategy(progress, summary)
        strategy.synchronize([], {})
        # Verify
        self.assertEqual(len(summary.errors), 1)
        self.assertEqual(summary.errors[0].error_id, CaughtException.ERROR_ID)

    @patch('pulp_node.handlers.model.RepositoryOnChild.fetch', side_effect=ValueError())
    def test_merge_repositories_exception(self, *unused):
        # Setup
        progress = HandlerProgress(CONDUIT)
        summary = SummaryReport()
        # Test
        strategy = HandlerStrategy(progress, summary)
        strategy._merge_repositories([BINDING])
        # Verify
        self.assertEqual(len(summary.errors), 1)
        self.assertEqual(summary.errors[0].error_id, CaughtException.ERROR_ID)

    @patch('pulp_node.handlers.model.RepositoryOnChild.fetch', side_effect=RepoSyncRestError(REPO_ID, 401))
    def test_merge_repositories_node_error(self, *unused):
        # Setup
        progress = HandlerProgress(CONDUIT)
        summary = SummaryReport()
        # Test
        strategy = HandlerStrategy(progress, summary)
        strategy._merge_repositories([BINDING])
        # Verify
        self.assertEqual(len(summary.errors), 1)
        self.assertEqual(summary.errors[0].error_id, RepoSyncRestError.ERROR_ID)
        self.assertEqual(summary.errors[0].details['http_code'], 401)

    @patch('pulp_node.handlers.model.RepositoryOnChild.fetch_all', return_value=[TestRepo(123)])
    @patch('pulp_node.handlers.model.RepositoryOnChild.delete', side_effect=ValueError())
    def test_delete_repositories_exception(self, *unused):
        # Setup
        progress = HandlerProgress(CONDUIT)
        summary = SummaryReport()
        # Test
        strategy = HandlerStrategy(progress, summary)
        strategy._delete_repositories([BINDING])
        # Verify
        self.assertEqual(len(summary.errors), 1)
        self.assertEqual(summary.errors[0].error_id, CaughtException.ERROR_ID)

    @patch('pulp_node.handlers.model.RepositoryOnChild.fetch_all', return_value=[TestRepo(123)])
    @patch('pulp_node.handlers.model.RepositoryOnChild.delete', side_effect=CaughtException(ValueError()))
    def test_delete_repositories_node_error(self, *unused):
        # Setup
        progress = HandlerProgress(CONDUIT)
        summary = SummaryReport()
        # Test
        strategy = HandlerStrategy(progress, summary)
        strategy._delete_repositories([BINDING])
        # Verify
        self.assertEqual(len(summary.errors), 1)
        self.assertEqual(summary.errors[0].error_id, CaughtException.ERROR_ID)

    def test_strategy_factory(self):
        for name, strategy in STRATEGIES.items():
            self.assertEqual(find_strategy(name), strategy)
        self.assertRaises(StrategyUnsupported, find_strategy, '---')