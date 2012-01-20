# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import sys
import threading
import time
import traceback

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + '/../common/')

import mock
import testutil

from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallReport, CallRequest
from pulp.server.dispatch.task import Task
from pulp.server.dispatch.taskqueue import TaskQueue

# call request test data -------------------------------------------------------

class NamedMock(mock.Mock):
    __name__ = 'NamedMock'

# instantiation testing --------------------------------------------------------

class TaskQueueInstantiationTests(testutil.PulpTest):

    def test_instantiation(self):
        try:
            TaskQueue(1)
        except:
            self.fail(traceback.format_exc())

    def test_singleton(self):
        # task queues with same concurrency threshold
        queue_1 = TaskQueue(1)
        queue_2 = TaskQueue(1)
        # task queue with different concurrency threshold
        queue_3 = TaskQueue(2)
        # test singleton
        self.assertTrue(queue_1 is queue_2)
        self.assertFalse(queue_1 is queue_3)

# queue start/stop testing -----------------------------------------------------

class TaskQueueStartStopTests(testutil.PulpTest):

    def setUp(self):
        self.queue = TaskQueue(1)

    def tearDown(self):
        try:
            self.queue.stop()
        except AssertionError:
            pass
        self.queue = None

    def test_start(self):
        self.assertTrue(self.queue._TaskQueue__dispatcher is None)
        self.queue.start()
        self.assertTrue(isinstance(self.queue._TaskQueue__dispatcher, threading.Thread))

    def test_stop(self):
        self.queue.start()
        self.assertTrue(isinstance(self.queue._TaskQueue__dispatcher, threading.Thread))
        self.queue.stop()
        self.assertTrue(self.queue._TaskQueue__dispatcher is None)

# task queue base tests class --------------------------------------------------

class TaskQueueTests(testutil.PulpTest):

    def setUp(self):
        super(TaskQueueTests, self).setUp()
        self.queue = TaskQueue(2)
        self.queue.start()

    def tearDown(self):
        super(TaskQueueTests, self).tearDown()
        self.queue.stop()
        self.queue = None

    def wait_for_task_to_start(self, task, interval=0.1, timeout=1.0):
        elapsed = 0.0
        while task.call_report.state is not dispatch_constants.CALL_RUNNING_STATE:
            time.sleep(interval)
            elapsed += interval
            if elapsed < timeout:
                continue
            self.fail('Task [%s] failed to start after %.2f seconds' % (task.id, timeout))

    def wait_for_task_to_complete(self, task, interval=0.1, timeout=1.0):
        elapsed = 0.0
        while task.call_report.state not in dispatch_constants.CALL_COMPLETE_STATES:
            time.sleep(interval)
            elapsed += interval
            if elapsed < timeout:
                continue
            self.fail('Task [%s] failed to complete after %.2f seconds' % (task.id, timeout))

# task execution testing -------------------------------------------------------

class TaskExecutionTests(TaskQueueTests):

    def test_task_enqueue(self):
        pass

    def test_task_dequeue(self):
        pass

    def test_task_queue_complete(self):
        pass

    def test_queued_call(self):
        pass

    def test_task_run(self):
        request = CallRequest(NamedMock())
        report = CallReport()
        task = Task(request, report, asynchronous=True)
        self.queue.enqueue(task)
        self.wait_for_task_to_start(task)
        self.assertTrue(self.queue.get(task.id) is task)
        task.succeeded()
        self.wait_for_task_to_complete(task)
        self.assertTrue(self.queue.get(task.id) is None)

    def test_blocking_task_run(self):
        task_1 = Task(CallRequest(NamedMock()), asynchronous=True)
        task_2 = Task(CallRequest(NamedMock()), asynchronous=True)
        task_2.blocking_tasks.add(task_1.id)
        self.queue.enqueue(task_1)
        self.queue.enqueue(task_2)
        self.wait_for_task_to_start(task_1)
        # task_2 cannot start because it is blocked by task_1
        self.assertTrue(task_2.call_report.state is dispatch_constants.CALL_WAITING_STATE)
        task_1.succeeded()
        self.wait_for_task_to_complete(task_1)
        # task_2 can start because task_1 has completed and unblocked it
        self.wait_for_task_to_start(task_2)
        task_2.succeeded()
        self.wait_for_task_to_complete(task_2)

    def test_exceed_concurrency(self):
        # this test relies on a concurrency threshold of 2
        task_1 = Task(CallRequest(NamedMock()), asynchronous=True)
        task_2 = Task(CallRequest(NamedMock()), asynchronous=True)
        task_3 = Task(CallRequest(NamedMock()), asynchronous=True)
        self.queue.enqueue(task_1)
        self.queue.enqueue(task_2)
        self.queue.enqueue(task_3)
        self.wait_for_task_to_start(task_1)
        self.wait_for_task_to_start(task_2)
        # task_3 cannot start because the concurrency threshold is 2
        self.assertTrue(task_3.call_report.state is dispatch_constants.CALL_WAITING_STATE)
        task_1.succeeded()
        task_2.succeeded()
        self.wait_for_task_to_complete(task_1)
        self.wait_for_task_to_complete(task_2)
        # task_3 can start because task_1 and task_2 have completed
        self.wait_for_task_to_start(task_3)
        self.assertTrue(task_3.call_report.state is dispatch_constants.CALL_RUNNING_STATE)
        task_3.succeeded()
        self.wait_for_task_to_complete(task_3)

    def test_archived_call(self):
        pass

    def test_task_cancel(self):
        pass

    def test_task_get(self):
        pass

    def test_task_find(self):
        pass

    def test_task_waiting_running_all(self):
        pass
