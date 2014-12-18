"""
This module contains tests for pulp.server.db.model.dispatch.TaskStatus model.
"""

import uuid

from datetime import datetime
from mongoengine import NotUniqueError, ValidationError
from pymongo import DESCENDING

import mock

from ... import base

from pulp.common import constants, dateutils
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.dispatch import TaskStatus


class TaskStatusTests(base.PulpServerTests):
    """
    Test the TaskStatus class functions.
    """
    def clean(self):
        super(TaskStatusTests, self).clean()
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

    def test_task_status_update(self):
        """
        Tests the successful operation of task status update.
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
                 'progress_report': {'report-id': 'my-progress'}}

        TaskStatus.objects(task_id=task_id).update_one(set__start_time=delta['start_time'],
                                                       set__state=delta['state'],
                                                       set__progress_report=delta['progress_report'])

        task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertEqual(task_status['start_time'], delta['start_time'])
        # Make sure that parse_iso8601_datetime is able to parse the start_time without errors
        dateutils.parse_iso8601_datetime(task_status['start_time'])
        self.assertEqual(task_status['state'], delta['state'])
        self.assertEqual(task_status['progress_report'], delta['progress_report'])
        self.assertEqual(task_status['worker_name'], worker_name)

    @mock.patch('pulp.server.db.model.base.CriteriaQuerySet.find_by_criteria')
    def test_find_by_criteria(self, mock_find_by_criteria):
        criteria = Criteria()
        TaskStatus.objects.find_by_criteria(criteria)
        mock_find_by_criteria.assert_called_once_with(criteria)

    def test_find_by_criteria_with_result(self):
        tags = ['test', 'tags']
        TaskStatus(task_id='1').save()
        TaskStatus(task_id='2', tags=tags).save()

        result = 'done'
        TaskStatus(task_id='3', tags=tags).save()

        TaskStatus.objects(task_id='3').update_one(set__state=constants.CALL_FINISHED_STATE,
                                                   set__result=result)

        filters = {'tags': tags, 'task_id': {'$in': ['1', '3']}}
        fields = ['task_id', 'tags', 'result']
        limit = 1
        sort = (('task_id', DESCENDING), )
        criteria = Criteria(filters=filters, fields=fields, limit=limit, sort=sort)
        query_set = TaskStatus.objects.find_by_criteria(criteria)
        self.assertEqual(len(query_set), 1)
        self.assertEqual(query_set[0].task_id, '3')
        self.assertEqual(query_set[0].result, result)
        task_state_default = constants.CALL_WAITING_STATE
        self.assertEqual(query_set[0].state, task_state_default)

    def test_set_accepted(self):
        task_id = self.get_random_uuid()
        TaskStatus(task_id, state=constants.CALL_WAITING_STATE).save()

        TaskStatus.objects(task_id=task_id, state=constants.CALL_WAITING_STATE).\
            update_one(set__state=constants.CALL_ACCEPTED_STATE)
        task_status = TaskStatus.objects.get(task_id=task_id)
        self.assertTrue(task_status['state'], constants.CALL_ACCEPTED_STATE)

    @mock.patch('pulp.common.dateutils.format_iso8601_datetime')
    def test_set_succeeded(self, mock_date):
        task_id = self.get_random_uuid()
        TaskStatus(task_id).save()

        result = 'done'
        now = '2014-11-21 05:21:38.829678'
        mock_date.return_value = now

        t = datetime.now(dateutils.utc_tz())
        finished = dateutils.format_iso8601_datetime(t)
        TaskStatus.objects(task_id=task_id).update_one(set__finish_time=finished,
                                                       set__state=constants.CALL_FINISHED_STATE,
                                                       set__result=result)
        task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertTrue(task_status['state'], constants.CALL_FINISHED_STATE)
        self.assertTrue(task_status['finish_time'], now)
        self.assertTrue(task_status['result'], result)

    def test_set_succeeded_with_timestamp(self):
        task_id = self.get_random_uuid()
        TaskStatus(task_id).save()

        result = 'done'
        now = '2014-11-21 05:21:38.829678'

        TaskStatus.objects(task_id=task_id).update_one(set__finish_time=now,
                                                       set__state=constants.CALL_FINISHED_STATE,
                                                       set__result=result)
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

        TaskStatus.objects(task_id=task_id).update_one(set__finish_time=finished,
                                                       set__state=constants.CALL_ERROR_STATE,
                                                       set__traceback=traceback)
        task_status = TaskStatus.objects.get(task_id=task_id)
        self.assertTrue(task_status['state'], constants.CALL_ERROR_STATE)
        self.assertTrue(task_status['finish_time'], finished)
        self.assertTrue(task_status['traceback'], traceback)

    def test_set_failed_with_timestamp(self):
        task_id = self.get_random_uuid()
        TaskStatus(task_id).save()

        traceback = 'abcdef'
        finished = '2014-11-21 05:21:38.829678'

        TaskStatus.objects(task_id=task_id).update_one(set__finish_time=finished,
                                                       set__state=constants.CALL_ERROR_STATE,
                                                       set__traceback=traceback)
        task_status = TaskStatus.objects.get(task_id=task_id)
        self.assertTrue(task_status['state'], constants.CALL_ERROR_STATE)
        self.assertTrue(task_status['finish_time'], finished)
        self.assertTrue(task_status['traceback'], traceback)
