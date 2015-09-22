"""
This module contains tests for the pulp.server.webservices.views.tasks module.
"""
import mock

from mongoengine.queryset import DoesNotExist

from .base import assert_auth_DELETE, assert_auth_READ
from pulp.common.compat import unittest
from pulp.server import exceptions as pulp_exceptions
from pulp.server.db import models
from pulp.server.exceptions import MissingResource
from pulp.server.webservices.views import util
from pulp.server.webservices.views.tasks import (TaskCollectionView, TaskResourceView,
                                                 TaskSearchView, task_serializer)


@mock.patch('pulp.server.webservices.views.tasks.serial_dispatch')
def test_task_serializer(mock_seralization):
    """
    Test task_serializer helper function.
    """
    mock_seralization.task_status.return_value = {'status': 'mock'}
    mock_seralization.spawned_tasks.return_value = {'spawned_task': 'mock'}
    mock_seralization.task_result_href.return_value = {'_href': '/mock/path/'}

    task = {'task_id': 'mock_task'}
    serialized_task = task_serializer(task)
    mock_seralization.task_status.assert_called_once()
    mock_seralization.spawned_tasks.assert_called_once()
    mock_seralization.task_result_href.assert_called_once()

    expected_task = {'status': 'mock', 'spawned_task': 'mock', '_href': '/mock/path/'}
    if serialized_task != expected_task:
        raise AssertionError("Task serializer did not generate expected task. \n" +
                             "Task: {}, \nExpected Task: {}".format(serialized_task, expected_task))


class TestTaskSearchView(unittest.TestCase):
    """
    Test the TaskSearchView class.
    """
    def test_class_attribute(self):
        """
        Ensure that the TaskSearchView class has the correct class attributes.
        """
        self.assertEqual(TaskSearchView.response_builder,
                         util.generate_json_response_with_pulp_encoder)
        self.assertEqual(TaskSearchView.model, models.TaskStatus)
        self.assertEqual(TaskSearchView.serializer, task_serializer)


class TestTaskCollection(unittest.TestCase):
    """
    Tests for TaskCollectionView.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.tasks.task_serializer')
    @mock.patch('pulp.server.webservices.views.tasks.TaskStatus')
    @mock.patch('pulp.server.webservices.views.tasks.generate_json_response_with_pulp_encoder')
    def test_get_task_collection(self, mock_resp, mock_task_status, mock_task_serializer):
        """
        Test get task_collection with tags.
        """

        mock_request = mock.MagicMock()
        mock_request.GET.getlist.return_value = ['mock_tag_1', 'mock_tag_2']
        mock_task_status.objects.return_value = ['mock_1', 'mock_2']
        mock_task_serializer.side_effect = lambda x: x

        task_collection = TaskCollectionView()
        response = task_collection.get(mock_request)

        mock_task_status.objects.assert_called_once_with(tags__all=['mock_tag_1', 'mock_tag_2'])
        mock_resp.assert_called_once_with(['mock_1', 'mock_2'])
        mock_task_serializer.assert_has_calls([mock.call('mock_1'), mock.call('mock_2')])
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.tasks.task_serializer')
    @mock.patch('pulp.server.webservices.views.tasks.TaskStatus')
    @mock.patch('pulp.server.webservices.views.tasks.generate_json_response_with_pulp_encoder')
    def test_get_task_collection_no_tags(self, mock_resp, mock_task_status, mock_task_serializer):
        """
        Test get task_collection with no tags.
        """

        mock_request = mock.MagicMock()
        mock_request.GET.getlist.return_value = []
        mock_task_status.objects.return_value = ['mock_1', 'mock_2']
        mock_task_serializer.side_effect = lambda x: x

        task_collection = TaskCollectionView()
        response = task_collection.get(mock_request)

        mock_task_status.objects.assert_called_once_with()
        mock_resp.assert_called_once_with(['mock_1', 'mock_2'])
        mock_task_serializer.assert_has_calls([mock.call('mock_1'), mock.call('mock_2')])
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.tasks.TaskStatus')
    def test_delete_task_collection(self, mock_task_status):
        """
        Test get task_collection with tags.
        """

        mock_request = mock.MagicMock()
        mock_request.GET.getlist.return_value = ['finished']

        task_collection = TaskCollectionView()
        task_collection.delete(mock_request)

        mock_task_status.objects.assert_called_once_with(state='finished')

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.tasks.TaskStatus')
    def test_delete_task_collection_no_status(self, mock_task_status):
        """
        Test get task_collection with no state.
        """

        mock_request = mock.MagicMock()
        mock_request.GET.getlist.return_value = []

        task_collection = TaskCollectionView()
        with self.assertRaises(pulp_exceptions.PulpCodedForbiddenException):
            task_collection.delete(mock_request)


class TestTaskResource(unittest.TestCase):
    """
    View for a single task.
    """

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.tasks.Worker')
    @mock.patch('pulp.server.webservices.views.tasks.task_serializer')
    @mock.patch('pulp.server.webservices.views.tasks.TaskStatus')
    @mock.patch('pulp.server.webservices.views.tasks.generate_json_response_with_pulp_encoder')
    def test_get_task_resource(self, mock_resp, mock_task_status, mock_task_serial, mock_worker):
        """
        Test get task_resource with an existing task.
        """
        def mock_serializer(arg):
            return arg

        mock_request = mock.MagicMock()
        mock_task_status.objects.get.return_value = {'id': 'mock_task', 'worker_name': 'mock'}
        mock_task_serial.side_effect = mock_serializer
        mock_worker_inst = mock.MagicMock()
        mock_worker_inst.queue_name = 'mock_q_name'
        mock_worker.return_value = mock_worker_inst

        task_resource = TaskResourceView()
        response = task_resource.get(mock_request, 'mock_task')

        expected_content = {'id': 'mock_task', 'worker_name': 'mock', 'queue': 'mock_q_name'}
        mock_resp.assert_called_once_with(expected_content)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_READ())
    @mock.patch('pulp.server.webservices.views.tasks.TaskStatus')
    def test_get_task_resource_invalid_task(self, mock_task_status):
        """
        Test get task_resource with an non-existing task.
        """

        mock_request = mock.MagicMock()
        mock_task_status.objects.get.side_effect = DoesNotExist()

        task_resource = TaskResourceView()
        try:
            task_resource.get(mock_request, 'mock_task')
        except MissingResource, response:
            pass
        else:
            AssertionError("MissingResource should be raised with non-existing task.")

        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data, {'resources': {'resource_id': 'mock_task'}})

    @mock.patch('pulp.server.webservices.views.decorators._verify_auth',
                new=assert_auth_DELETE())
    @mock.patch('pulp.server.webservices.views.tasks.tasks')
    @mock.patch('pulp.server.webservices.views.tasks.generate_json_response')
    def test_delete_task_resource(self, mock_resp, mock_task):
        """
        View should dispatch a task.cancel with the task id.
        """
        mock_request = mock.MagicMock()
        task_resource = TaskResourceView()

        response = task_resource.delete(mock_request, 'mock_task_id')
        mock_task.cancel.assert_called_once_with('mock_task_id')
        mock_resp.assert_called_once_with(None)
        self.assertTrue(response is mock_resp.return_value)
