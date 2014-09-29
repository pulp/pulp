"""
This module contains tests for the pulp.server.webservices.dispatch module.
"""
from datetime import datetime
import json
import uuid

import mock

from .... import base
from pulp.common import constants
from pulp.devel.unit.server.base import PulpWebservicesTests
from pulp.devel.unit.util import compare_dict
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.auth import authorization
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server.db.model.resources import Worker
from pulp.server.exceptions import MissingResource
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers import dispatch as dispatch_controller


class TestTaskResource(PulpWebservicesTests):
    """
    Test the TaskResource class.
    """
    def setUp(self):
        super(TestTaskResource, self).setUp()
        TaskStatus.get_collection().remove()
        self.task_resource = dispatch_controller.TaskResource()

    def tearDown(self):
        super(TestTaskResource, self).tearDown()
        TaskStatus.get_collection().remove()

    @mock.patch('pulp.server.async.tasks.controller.revoke', autospec=True)
    def test_DELETE_celery_task(self, revoke):
        """
        Test the DELETE() method with a UUID that does not correspond to a UUID that the
        coordinator is aware of. This should cause a revoke call to Celery's Controller.
        """
        task_id = '1234abcd'
        TaskStatusManager.create_task_status(task_id)

        self.task_resource.DELETE(task_id)

        revoke.assert_called_once_with(task_id, terminate=True)

    def test_DELETE_completed_celery_task(self):
        """
        Test the DELETE() method does not change the state of a task that is already complete
        """
        task_id = '1234abcd'
        TaskStatusManager.create_task_status(task_id, state=constants.CALL_FINISHED_STATE)
        self.task_resource.DELETE(task_id)
        task_status = TaskStatusManager.find_by_task_id(task_id)
        self.assertEqual(task_status['state'], constants.CALL_FINISHED_STATE)

    def test_DELETE_non_existing_celery_task(self):
        """
        Test the DELETE() method raises a TaskNotFound exception if the task is not found.
        """
        task_id = '1234abcd'
        self.assertRaises(MissingResource, self.task_resource.DELETE, task_id)

    @mock.patch('pulp.server.async.tasks.controller.revoke', autospec=True)
    def test_DELETE_doesnt_cancel_spawned_celery_task(self, revoke):
        """
        Test the DELETE() which should cause a revoke call to Celery's Controller.
        This also tests that the spawned tasks are canceled as well.
        """
        task_id = '1234abcd'
        spawned_task_id = 'spawned_task'
        spawned_by_spawned_task_id = 'spawned_by_spawned_task'
        TaskStatusManager.create_task_status(task_id)
        TaskStatusManager.create_task_status(spawned_task_id)
        TaskStatusManager.create_task_status(spawned_by_spawned_task_id)
        TaskStatusManager.update_task_status(task_id, delta={'spawned_tasks': [spawned_task_id]})
        TaskStatusManager.update_task_status(spawned_task_id,
                                             delta={'spawned_tasks': [spawned_by_spawned_task_id]})
        self.task_resource.DELETE(task_id)

        self.assertEqual(revoke.call_count, 1)
        revoke.assert_called_once_with(task_id, terminate=True)

    def test_GET_has_correct_queue_attribute(self):
        task_id = '1234abcd'
        TaskStatusManager.create_task_status(task_id, worker_name='worker1')

        result = self.task_resource.GET(task_id)

        result_json = json.loads(result)
        self.assertTrue('queue' in result_json)
        self.assertTrue(result_json['queue'] == 'worker1.dq')

    def test_GET_has_correct_worker_name_attribute(self):
        task_id = '1234abcd'
        TaskStatusManager.create_task_status(task_id, worker_name='worker1')

        result = self.task_resource.GET(task_id)

        result_json = json.loads(result)
        self.assertTrue('worker_name' in result_json)
        self.assertTrue(result_json['worker_name'] == 'worker1')

    def test_GET_has_correct_task_id_attribute(self):
        task_id = '1234abcd'
        TaskStatusManager.create_task_status(task_id, worker_name='worker1')

        result = self.task_resource.GET(task_id)

        result_json = json.loads(result)
        self.assertTrue('task_id' in result_json)
        self.assertTrue(result_json['task_id'] == task_id)


