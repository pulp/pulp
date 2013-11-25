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

import base
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.db.model.dispatch import TaskStatus

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
        state1 = 'waiting'

        task_id2 = str(uuid.uuid4())
        state2 = 'running'
        tags = ['random','tags']

        TaskStatusManager.create_task_status(task_id1, tags, state1)
        TaskStatusManager.create_task_status(task_id2, tags, state2)
        status, body = self.get('/v2/tasks/')

        # Validate
        self.assertEqual(200, status)
        self.assertTrue(len(body)== 2)
        for task in body:
            if task['task_id'] == task_id1:
                self.assertEquals(task['state'], state1)
            else:
                self.assertEquals(task['state'], state2)
        self.assertEquals(task['tags'], tags)


