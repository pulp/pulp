# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
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
This module contains tests for the pulp.server.webservices.dispatch module.
"""
import uuid
import mock

from .... import base
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server.db.model.resources import AvailableQueue

class TestTaskResource(base.PulpWebserviceTests):
    """
    Test the TaskResource class.
    """
    @mock.patch('pulp.server.async.tasks.controller.revoke', autospec=True)
    def test_DELETE_celery_task(self, revoke):
        """
        Test the DELETE() method with a UUID that does not correspond to a UUID that the
        coordinator is aware of. This should cause a revoke call to Celery's Controller.
        """
        task_id = '1234abcd'
        url = '/v2/tasks/%s/'
        test_queue = AvailableQueue('test_queue')
        TaskStatusManager.create_task_status(task_id, test_queue.name)

        self.delete(url % task_id)

        revoke.assert_called_once_with(task_id, terminate=True)


class TestTaskCollection(base.PulpWebserviceTests):
    """
    Test the TaskCollection class.
    """
    def setUp(self):
        base.PulpWebserviceTests.setUp(self)
        TaskStatus.get_collection().remove()

    def tearDown(self):
        base.PulpWebserviceTests.tearDown(self)
        TaskStatus.get_collection().remove()

    def test_GET_celery_tasks(self):
        """
        Test the GET() method to get all current tasks.
        """
        # Populate a couple of task statuses
        task_id1 = str(uuid.uuid4())
        queue_1 = 'queue_1'
        state1 = 'waiting'

        task_id2 = str(uuid.uuid4())
        queue_2 = 'queue_2'
        state2 = 'running'
        tags = ['random','tags']

        TaskStatusManager.create_task_status(task_id1, queue_1, tags, state1)
        TaskStatusManager.create_task_status(task_id2, queue_2, tags, state2)
        status, body = self.get('/v2/tasks/')

        # Validate
        self.assertEqual(200, status)
        self.assertTrue(len(body)== 2)
        for task in body:
            if task['task_id'] == task_id1:
                self.assertEquals(task['state'], state1)
                self.assertEqual(task['queue'], queue_1)
            else:
                self.assertEquals(task['state'], state2)
                self.assertEqual(task['queue'], queue_2)
        self.assertEquals(task['tags'], tags)

    def test_GET_celery_task_by_id(self):
        """
        Test the GET() method to get a current task with given id.
        """
        # Populate a couple of task statuses
        task_id1 = str(uuid.uuid4())
        queue_1 = 'queue_1'
        state1 = 'waiting'

        task_id2 = str(uuid.uuid4())
        queue_2 = 'queue_2'
        state2 = 'running'
        tags = ['random','tags']

        TaskStatusManager.create_task_status(task_id1, queue_1, tags, state1)
        TaskStatusManager.create_task_status(task_id2, queue_2, tags, state2)
        status, body = self.get('/v2/tasks/%s/' % task_id2)

        # Validate
        self.assertEqual(200, status)
        self.assertIsInstance(body, dict)
        self.assertEquals(body['state'], state2)
        self.assertEqual(body['queue'], queue_2)
        self.assertEquals(body['tags'], tags)

    def test_GET_celery_task_by_missing_id(self):
        """
        Test the GET() method to get a current task with given id.
        """
        # Populate a couple of task statuses
        task_id1 = str(uuid.uuid4())
        queue_1 = 'queue_1'
        state1 = 'waiting'
        tags = ['random', 'tags']

        TaskStatusManager.create_task_status(task_id1, queue_1, tags, state1)
        status, body = self.get('/v2/tasks/%s/' % str(uuid.uuid4()))

        # Validate
        self.assertEqual(404, status)
        self.assertIsInstance(body, dict)
        self.assertTrue('Task Not Found' in body['error_message'])
        self.assertTrue(task_id1 in body['error_message'])