class TestTaskCollection(base.PulpWebserviceTests):
    """
    Test the TaskCollection class.
    """
    def test_GET_celery_tasks(self):
        """
        Test the GET() method to get all current tasks.
        """
        # Populate a couple of task statuses
        task_id1 = str(uuid.uuid4())
        worker_1 = 'worker_1'
        state1 = 'waiting'

        task_id2 = str(uuid.uuid4())
        worker_2 = 'worker_2'
        state2 = 'running'
        tags = ['random', 'tags']

        TaskStatusManager.create_task_status(task_id1, worker_1, tags, state1)
        TaskStatusManager.create_task_status(task_id2, worker_2, tags, state2)
        status, body = self.get('/v2/tasks/')

        # Validate
        self.assertEqual(200, status)
        self.assertTrue(len(body) == 2)
        for task in body:
            if task['task_id'] == task_id1:
                self.assertEqual(task['_href'],
                                 serialization.dispatch.task_result_href(task)['_href'])
                self.assertEquals(task['state'], state1)
                self.assertEqual(task['worker_name'], worker_1)
            else:
                self.assertEqual(task['_href'],
                                 serialization.dispatch.task_result_href(task)['_href'])
                self.assertEquals(task['state'], state2)
                self.assertEqual(task['worker_name'], worker_2)
        self.assertEquals(task['tags'], tags)

    def test_GET_celery_tasks_by_tags(self):
        """
        Test the GET() method to get all current tasks.
        """
        # Populate a few of task statuses
        task_id1 = str(uuid.uuid4())
        worker_1 = 'worker_1'
        state1 = 'waiting'
        tags1 = ['random', 'tags']

        task_id2 = str(uuid.uuid4())
        worker_2 = 'worker_2'
        state2 = 'running'
        tags2 = ['random', 'tags']

        task_id3 = str(uuid.uuid4())
        worker_3 = 'worker_3'
        state3 = 'running'
        tags3 = ['random']

        TaskStatusManager.create_task_status(task_id1, worker_1, tags1, state1)
        TaskStatusManager.create_task_status(task_id2, worker_2, tags2, state2)
        TaskStatusManager.create_task_status(task_id3, worker_3, tags3, state3)

        # Validate for tags
        status, body = self.get('/v2/tasks/?tag=random&tag=tags')
        self.assertEqual(200, status)
        self.assertTrue(len(body) == 2)
        for task in body:
            if task['task_id'] == task_id1:
                self.assertEquals(task['state'], state1)
                self.assertEqual(task['worker_name'], worker_1)
                self.assertEqual(task['tags'], tags1)
            else:
                self.assertEqual(task['task_id'], task_id2)
                self.assertEquals(task['state'], state2)
                self.assertEqual(task['worker_name'], worker_2)
                self.assertEquals(task['tags'], tags2)

        # Negative test
        status, body = self.get('/v2/tasks/?tag=non_existent')
        self.assertEqual(200, status)
        self.assertTrue(len(body) == 0)

    def test_GET_celery_task_by_id(self):
        """
        Test the GET() method to get a current task with given id.
        """
        # Populate a couple of task statuses
        task_id1 = str(uuid.uuid4())
        worker_1 = 'worker_1'
        state1 = 'waiting'

        task_id2 = str(uuid.uuid4())
        worker_2 = 'worker_2'
        state2 = 'running'
        tags = ['random', 'tags']

        TaskStatusManager.create_task_status(task_id1, worker_1, tags, state1)
        TaskStatusManager.create_task_status(task_id2, worker_2, tags, state2)
        status, body = self.get('/v2/tasks/%s/' % task_id2)

        # Validate
        self.assertEqual(200, status)
        self.assertTrue(isinstance(body, dict))
        self.assertEquals(body['state'], state2)
        self.assertEqual(body['worker_name'], worker_2)
        self.assertEquals(body['tags'], tags)

    def test_GET_celery_task_by_missing_id(self):
        """
        Test the GET() method to get a current task with given id.
        """
        # Populate a couple of task statuses
        task_id1 = str(uuid.uuid4())
        worker_1 = 'worker_1'
        state1 = 'waiting'
        tags = ['random', 'tags']

        TaskStatusManager.create_task_status(task_id1, worker_1, tags, state1)
        non_existing_task_id = str(uuid.uuid4())
        status, body = self.get('/v2/tasks/%s/' % non_existing_task_id)

        # Validate
        self.assertEqual(404, status)
        self.assertTrue(isinstance(body, dict))
        self.assertTrue('Missing resource' in body['error_message'])
        self.assertTrue(non_existing_task_id in body['error_message'])


class SearchTaskCollectionTests(PulpWebservicesTests):

    def get_task(self):
        return {u'task_id': u'foo',
                u'spawned_tasks': [u'bar', u'baz']}

    @mock.patch('pulp.server.webservices.controllers.dispatch.SearchTaskCollection.'
                '_get_query_results_from_get', autospec=True)
    def test_get(self, mock_get_results):
        search_controller = dispatch_controller.SearchTaskCollection()
        mock_get_results.return_value = [self.get_task()]
        processed_tasks_json = search_controller.GET()

        # Mimic the processing
        updated_task = dispatch_controller.task_serializer(self.get_task())
        processed_tasks = json.loads(processed_tasks_json)
        compare_dict(updated_task, processed_tasks[0])

        #validate the permissions
        self.validate_auth(authorization.READ)

    @mock.patch('pulp.server.webservices.controllers.dispatch.SearchTaskCollection.'
                '_get_query_results_from_post', autospec=True)
    def test_post(self, mock_get_results):
        search_controller = dispatch_controller.SearchTaskCollection()
        mock_get_results.return_value = [self.get_task()]
        processed_tasks_json = search_controller.POST()

        # Mimic the processing
        updated_task = dispatch_controller.task_serializer(self.get_task())
        processed_tasks = json.loads(processed_tasks_json)
        compare_dict(updated_task, processed_tasks[0])

        #validate the permissions
        self.validate_auth(authorization.READ)
