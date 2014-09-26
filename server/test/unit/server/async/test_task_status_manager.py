# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
"""
This module contains tests for the pulp.server.async.task_status_manager module.
"""
import mock
import uuid

from datetime import datetime

from ... import base

from pulp.common import constants, dateutils
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.dispatch import TaskStatus
import pulp.server.exceptions as exceptions


class TaskStatusManagerTests(base.PulpServerTests):
    """
    Test the TaskStatusManager class.
    """
    def clean(self):
        super(TaskStatusManagerTests, self).clean()
        TaskStatus.get_collection().remove(safe=True)

    def get_random_uuid(self):
        return str(uuid.uuid4())

    def test_create_task_status(self):
        """
        Tests that create_task_status() with valid data is successful.
        """
        task_id = self.get_random_uuid()
        worker_name = 'a_worker_name'
        tags = ['test-tag1', 'test-tag2']
        state = 'waiting'

        created = TaskStatusManager.create_task_status(task_id, worker_name, tags, state)

        task_statuses = list(TaskStatus.get_collection().find())
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
        Tests create_task_status() with minimal information, to ensure that defaults are handled
        properly.
        """
        task_id = self.get_random_uuid()

        TaskStatusManager.create_task_status(task_id)

        task_statuses = list(TaskStatus.get_collection().find())
        self.assertEqual(1, len(task_statuses))
        self.assertEqual(task_id, task_statuses[0]['task_id'])
        self.assertEqual(None, task_statuses[0]['worker_name'])
        self.assertEqual([], task_statuses[0]['tags'])
        self.assertEqual('waiting', task_statuses[0]['state'])

    def test_create_task_status_invalid_task_id(self):
        """
        Test that calling create_task_status() with an invalid task id raises the correct error.
        """
        try:
            TaskStatusManager.create_task_status(None)
        except exceptions.InvalidValue, e:
            self.assertTrue(e.property_names[0], 'task_id')
        else:
            self.fail('Invalid ID did not raise an exception')

    def test_create_task_status_duplicate_task_id(self):
        """
        Tests create_task_status() with a duplicate task id.
        """
        task_id = self.get_random_uuid()

        TaskStatusManager.create_task_status(task_id)
        try:
            TaskStatusManager.create_task_status(task_id)
        except exceptions.DuplicateResource, e:
            self.assertTrue(task_id in e)
        else:
            self.fail('Task status with a duplicate task id did not raise an exception')

    def test_create_task_status_invalid_attributes(self):
        """
        Tests that calling create_task_status() with invalid attributes
        results in an error
        """
        task_id = self.get_random_uuid()
        worker_name = ['not a string']
        tags = 'not a list'
        state = 1
        try:
            TaskStatusManager.create_task_status(task_id, worker_name, tags, state)
        except exceptions.InvalidValue, e:
            self.assertTrue('tags' in e.data_dict()['property_names'])
            self.assertTrue('state' in e.data_dict()['property_names'])
            self.assertTrue('worker_name' in e.data_dict()['property_names'])
        else:
            self.fail('Invalid attributes did not cause create to raise an exception')

    def test_delete_task_status(self):
        """
        Test delete_task_status() under normal circumstances.
        """
        task_id = self.get_random_uuid()
        TaskStatusManager.create_task_status(task_id)

        TaskStatusManager.delete_task_status(task_id)

        task_statuses = list(TaskStatusManager.find_all())
        self.assertEqual(0, len(task_statuses))

    def test_delete_not_existing_task_status(self):
        """
        Tests that deleting a task status that doesn't exist raises the appropriate error.
        """
        task_id = self.get_random_uuid()
        try:
            TaskStatusManager.delete_task_status(task_id)
        except exceptions.MissingResource, e:
            self.assertTrue(task_id == e.resources['resource_id'])
        else:
            self.fail('Exception expected')

    def test_update_task_status(self):
        """
        Tests the successful operation of update_task_status().
        """
        task_id = self.get_random_uuid()
        worker_name = 'special_worker_name'
        tags = ['test-tag1', 'test-tag2']
        state = 'waiting'
        TaskStatusManager.create_task_status(task_id, worker_name, tags, state)
        now = datetime.now(dateutils.utc_tz())
        start_time = dateutils.format_iso8601_datetime(now)
        delta = {'start_time': start_time,
                 'state': 'running',
                 'disregard': 'ignored',
                 'progress_report': {'report-id': 'my-progress'}}

        updated = TaskStatusManager.update_task_status(task_id, delta)

        task_status = TaskStatusManager.find_by_task_id(task_id)
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


    @mock.patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    def test_set_accepted(self, mock_update):
        task_id = 'test'

        # test

        TaskStatusManager.set_task_accepted(task_id)

        # validation

        delta = {
            'state': constants.CALL_ACCEPTED_STATE
        }

        mock_update.assert_called_with(task_id=task_id, delta=delta)

    @mock.patch('pulp.common.dateutils.format_iso8601_datetime')
    @mock.patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    def test_set_started(self, mock_update, mock_date):
        task_id = 'test'
        now = '1234'
        mock_date.return_value = now

        # test

        TaskStatusManager.set_task_started(task_id)

        # validation

        delta = {
            'state': constants.CALL_RUNNING_STATE,
            'start_time': now
        }

        mock_update.assert_called_with(task_id=task_id, delta=delta)

    @mock.patch('pulp.common.dateutils.format_iso8601_datetime')
    @mock.patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    def test_set_succeeded(self, mock_update, mock_date):
        task_id = 'test'
        result = 'done'
        now = '1234'

        mock_date.return_value = now

        # test

        TaskStatusManager.set_task_succeeded(task_id, result)

        # validation

        delta = {
            'state': constants.CALL_FINISHED_STATE,
            'finish_time': now,
            'result': result
        }

        mock_update.assert_called_with(task_id=task_id, delta=delta)

    @mock.patch('pulp.common.dateutils.format_iso8601_datetime')
    @mock.patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    def test_set_failed(self, mock_update, mock_date):
        task_id = 'test'
        traceback = 'TB'
        now = '1234'

        mock_date.return_value = now

        # test

        TaskStatusManager.set_task_failed(task_id, traceback)

        # validation

        delta = {
            'state': constants.CALL_ERROR_STATE,
            'finish_time': now,
            'traceback': traceback
        }

        mock_update.assert_called_with(task_id=task_id, delta=delta)
