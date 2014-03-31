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

from base import Task as TestTask, TaskResult as TestReport
from pulp_node.handlers.strategies import *
from pulp_node.error import *
from pulp_node.handlers.model import Repository
from pulp_node.handlers.reports import SummaryReport, HandlerProgress


class TestConduit:

    def __init__(self, cancel_on=0):
        self.cancel_on = cancel_on
        self.cancelled_call_count = 0

    update_progress = Mock()

    def cancelled(self):
        self.cancelled_call_count += 1
        return self.cancel_on and self.cancelled_call_count >= self.cancel_on


class TestResponse:

    def __init__(self, http_code, body=None):
        self.response_code = http_code
        self.response_body = body


class TestRepo:

    def __init__(self, repo_id):
        self.repo_id = repo_id



REPO_ID = 'foo'
TYPE_ID = 'random_importer'
TASK_ID = 'test_task'

NODE_CERTIFICATE = """
    -----BEGIN RSA PRIVATE KEY-----
    PULPROCKSPULPROCKSPULPROCKS
    -----END RSA PRIVATE KEY-----
    -----BEGIN CERTIFICATE-----
    PULPROCKSPULPROCKSPULPROCKS
    -----END CERTIFICATE-----
"""

PARENT_SETTINGS = {
    constants.HOST: 'pulp.redhat.com',
    constants.PORT: 443,
    constants.NODE_CERTIFICATE: NODE_CERTIFICATE,
}


class TestBase(TestCase):

    def request(self, cancel_on=0):
        conduit = TestConduit(cancel_on)
        progress = HandlerProgress(conduit)
        summary = SummaryReport()
        request = Request(
            conduit=conduit,
            progress=progress,
            summary=summary,
            bindings=[dict(repo_id=REPO_ID, details={})],
            scope=constants.NODE_SCOPE,
            options={constants.PARENT_SETTINGS: PARENT_SETTINGS}
        )
        return request

    def test_abstract(self):
        # Test
        strategy = HandlerStrategy()
        # Verify
        self.assertRaises(NotImplementedError, strategy._synchronize, None)

    @patch('pulp_node.handlers.validation.Validator.validate', side_effect=ValueError())
    def test_synchronize_validation_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = HandlerStrategy()
        strategy.synchronize(request)
        # Verify
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, CaughtException.ERROR_ID)

    @patch('pulp_node.handlers.validation.Validator.validate', side_effect=ImporterNotInstalled(REPO_ID, TYPE_ID))
    def test_synchronize_validation_node_error(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = HandlerStrategy()
        strategy.synchronize(request)
        # Verify
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, ImporterNotInstalled.ERROR_ID)

    @patch('pulp_node.handlers.model.Repository.fetch', side_effect=ValueError())
    def test_synchronize_merge_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = HandlerStrategy()
        strategy.synchronize(request)
        # Verify
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, CaughtException.ERROR_ID)

    @patch('pulp_node.handlers.model.Repository.fetch', side_effect=ValueError())
    def test_merge_repositories_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = HandlerStrategy()
        strategy._merge_repositories(request)
        # Verify
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, CaughtException.ERROR_ID)

    @patch('pulp_node.handlers.model.Repository.fetch', side_effect=RepoSyncRestError(REPO_ID, 401))
    def test_merge_repositories_node_error(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = HandlerStrategy()
        strategy._merge_repositories(request)
        # Verify
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, RepoSyncRestError.ERROR_ID)
        self.assertEqual(request.summary.errors[0].details['http_code'], 401)

    @patch('pulp_node.handlers.model.Repository.fetch_all', return_value=[TestRepo('123')])
    @patch('pulp_node.handlers.model.Repository.delete', side_effect=ValueError())
    def test_delete_repositories_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = HandlerStrategy()
        strategy._delete_repositories(request)
        # Verify
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, CaughtException.ERROR_ID)

    @patch('pulp_node.handlers.model.Repository.fetch_all', return_value=[TestRepo(123)])
    @patch('pulp_node.handlers.model.Repository.delete', side_effect=CaughtException(ValueError()))
    def test_delete_repositories_node_error(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = HandlerStrategy()
        strategy._delete_repositories(request)
        # Verify
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, CaughtException.ERROR_ID)

    @patch('pulp_node.handlers.model.Repository.fetch_all', return_value=[REPO_ID])
    def test_merge_repositories_cancelled(self, *unused):
        # Setup
        request = self.request(1)
        # Test
        strategy = HandlerStrategy()
        strategy._merge_repositories(request)
        # Verify
        self.assertEqual(len(request.summary.errors), 0)
        self.assertEqual(len(request.summary.repository), 1)
        repository = request.summary.repository[REPO_ID]
        self.assertEqual(repository.repo_id, REPO_ID)
        self.assertEqual(repository.action, RepositoryReport.CANCELLED)
        units = repository.units
        self.assertEqual(units.added, 0)
        self.assertEqual(units.updated, 0)
        self.assertEqual(units.removed, 0)

    @patch('pulp_node.handlers.model.Repository.fetch_all', return_value=[TestRepo(REPO_ID)])
    def test_delete_repositories_cancelled(self, *unused):
        # Setup
        request = self.request(1)
        # Test
        strategy = HandlerStrategy()
        strategy._delete_repositories(request)
        # Verify
        self.assertEqual(len(request.summary.errors), 0)
        self.assertEqual(len(request.summary.repository), 1)
        repository = request.summary.repository[REPO_ID]
        self.assertEqual(repository.repo_id, REPO_ID)
        self.assertEqual(repository.action, RepositoryReport.CANCELLED)
        units = repository.units
        self.assertEqual(units.added, 0)
        self.assertEqual(units.updated, 0)
        self.assertEqual(units.removed, 0)

    @patch('pulp.bindings.repository.RepositoryActionsAPI.sync',
           return_value=TestResponse(202, TestReport(TASK_ID)))
    @patch('pulp.bindings.tasks.TasksAPI.cancel_task',
           return_value=TestResponse(200))
    def test_model_repo_sync_cancelled(self, mock_cancel, *unused):
        # Setup
        conduit = TestConduit(1)
        # Test
        repository = Repository(REPO_ID)
        options = options={constants.PARENT_SETTINGS: PARENT_SETTINGS}
        repository.run_synchronization(None, conduit.cancelled, options)
        # Verify
        mock_cancel.assert_called_with(TASK_ID)

    def test_strategy_factory(self):
        for name, strategy in STRATEGIES.items():
            self.assertEqual(find_strategy(name), strategy)
        self.assertRaises(StrategyUnsupported, find_strategy, '---')
