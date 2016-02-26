"""
This module contains tests for the pulp.server.webservices.views.task_groups module.
"""
import mock

from .base import assert_auth_DELETE, assert_auth_READ
from pulp.common.compat import unittest
from pulp.server.exceptions import MissingResource

from pulp.server.webservices.views.task_groups import TaskGroupView, TaskGroupSummaryView


class MockQuerySet(object):

    def __init__(self, list_of_objects):
        self.items = list_of_objects
        self.i = 0
        self.n = len(self.items)

    def count(self):
        return len(self.items)

    def filter(self, state=None):
        filtered_list = []
        for item in self.items:
            if item['state'] == state:
                filtered_list.append(item)
        return MockQuerySet(filtered_list)


class TestTaskGroupView(unittest.TestCase):
    """
    Tests for TaskGroupView
    """
    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.task_groups.TaskStatus.objects')
    @mock.patch('pulp.server.webservices.views.task_groups.tasks')
    def test_delete_task_resource_nonexistant(self, mock_task, mock_objects):
        """
        Test delete task_group with no tasks
        """
        mock_request = mock.MagicMock()

        mock_objects.only.return_value.filter.return_value = []
        task_resource = TaskGroupView()

        self.assertRaises(MissingResource, task_resource.delete, mock_request, 'mock_task')

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.task_groups.TaskStatus.objects')
    @mock.patch('pulp.server.webservices.views.task_groups.tasks')
    @mock.patch(
        'pulp.server.webservices.views.task_groups.generate_json_response')
    def test_delete_task_resource(self, mock_resp, mock_task, mock_objects):
        """
        Test delete task_group with one task
        """
        mock_request = mock.MagicMock()
        task1 = mock.Mock(task_id='test_foo_path')
        task2 = mock.Mock(task_id='test_foo_path1')
        mock_objects.only.return_value.filter.return_value = [task1, task2]

        task_resource = TaskGroupView()

        response = task_resource.delete(mock_request, 'mock_task')

        self.assertEqual(mock_task.cancel.call_count, 2)

        mock_task.cancel.assert_any_call('test_foo_path')
        mock_task.cancel.assert_any_call('test_foo_path1')
        self.assertTrue(response is mock_resp.return_value)


class TestTaskGroupSummary(unittest.TestCase):
    """
    Tests for TaskGroupSummaryView
    """
    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.task_groups.TaskStatus.objects')
    @mock.patch(
        'pulp.server.webservices.views.task_groups.generate_json_response_with_pulp_encoder')
    def test_get_task_group_summary_nonexistant(self, mock_resp, mock_objects):
        """
        Test get task_group_summary with no tasks
        """

        mock_request = mock.MagicMock()
        mock_objects.return_value = MockQuerySet([])

        task_group_summary = TaskGroupSummaryView()
        response = task_group_summary.get(mock_request, 'mock_task')

        expected_content = {'accepted': 0, 'finished': 0, 'running': 0, 'canceled': 0,
                            'waiting': 0, 'skipped': 0, 'suspended': 0, 'error': 0, 'total': 0}
        mock_resp.assert_called_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.task_groups.TaskStatus.objects')
    @mock.patch(
        'pulp.server.webservices.views.task_groups.generate_json_response_with_pulp_encoder')
    def test_get_task_group_summary(self, mock_resp, mock_objects):
        """
        Test get task_group_summary with multiple tasks
        """
        mock_request = mock.MagicMock()
        mock_objects.return_value = MockQuerySet([{'id': 'mock_task', 'worker_name': 'mock',
                                                   'state': 'running'},
                                                  {'id': 'mock_task', 'worker_name': 'mock',
                                                   'state': 'finished'},
                                                  {'id': 'mock_task', 'worker_name': 'mock',
                                                   'state': 'waiting'}])

        task_group_summary = TaskGroupSummaryView()
        response = task_group_summary.get(mock_request, 'mock_task')

        expected_content = {'accepted': 0, 'finished': 1, 'running': 1, 'canceled': 0,
                            'waiting': 1, 'skipped': 0, 'suspended': 0, 'error': 0, 'total': 3}
        mock_resp.assert_called_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)
