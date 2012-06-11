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

import mock
import os
import sys
import threading
import time
import traceback

import base

from pulp.server.db.model.dispatch import QueuedCall
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import pickling
from pulp.server.dispatch.call import CallRequest
from pulp.server.dispatch.task import AsyncTask, Task
from pulp.server.dispatch.taskqueue import TaskQueue

# call request test data -------------------------------------------------------

class NamedMock(mock.Mock):
    __name__ = 'NamedMock'

def call(*args, **kwargs):
    pass

# instantiation testing --------------------------------------------------------

class TaskQueueInstantiationTests(base.PulpServerTests):

    def test_instantiation(self):
        try:
            TaskQueue(1)
        except:
            self.fail(traceback.format_exc())

    def _test_singleton(self):
        # task queues with same concurrency threshold
        queue_1 = TaskQueue(1)
        queue_2 = TaskQueue(1)
        # task queue with different concurrency threshold
        queue_3 = TaskQueue(2)
        # test singleton
        self.assertTrue(queue_1 is queue_2)
        self.assertFalse(queue_1 is queue_3)

# queue start/stop testing -----------------------------------------------------

class TaskQueueStartStopTests(base.PulpServerTests):

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

class TaskQueueTests(base.PulpServerTests):

    def setUp(self):
        super(TaskQueueTests, self).setUp()
        pickling.initialize()
        self.queue = TaskQueue(2)
        # NOTE we are not starting the queue (i.e. firing up the dispatcher thread)

    def tearDown(self):
        super(TaskQueueTests, self).tearDown()
        QueuedCall.get_collection().drop()
        self.queue = None

    def gen_task(self, call=call):
        return Task(CallRequest(call))

    def gen_async_task(self, call=call):
        return AsyncTask(CallRequest(call))

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

# task queue control flow tests ------------------------------------------------

