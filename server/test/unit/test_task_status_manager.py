# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 Red Hat, Inc.
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
import uuid 

import base

from pulp.common import dateutils
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.db.model.dispatch import TaskStatus
import pulp.server.exceptions as exceptions

 
class TaskStatusManagerTests(base.PulpServerTests):
 
    def setUp(self):
        super(TaskStatusManagerTests, self).setUp()
 
    def tearDown(self):
        super(TaskStatusManagerTests, self).tearDown()
 
    def clean(self):
        super(TaskStatusManagerTests, self).clean()
        TaskStatus.get_collection().remove()
 
    def get_random_uuid(self):
        return str(uuid.uuid4())
 
    def test_create(self):
        """
        Tests creating a TaskStatus with valid data is successful.
        """
        # Setup
        task_id = self.get_random_uuid()
        tags = ['test-tag1', 'test-tag2']
        state = 'waiting'
        # Test
        created = TaskStatusManager.create_task_status(task_id, tags, state)
        # Verify
        task_statuses = list(TaskStatus.get_collection().find())
        self.assertEqual(1, len(task_statuses))
 
        task_status = task_statuses[0]
        self.assertEqual(task_id, task_status['task_id'])
        self.assertEqual(tags, task_status['tags'])
        self.assertEqual(state, task_status['state'])
 
        self.assertEqual(task_id, created['task_id'])
        self.assertEqual(tags, created['tags'])
        self.assertEqual(state, created['state'])
 
    def test_create_defaults(self):
        """
        Tests creating a task status with minimal information.
        """
        # Test
        task_id = self.get_random_uuid()
        TaskStatusManager.create_task_status(task_id)
        # Verify
        task_statuses = list(TaskStatus.get_collection().find())
        self.assertEqual(1, len(task_statuses))
        self.assertEqual(task_id, task_statuses[0]['task_id'])
 
    def test_create_invalid_task_id(self):
        """
        Tests creating a task status with an invalid task id raises the correct error.
        """
        try:
            TaskStatusManager.create_task_status(None)
            self.fail('Invalid ID did not raise an exception')
        except exceptions.InvalidValue, e:
            self.assertTrue(e.property_names[0], 'task_id')
  
    def test_create_duplicate_task_id(self):
        """
        Tests creating a task status with a duplicate task id.
        """
        task_id = self.get_random_uuid()
        TaskStatusManager.create_task_status(task_id)
        try:
            TaskStatusManager.create_task_status(task_id)
            self.fail('Task status with a duplicate task id did not raise an exception')
        except exceptions.DuplicateResource, e:
            self.assertTrue(task_id in e)

    def test_create_invalid_attributes(self):
        """
        Tests that creating a task status with invalid attributes
        results in an error
        """
        task_id = self.get_random_uuid()
        tags = 'not a list'
        state = 1
        try:
            TaskStatusManager.create_task_status(task_id, tags, state)
            self.fail('Invalid attributes did not cause create to raise an exception')
        except exceptions.InvalidValue, e:
            self.assertTrue('tags' in e.data_dict()['property_names'])
            self.assertTrue('state' in e.data_dict()['property_names'])
  
    def test_delete_task_status(self):
        """
        Tests deleting a task status under normal circumstances.
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
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue(task_id == e.resources['resource_id'])

    def test_update_task_status(self):
        """
        Tests the case of successfully updating a task status.
        """
        task_id = self.get_random_uuid()
        tags = ['test-tag1', 'test-tag2']
        state = 'waiting'
        TaskStatusManager.create_task_status(task_id, tags, state)
        delta = {'start_time': dateutils.now_utc_timestamp(),
                 'state': 'running',
                 'disregard': 'ignored'}

        updated = TaskStatusManager.update_task_status(task_id, delta)

        task_status =  TaskStatusManager.find_by_task_id(task_id)
        self.assertEqual(task_status['start_time'], delta['start_time'])
        self.assertEqual(task_status['state'], delta['state'])
        self.assertEqual(updated['start_time'], delta['start_time'])
        self.assertEqual(updated['state'], delta['state'])
  
    def test_update_missing_task_status(self):
        """
        Tests updating a task status that doesn't exist raises the appropriate exception.
        """
        task_id = self.get_random_uuid()
        try:
            TaskStatusManager.update_task_status(task_id, {})
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue(task_id == e.resources['resource_id'])

