"""
This module contains tests for the pulp.server.async.task_status_manager module.
"""

import uuid

from datetime import datetime
from mongoengine import NotUniqueError, ValidationError

import mock

from ... import base

from pulp.common import constants, dateutils
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server import exceptions


class TaskStatusManagerTests(base.PulpServerTests):
    """
    Test the TaskStatusManager class.
    """
    def clean(self):
        super(TaskStatusManagerTests, self).clean()
        TaskStatus.objects().delete()

    def get_random_uuid(self):
        return str(uuid.uuid4())

    def test_create_task_status(self):
        """
        Tests that TaskStatus creation with valid data is successful.
        """
        task_id = self.get_random_uuid()
        worker_name = 'a_worker_name'
        tags = ['test-tag1', 'test-tag2']
        state = 'waiting'

        created = TaskStatus(task_id, worker_name, tags, state).save()

        task_statuses = TaskStatus.objects()
        self.assertEqual(1, len(task_statuses))

        task_status = task_statuses[0]
        self.assertEqual(task_id, task_status['task_id'])
        self.assertEqual(worker_name, task_status['worker_name'])
        self.assertEqual(tags, task_status['tags'])
        self.assertEqual(state, task_status['state'])

        self.assertEqual(task_id, created['task_id'])
        self.assertEqual(tags, created['tags'])
        self.assertEqual(state, created['state'])

    def test_create_task_status_defaults(self):
        """
        Tests TaskStatus creation with minimal information, to ensure that defaults are handled
        properly.
        """
        task_id = self.get_random_uuid()

        TaskStatus(task_id).save()

        task_statuses = TaskStatus.objects()
        self.assertEqual(1, len(task_statuses))
        self.assertEqual(task_id, task_statuses[0]['task_id'])
        self.assertEqual(None, task_statuses[0]['worker_name'])
        self.assertEqual([], task_statuses[0]['tags'])
        self.assertEqual('waiting', task_statuses[0]['state'])

    def test_create_task_status_invalid_task_id(self):
        """
        Test that TaskStatus creation with an invalid task id raises the correct error.
        """
        try:
            TaskStatus(None).save()
        except ValidationError, e:
            self.assertTrue('task_id' in e.message)
        else:
            self.fail('Invalid ID did not raise an exception')

    def test_create_task_status_duplicate_task_id(self):
        """
        Tests TaskStatus creation with a duplicate task id.
        """
        task_id = self.get_random_uuid()

        TaskStatus(task_id).save()
        try:
            TaskStatus(task_id).save()
        except NotUniqueError, e:
            self.assertTrue(task_id in e.message)
        else:
            self.fail('Task status with a duplicate task id did not raise an exception')

    def test_create_task_status_invalid_attributes(self):
        """
        Tests that TaskStatus creation with invalid attributes
        results in an error
        """
        task_id = self.get_random_uuid()
        worker_name = ['not a string']
        tags = 'not a list'
        state = 1
        try:
            TaskStatus(task_id, worker_name, tags, state).save()
        except ValidationError, e:
            self.assertTrue('tags' in e.message)
            self.assertTrue('state' in e.message)
            self.assertTrue('worker_name' in e.message)
        else:
            self.fail('Invalid attributes did not cause create to raise an exception')

    def test_update_task_status(self):
        """
        Tests the successful operation of update_task_status().
        """
        task_id = self.get_random_uuid()
        worker_name = 'special_worker_name'
        tags = ['test-tag1', 'test-tag2']
        state = 'waiting'
        TaskStatus(task_id, worker_name, tags, state).save()
        now = datetime.now(dateutils.utc_tz())
        start_time = dateutils.format_iso8601_datetime(now)
        delta = {'start_time': start_time,
                 'state': 'running',
                 'disregard': 'ignored',
                 'progress_report': {'report-id': 'my-progress'}}

        updated = TaskStatusManager.update_task_status(task_id, delta)

        task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertEqual(task_status['start_time'], delta['start_time'])
        # Make sure that parse_iso8601_datetime is able to parse the start_time without errors
        dateutils.parse_iso8601_datetime(task_status['start_time'])
        self.assertEqual(task_status['state'], delta['state'])
        self.assertEqual(task_status['progress_report'], delta['progress_report'])
        self.assertEqual(task_status['worker_name'], worker_name)
        self.assertEqual(updated['start_time'], delta['start_time'])
        self.assertEqual(updated['state'], delta['state'])
        self.assertEqual(updated['progress_report'], delta['progress_report'])
        self.assertTrue('disregard' not in updated)
        self.assertTrue('disregard' not in task_status)

    def test_update_missing_task_status(self):
        """
        Tests updating a task status that doesn't exist raises the appropriate exception.
        """
        task_id = self.get_random_uuid()
        try:
            TaskStatusManager.update_task_status(task_id, {})
        except exceptions.MissingResource, e:
            self.assertTrue(task_id == e.resources['resource_id'])
        else:
            self.fail('Exception expected')

    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_find_by_criteria(self, mock_query):
        criteria = Criteria()
        TaskStatusManager.find_by_criteria(criteria)
        mock_query.assert_called_once_with(criteria)

    def test_set_accepted(self):
        task_id = self.get_random_uuid()
        TaskStatus(task_id, state=constants.CALL_WAITING_STATE).save()

        TaskStatusManager.set_task_accepted(task_id)
        task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertTrue(task_status['state'], constants.CALL_ACCEPTED_STATE)

    @mock.patch('pulp.common.dateutils.format_iso8601_datetime')
    def test_set_succeeded(self, mock_date):
        task_id = self.get_random_uuid()
        TaskStatus(task_id).save()

        result = 'done'
        now = '2014-11-21 05:21:38.829678'
        mock_date.return_value = now

        TaskStatusManager.set_task_succeeded(task_id, result)
        task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertTrue(task_status['state'], constants.CALL_FINISHED_STATE)
        self.assertTrue(task_status['finish_time'], now)
        self.assertTrue(task_status['result'], result)

    def test_set_succeeded_with_timestamp(self):
        task_id = self.get_random_uuid()
        TaskStatus(task_id).save()

        result = 'done'
        now = '2014-11-21 05:21:38.829678'

        TaskStatusManager.set_task_succeeded(task_id, result, timestamp=now)
        task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertTrue(task_status['state'], constants.CALL_FINISHED_STATE)
        self.assertTrue(task_status['finish_time'], now)
        self.assertTrue(task_status['result'], result)

    @mock.patch('pulp.common.dateutils.format_iso8601_datetime')
    def test_set_failed(self, mock_date):
        task_id = self.get_random_uuid()
        TaskStatus(task_id).save()

        traceback = 'abcdef'
        finished = '2014-11-21 05:21:38.829678'
        mock_date.return_value = finished

        TaskStatusManager.set_task_failed(task_id, traceback)
        task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertTrue(task_status['state'], constants.CALL_ERROR_STATE)
        self.assertTrue(task_status['finish_time'], finished)
        self.assertTrue(task_status['traceback'], traceback)

    def test_set_failed_with_timestamp(self):
        task_id = self.get_random_uuid()
        TaskStatus(task_id).save()

        traceback = 'abcdef'
        finished = '2014-11-21 05:21:38.829678'

        TaskStatusManager.set_task_failed(task_id, traceback=traceback, timestamp=finished)
        task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertTrue(task_status['state'], constants.CALL_ERROR_STATE)
        self.assertTrue(task_status['finish_time'], finished)
        self.assertTrue(task_status['traceback'], traceback)

    @mock.patch('pulp.common.dateutils.format_iso8601_datetime')
    @mock.patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_set_started(self, mock_objects, mock_date):
        test_date = '2014-11-21 05:21:38.829678'
        mock_date.return_value = test_date
        test_objects = mock.Mock()
        mock_objects.return_value = test_objects
        call = mock._Call()

        TaskStatusManager.set_task_started(task_id='test-task-id')

        self.assertEqual(test_objects.update_one.call_args_list, [call(set__start_time='2014-11-21 05:21:38.829678'),
                                                                  call(set__state='running')])

    @mock.patch('pulp.server.db.model.dispatch.TaskStatus.objects')
    def test_set_started_with_timestamp(self, mock_objects):
        test_date = '2014-11-21 05:21:38.829678'
        test_objects = mock.Mock()
        mock_objects.return_value = test_objects
        call = mock._Call()

        TaskStatusManager.set_task_started(task_id='test-task-id', timestamp=test_date)

        self.assertEqual(test_objects.update_one.call_args_list, [call(set__start_time='2014-11-21 05:21:38.829678'),
                                                                  call(set__state='running')])