class TaskQueueControlFlowTests(TaskQueueTests):

    def test_task_enqueue(self):
        task = self.gen_task()
        try:
            self.queue.enqueue(task)
        except:
            self.fail(traceback.format_exc())
        self.assertTrue(task in self.queue.waiting_tasks())

    def test_task_enqueue_execution_hook(self):
        task = self.gen_task()
        hook = NamedMock()
        task.call_request.add_life_cycle_callback(dispatch_constants.CALL_ENQUEUE_LIFE_CYCLE_CALLBACK, hook)
        self.queue.enqueue(task)
        self.assertTrue(hook.call_count == 1)
        self.assertTrue(task.call_request in hook.call_args[0])
        self.assertTrue(task.call_report in hook.call_args[0])

    def test_queued_call_collection(self):
        task = self.gen_task(call=call)
        collection = QueuedCall.get_collection()
        try:
            self.queue.enqueue(task)
        except:
            self.fail(traceback.format_exc())
        queued_call = collection.find_one({'_id': task.queued_call_id})
        self.assertFalse(queued_call is None)
        self.assertFalse(queued_call['serialized_call_request'] is None)
        try:
            call_request = CallRequest.deserialize(queued_call['serialized_call_request'])
        except:
            self.fail(traceback.format_exc())
        self.assertFalse(call_request is None)

    def test_multi_enqueue(self):
        task_1 = self.gen_task()
        task_2 = self.gen_task()
        task_3 = self.gen_task()
        for t in (task_1, task_2, task_3):
            self.queue.enqueue(t)
        self.assertTrue(task_1 in self.queue.waiting_tasks())
        self.assertTrue(task_2 in self.queue.waiting_tasks())
        self.assertTrue(task_3 in self.queue.waiting_tasks())

    def test_validate_blocking_task(self):
        task_1 = self.gen_task()
        task_2 = self.gen_task()
        task_2.blocking_tasks.add(task_1.id)
        self.queue.enqueue(task_1)
        self.queue.enqueue(task_2)
        # blocking_tasks are actually replaced
        self.assertTrue(task_1.id in task_2.blocking_tasks)

    def test_invalid_blocking_task(self):
        task_1 = self.gen_task()
        task_2 = self.gen_task()
        task_2.blocking_tasks.add(task_1.id)
        self.queue.enqueue(task_2)
        # task_1 cannot block task_2 because it is not queued
        self.assertFalse(task_1.id in task_2.blocking_tasks)

    def test_get_ready_task(self):
        task = self.gen_task()
        self.queue.enqueue(task)
        task_list = self.queue._get_ready_tasks()
        self.assertTrue(task in task_list)

    def test_get_ready_tasks(self):
        task_1 = self.gen_task()
        task_2 = self.gen_task()
        task_3 = self.gen_task()
        for t in (task_1, task_2, task_3):
            self.queue.enqueue(t)
        task_list = self.queue._get_ready_tasks()
        self.assertTrue(task_1 in task_list)
        self.assertTrue(task_2 in task_list)
        self.assertFalse(task_3 in task_list)

    def test_get_ready_tasks_blocking(self):
        task_1 = self.gen_task()
        task_2 = self.gen_task()
        task_2.blocking_tasks.add(task_1.id)
        self.queue.enqueue(task_1)
        self.queue.enqueue(task_2)
        task_list = self.queue._get_ready_tasks()
        self.assertTrue(task_1 in task_list)
        self.assertFalse(task_2 in task_list)

    def test_run_ready_task(self):
        task = self.gen_async_task()
        self.queue.enqueue(task)
        self.queue._run_ready_task(task)
        self.wait_for_task_to_start(task)
        self.assertFalse(task in self.queue.waiting_tasks())
        self.assertTrue(task in self.queue.running_tasks())

    def test_run_ready_task_complete(self):
        task = self.gen_async_task()
        self.queue.enqueue(task)
        self.queue._run_ready_task(task)
        self.wait_for_task_to_start(task)
        task._succeeded()
        self.wait_for_task_to_complete(task)
        self.assertFalse(task in self.queue.waiting_tasks())
        self.assertFalse(task in self.queue.running_tasks())

    def test_run_ready_task_blocked(self):
        task_1 = self.gen_async_task()
        task_2 = self.gen_task()
        task_2.blocking_tasks.add(task_1.id)
        self.queue.enqueue(task_1)
        self.queue.enqueue(task_2)
        self.queue._run_ready_task(task_1)
        self.wait_for_task_to_start(task_1)
        task_list = self.queue._get_ready_tasks()
        self.assertFalse(task_1 in task_list)
        self.assertFalse(task_2 in task_list)
        task_1._succeeded()
        self.wait_for_task_to_complete(task_1)
        task_list = self.queue._get_ready_tasks()
        self.assertTrue(task_2 in task_list)

    def test_task_dequeue(self):
        task = self.gen_task()
        self.queue.enqueue(task)
        self.assertTrue(task in self.queue.waiting_tasks())
        self.queue.dequeue(task)
        self.assertFalse(task in self.queue.all_tasks())

    def test_task_dequeue_execution_hook(self):
        task = self.gen_task()
        hook = NamedMock()
        task.call_request.add_life_cycle_callback(dispatch_constants.CALL_DEQUEUE_LIFE_CYCLE_CALLBACK, hook)
        self.queue.enqueue(task)
        self.queue.dequeue(task)
        self.assertTrue(hook.call_count == 1)
        self.assertTrue(task.call_request in hook.call_args[0])
        self.assertTrue(task.call_report in hook.call_args[0])

    def task_dequeue_blocking(self):
        task_1 = self.gen_task()
        task_2 = self.gen_task()
        task_2.blocking_tasks.add(task_1.id)
        self.queue.enqueue(task_1)
        self.queue.enqueue(task_2)
        self.assertTrue(task_1.id in task_2.blocking_tasks)
        self.queue.dequeue(task_1)
        self.assertFalse(task_1.id in task_2.blocking_tasks)

# task queue query tests -------------------------------------------------------

class TaskQueueQueryTests(TaskQueueTests):

    def test_get(self):
        task_1 = self.gen_task()
        self.queue.enqueue(task_1)
        task_2 = self.queue.get(task_1.id)
        self.assertTrue(task_2 is task_1)

    def test_find_single_tag(self):
        tag = 'TAG'
        task = self.gen_task()
        task.call_request.tags.append(tag)
        self.queue.enqueue(task)
        task_list = self.queue.find(tag)
        self.assertTrue(len(task_list) == 1)
        self.assertTrue(task in task_list)

    def test_find_multi_tags(self):
        tags = ['FEE', 'FIE', 'FOE', 'FOO']
        task = self.gen_task()
        task.call_request.tags.extend(tags)
        self.queue.enqueue(task)
        task_list = self.queue.find(*tags[1:3]) # only passes in 'FIE', 'FOE'
        self.assertTrue(task in task_list)

    def test_find_multi_tasks(self):
        tags = ['one', 'two', 'three', 'four']
        task_1 = self.gen_task()
        task_1.call_request.tags.extend(tags[:2])
        task_2 = self.gen_task()
        task_2.call_request.tags.extend(tags[1:3])
        task_3 = self.gen_task()
        task_3.call_request.tags.extend(tags[2:])
        for t in (task_1, task_2, task_3):
            self.queue.enqueue(t)
        task_list = self.queue.find('two')
        self.assertTrue(task_1 in task_list)
        self.assertTrue(task_2 in task_list, str(task_2.call_request.tags))
        self.assertFalse(task_3 in task_list)

