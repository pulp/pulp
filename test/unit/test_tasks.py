#!/usr/bin/python
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

import copy_reg
import itertools
import os
import pprint
import sys
import time
import types
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.common import dateutils
from pulp.server.api.repo_sync_task import RepoSyncTask
from pulp.server.db.model.persistence import TaskSnapshot
from pulp.server.tasking.exception import NonUniqueTaskException
from pulp.server.tasking.scheduler import (
    Scheduler, ImmediateScheduler, AtScheduler, IntervalScheduler)
from pulp.server.tasking.task import (
    Task, task_enqueue, task_dequeue, task_exit, task_waiting, task_running,
    task_finished, task_error, task_timed_out, task_canceled,
    task_complete_states)
from pulp.server.tasking.taskqueue.queue import TaskQueue
from pulp.server.tasking.taskqueue.storage import (
    VolatileStorage, _pickle_method, _unpickle_method)

# task test functions ---------------------------------------------------------

def noop():
    pass

def args(*args):
    assert len(args) > 0

def kwargs(**kwargs):
    assert len(kwargs) > 0

def result():
    return True

def error():
    raise Exception('Aaaargh!')

def interrupt_me():
    while True:
        time.sleep(0.5)

def wait(seconds=5):
    time.sleep(seconds)

class Class(object):
    def method(self):
        pass

class Hook(object):
    def __init__(self):
        self.called = False
        self.task = None
    def __call__(self, task):
        self.called = True
        self.task = task

# unittest classes ------------------------------------------------------------

class TaskTester(testutil.PulpAsyncTest):

    def test_task_create(self):
        task = Task(noop)
        self.assertTrue(task.state == task_waiting)
        snapshot = task.snapshot()
        restored_task = Task.from_snapshot(snapshot)
        self.assertTrue(restored_task.state == task_waiting)

    def test_task_noop(self):
        task = Task(noop)
        task.run()
        snapshot = task.snapshot()
        restored_task = Task.from_snapshot(snapshot)
        self.assertTrue(task.state == task_finished)
        self.assertTrue(restored_task.state == task_finished)

    def test_task_args(self):
        task = Task(args, args=[1, 2, 'foo'])
        task.run()
        snapshot = task.snapshot()
        restored_task = Task.from_snapshot(snapshot)
        self.assertTrue(restored_task.state == task_finished)
        self.assertTrue(task.state == task_finished)

    def test_task_kwargs(self):
        task = Task(kwargs, kwargs={'arg1':1, 'arg2':2, 'argfoo':'foo'})
        task.run()
        snapshot = task.snapshot()
        restored_task = Task.from_snapshot(snapshot)
        self.assertTrue(restored_task.state == task_finished)
        self.assertTrue(task.state == task_finished)

    def test_task_result(self):
        task = Task(result)
        task.run()
        self.assertTrue(task.state == task_finished)
        self.assertTrue(task.result is True)

    def test_task_error(self):
        task = Task(error)
        task.run()
        snapshot = task.snapshot()
        restored_task = Task.from_snapshot(snapshot)
        self.assertTrue(task.state == task_error)
        self.assertTrue(task.traceback is not None)
        self.assertTrue(restored_task.state == task_error)
        self.assertTrue(restored_task.traceback is not None)

    def __test_sync_task(self):
        repo = self.repo_api.create('some-id', 'some name', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64/')
        self.assertTrue(repo is not None)

        task = self.repo_api.sync(repo['id'])
        snapshot = task.snapshot()
        restored_task = Task.from_snapshot(snapshot)
        print "restored sync task: %s" % restored_task.__dict__
        self.assertTrue(restored_task.state == 'waiting')
        task.cancel()
        restored_task.cancel()

    def test_add_remove_hook(self):
        task = Task(noop)
        hook = Hook()
        try:
            task.add_enqueue_hook(hook)
            task.add_dequeue_hook(hook)
            task.remove_enqueue_hook(hook)
            task.remove_dequeue_hook(hook)
        except:
            self.fail()


class QueueTester(testutil.PulpAsyncTest):

    def _wait_for_task(self, task, timeout=timedelta(seconds=20)):
        start = datetime.now()
        while task.state not in task_complete_states:
            time.sleep(0.1)
            if datetime.now() - start >= timeout:
                raise RuntimeError('Task wait timed out after %d seconds, with state: %s' %
                                       (timeout.seconds, task.state))
        if task.state == task_error:
            pprint.pprint(task.traceback)


class TaskQueueTester(QueueTester):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.queue = TaskQueue()

    def tearDown(self):
        testutil.PulpAsyncTest.tearDown(self)
        self.queue._cancel_dispatcher()
        del self.queue

    def test_task_enqueue(self):
        task = Task(noop)
        self.queue.enqueue(task)
        self.assertTrue(task.state == task_waiting)

    def test_enqueue_duplicate_allowed(self):
        # Setup
        task1 = Task(noop)
        self.queue.enqueue(task1)

        self.assertEqual(1, len(list(self.queue._TaskQueue__storage.all_tasks())))

        # Test
        task2 = Task(noop)
        self.queue.enqueue(task2, unique=False)

        # Verify
        self.assertEqual(2, len(list(self.queue._TaskQueue__storage.all_tasks())))

    def test_enqueue_duplicate_no_args(self):
        # Setup
        task1 = Task(noop)
        self.queue.enqueue(task1)

        self.assertEqual(1, len(list(self.queue._TaskQueue__storage.all_tasks())))

        # Test
        task2 = Task(noop)
        try:
            self.queue.enqueue(task2, unique=True)
        except NonUniqueTaskException:
            pass

        # Verify
        self.assertEqual(1, len(list(self.queue._TaskQueue__storage.all_tasks())))

    def test_enqueue_duplicate_with_same_kw_args(self):
        # Setup
        task1 = Task(kwargs, kwargs={'foo':1, 'bar':2})
        self.queue.enqueue(task1)

        self.assertEqual(1, len(list(self.queue._TaskQueue__storage.all_tasks())))

        # Test
        task2 = Task(kwargs, kwargs={'foo':1, 'bar':2})
        try:
            self.queue.enqueue(task2, unique=True)
        except NonUniqueTaskException:
            pass

        # Verify
        self.assertEqual(1, len(list(self.queue._TaskQueue__storage.all_tasks())))

    def test_enqueue_duplicate_with_different_kw_args(self):
        # Setup
        task1 = Task(kwargs, kwargs={'foo':1, 'bar':2})
        self.queue.enqueue(task1)

        self.assertEqual(1, len(list(self.queue._TaskQueue__storage.all_tasks())))

        # Test
        task2 = Task(kwargs, kwargs={'foo':2, 'bar':3})
        try:
            self.queue.enqueue(task2, unique=True)
        except NonUniqueTaskException:
            pass

        # Verify
        self.assertEqual(1, len(list(self.queue._TaskQueue__storage.all_tasks())))

    def test_enqueue_duplicate_with_same_args(self):
        # Setup
        task1 = Task(args, args=[1, 2])
        self.queue.enqueue(task1)

        self.assertEqual(1, len(list(self.queue._TaskQueue__storage.all_tasks())))

        # Test
        task2 = Task(args, args=[1, 2])
        try:
            self.queue.enqueue(task2, unique=True)
        except NonUniqueTaskException:
            pass

        # Verify
        self.assertEqual(1, len(list(self.queue._TaskQueue__storage.all_tasks())))

    def test_enqueue_duplicate_with_different_args(self):
        # Setup
        task1 = Task(args, args=[1, 2])
        self.queue.enqueue(task1)

        self.assertEqual(1, len(list(self.queue._TaskQueue__storage.all_tasks())))

        # Test
        task2 = Task(args, args=[2, 3])
        self.queue.enqueue(task2, unique=True)

        # Verify
        self.assertEqual(2, len(list(self.queue._TaskQueue__storage.all_tasks())))

    def test_enqueue_duplicate_with_immediate_scheduler(self):
        task1 = Task(noop)
        task2 = Task(noop)
        self.queue.enqueue(task1, True)
        self.assertRaises(NonUniqueTaskException, self.queue.enqueue, task2, True)

    def test_enqueue_duplicate_with_same_scheduler(self):
        at = AtScheduler(datetime.now(dateutils.local_tz()) + timedelta(minutes=10))
        task1 = Task(noop, scheduler=at)
        task2 = Task(noop, scheduler=at)
        self.queue.enqueue(task1, True)
        self.assertRaises(NonUniqueTaskException, self.queue.enqueue, task2, True)

    def test_enqueue_duplicate_with_different_schedulers(self):
        at = AtScheduler(datetime.now(dateutils.local_tz()) + timedelta(minutes=10))
        task1 = Task(noop, scheduler=at)
        task2 = Task(noop, scheduler=ImmediateScheduler())
        self.queue.enqueue(task1, True)
        enqueued_2 = self.queue.enqueue(task2, True)
        self.assertTrue(enqueued_2 is None)

    def test_task_dispatch(self):
        task = Task(noop)
        self.queue.enqueue(task)
        self._wait_for_task(task)
        self.assertTrue(task.state == task_finished)

    def test_task_dispatch_with_scheduled_time(self):
        delay_seconds = timedelta(seconds=10)
        schduler = AtScheduler(datetime.now(dateutils.local_tz()) + delay_seconds)
        task = Task(noop, scheduler=schduler)
        self.queue.enqueue(task)
        start_time = datetime.now()
        self._wait_for_task(task, timeout=timedelta(seconds=20))
        end_time = datetime.now()
        self.assertTrue(task.state == task_finished)
        self.assertTrue(end_time - start_time > delay_seconds)

    def test_task_find(self):
        task1 = Task(noop)
        self.queue.enqueue(task1)
        task2 = self.queue.find(id=task1.id)[0]
        self.assertTrue(task1 is task2)

    def test_find_invalid_criteria(self):
        # Setup
        task1 = Task(noop)
        self.queue.enqueue(task1)

        # Test
        found = self.queue.find(foo=task1.id)

        # Verify
        self.assertTrue(not found)

    def test_find_empty_queue(self):
        # Test
        found = self.queue.find(id=1)

        # Verify
        self.assertTrue(not found)

    def test_find_multiple_criteria(self):
        # Setup
        task1 = Task(noop)
        self.queue.enqueue(task1)

        # Test
        found = self.queue.find(id=task1.id, state=task_waiting)

        # Verify
        self.assertTrue(found[0] is task1)

    def test_find_multiple_matching(self):
        # Setup
        task1 = Task(noop)
        task2 = Task(noop)

        self.queue.enqueue(task1)
        self.queue.enqueue(task2)

        # Test
        found = self.queue.find(state=task_waiting)

        # Verify
        self.assertTrue(task2 in found)

    def test_find_job(self):
        # Setup
        ntasks = 3
        job_id = 99
        for i in range(0,ntasks):
            t = Task(noop)
            t.job_id = job_id
            self.queue.enqueue(t)
        # Test & Verify
        found = self.queue.find(job_id=job_id)
        self.assertEqual(len(found), ntasks)

    def test_task_status(self):
        task = Task(noop)
        self.queue.enqueue(task)
        self._wait_for_task(task)
        status = self.queue.find(id=task.id)
        self.assertTrue(status[0].state == task.state)

    def test_exists_matching_criteria(self):
        # Setup
        task1 = Task(noop)
        self.queue.enqueue(task1)

        # Test
        task2 = Task(noop)
        task2.id = task1.id

        result = self.queue.exists(task2, ['id'])

        # Verify
        self.assertTrue(result)

    def test_exists_unmatching_criteria(self):
        # Setup
        task1 = Task(noop)
        self.queue.enqueue(task1)

        # Test
        task2 = Task(noop)

        result = self.queue.exists(task2, ['id'])

        # Verify
        self.assertTrue(not result)

    def test_exists_multiple_criteria(self):
        # Setup
        task1 = Task(args, args=[1, 2])
        task2 = Task(args, args=[2, 3])

        self.queue.enqueue(task1)
        self.queue.enqueue(task2)

        # Test
        find_me = Task(args, args=[2, 3])

        found = self.queue.exists(find_me, ['method_name', 'args'])

        # Verify
        self.assertTrue(found)

    def test_exists_invalid_criteria(self):
        # Setup
        look_for = Task(noop)

        # Test & Verify
        self.assertRaises(ValueError, self.queue.exists, look_for, ['foo'])

    def test_weighted_tasks(self):
        task_1 = Task(wait, [3], weight=2)
        task_2 = Task(wait, [3], weight=3)
        self.queue.enqueue(task_1)
        self.queue.enqueue(task_2)
        time.sleep(1.0)
        self.assertTrue(task_1.state is task_running, task_1.state)
        self.assertTrue(task_2.state is task_waiting, task_2.state)
        self._wait_for_task(task_1)
        time.sleep(1.0)
        self.assertTrue(task_2.state is task_running, task_2.state)
        self._wait_for_task(task_2)

    def test_equeue_hook(self):
        task = Task(wait, [2])
        hook = Hook()
        task.add_enqueue_hook(hook)
        self.queue.enqueue(task)
        self.assertTrue(hook.called)
        self.assertTrue(hook.task is task)
        self._wait_for_task(task)

    def test_dequeue_hook(self):
        task = Task(wait, [2])
        hook = Hook()
        task.add_dequeue_hook(hook)
        self.queue.enqueue(task)
        self.assertFalse(hook.called)
        while hook.task is None:
            time.sleep(1)
        self.assertTrue(hook.called)
        self.assertTrue(hook.task is task)

class InterruptQueueTester(QueueTester):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.queue = TaskQueue()

    def tearDown(self):
        testutil.PulpAsyncTest.tearDown(self)
        self.queue._cancel_dispatcher()
        del self.queue

    def disable_task_timeout(self):
    #def test_task_timeout(self):
        task = Task(interrupt_me, timeout=timedelta(seconds=2))
        self.queue.enqueue(task)
        self._wait_for_task(task)
        self.assertTrue(task.state == task_timed_out, 'state is %s' % task.state)

    def disable_task_cancel(self):
    #def test_task_cancel(self):
        task = Task(interrupt_me)
        self.queue.enqueue(task)
        self.queue.cancel(task)
        self._wait_for_task(task)
        self.assertTrue(task.state == task_canceled, 'state is %s' % task.state)

    def disable_multiple_task_cancel(self):
    #def test_multiple_task_cancel(self):
        task1 = Task(interrupt_me)
        task2 = Task(interrupt_me)
        self.queue.enqueue(task1)
        self.queue.enqueue(task2)
        self.queue.cancel(task1)
        self.queue.cancel(task2)
        self._wait_for_task(task2)
        self.assertTrue(task2.state == task_canceled, 'state is %s' % task.state)


class PriorityQueueTester(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.storage = VolatileStorage()

    def tearDown(self):
        testutil.PulpAsyncTest.tearDown(self)
        del self.storage

    def _enqueue_three_tasks(self):
        task1 = Task(noop)
        task1.scheduled_time = 3
        task2 = Task(noop)
        task2.scheduled_time = 2
        task3 = Task(noop)
        task3.scheduled_time = 1
        for t in (task1, task2, task3):
            self.storage.enqueue_waiting(t)

    def test_task_order(self):
        self._enqueue_three_tasks()
        ordered = []
        while self.storage.num_waiting() > 0:
            ordered.append(self.storage.dequeue_waiting())
        for i, t1 in enumerate(ordered[:-1]):
            t2 = ordered[i + 1]
            self.assertTrue(t1.scheduled_time <= t2.scheduled_time)

    def test_task_peek(self):
        self._enqueue_three_tasks()
        t = self.storage.dequeue_waiting()
        self.assertTrue(t.scheduled_time == 1)

    def test_task_removal(self):
        t = Task(noop)
        self.storage.enqueue_waiting(t)
        self.assertTrue(self.storage.num_waiting() == 1)
        self.storage.remove_waiting(t)
        self.assertTrue(self.storage.num_waiting() == 0)


class ScheduledTaskTester(QueueTester):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.queue = TaskQueue()

    def tearDown(self):
        testutil.PulpAsyncTest.tearDown(self)
        self.queue._cancel_dispatcher()
        del self.queue

    def test_immediate(self):
        task = Task(noop, scheduler=ImmediateScheduler())
        self.queue.enqueue(task)
        self._wait_for_task(task)
        self.assertTrue(task.state is task_finished, 'state is %s' % task.state)

    def test_at(self):
        now = datetime.now(dateutils.local_tz())
        then = timedelta(seconds=10)
        at = AtScheduler(now + then)
        task = Task(noop, scheduler=at)
        self.queue.enqueue(task)
        self.assertTrue(task.state is task_waiting, 'state is %s' % task.state)
        self._wait_for_task(task, timedelta(seconds=11))
        self.assertTrue(task.state is task_finished, 'state is %s' % task.state)

    def test_at_time(self):
        now = datetime.now(dateutils.local_tz())
        then = timedelta(seconds=10)
        at = AtScheduler(now + then)
        task = Task(noop, scheduler=at)
        self.queue.enqueue(task)
        time.sleep(8)
        self.assertTrue(task.state is task_waiting, 'state is %s' % task.state)
        time.sleep(3)
        self.assertTrue(task.state is task_finished, 'state is %s' % task.state)

    def test_interval(self):
        now = datetime.now(dateutils.local_tz())
        then = timedelta(seconds=10)
        interval = IntervalScheduler(then, now + then, 1)
        task = Task(noop, scheduler=interval)
        self.queue.enqueue(task)
        self.assertTrue(task.state is task_waiting, 'state is %s' % task.state)
        self._wait_for_task(task, timedelta(seconds=11))
        self.assertTrue(task.state is task_finished, 'state is %s' % task.state)

    def test_interval_schedule(self):
        now = datetime.now(dateutils.local_tz())
        then = timedelta(seconds=10)
        interval = IntervalScheduler(then, now + then, 1)
        task = Task(noop, scheduler=interval)
        self.queue.enqueue(task)
        self._wait_for_task(task, timedelta(seconds=11))
        self.assertTrue(task.scheduled_time is None, 'scheduled_time is %s' % task.scheduled_time)

    def test_interval_no_start_time(self):
        then = timedelta(seconds=10)
        interval = IntervalScheduler(then, None, 1)
        task = Task(noop, scheduler=interval)
        self.queue.enqueue(task)
        now = datetime.now(dateutils.local_tz())
        self.assertTrue(task.scheduled_time <= now + then)
        self._wait_for_task(task)

    def test_multi_run_interval(self):
        now = datetime.now(dateutils.local_tz())
        then = timedelta(seconds=5)
        interval = IntervalScheduler(then, now + then, 2)
        task = Task(noop, scheduler=interval)
        self.queue.enqueue(task)
        time.sleep(3)
        self.assertTrue(task.state is task_waiting, 'state is %s' % task.state)
        time.sleep(4)
        self.assertTrue(task.state is task_waiting, 'state is %s' % task.state)
        time.sleep(4)
        self.assertTrue(task.state is task_finished, 'state is %s' % task.state)

    def test_interval_removal(self):
        then = timedelta(seconds=5)
        interval = IntervalScheduler(then, None, 1)
        task = Task(wait, scheduler=interval)
        self.queue.enqueue(task)
        time.sleep(1)
        self.assertTrue(isinstance(task.scheduler, IntervalScheduler))
        self.queue.remove(task)
        self.assertTrue(isinstance(task.scheduler, ImmediateScheduler))
        self._wait_for_task(task)


class PersistentTaskTester(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        copy_reg.pickle(types.MethodType, _pickle_method, _unpickle_method)
        TaskSnapshot.get_collection().remove()
        self.same_type_fields = ('scheduler',)

    def tearDown(self):
        testutil.PulpAsyncTest.tearDown(self)
        TaskSnapshot.get_collection().remove()

    def test_task_serialization(self):
        task = Task(noop)
        snapshot = task.snapshot()
        self.assertTrue(isinstance(snapshot, TaskSnapshot))

    def test_task_deserialization(self):
        task1 = Task(noop)
        snapshot = task1.snapshot()
        task2 = snapshot.to_task()
        self.assertTrue(isinstance(task2, Task))

    def test_task_with_immediate_scheduler_serialization(self):
        task = Task(noop, scheduler=ImmediateScheduler())
        snapshot = task.snapshot()
        self.assertTrue(isinstance(snapshot, TaskSnapshot))

    def test_task_with_immediate_scheduler_deserialization(self):
        task1 = Task(noop, scheduler=ImmediateScheduler())
        snapshot = task1.snapshot()
        task2 = snapshot.to_task()
        self.assertTrue(isinstance(task2.scheduler, ImmediateScheduler))

    def test_task_with_at_scheduler_serialization(self):
        now = datetime.now(dateutils.local_tz())
        then = timedelta(seconds=10)
        task = Task(noop, scheduler=AtScheduler(now + then))
        snapshot = task.snapshot()
        self.assertTrue(isinstance(snapshot, TaskSnapshot))

    def test_task_with_at_scheduler_serialization(self):
        now = datetime.now(dateutils.local_tz())
        then = timedelta(seconds=10)
        task1 = Task(noop, scheduler=AtScheduler(now + then))
        snapshot = task1.snapshot()
        task2 = snapshot.to_task()
        self.assertTrue(isinstance(task2.scheduler, ImmediateScheduler))

    def test_task_with_interval_scheduler_deserialization(self):
        now = datetime.now(dateutils.local_tz())
        then = timedelta(seconds=10)
        task = Task(noop, scheduler=IntervalScheduler(then, now + then, 1))
        snapshot = task.snapshot()
        self.assertTrue(isinstance(snapshot, TaskSnapshot))

    def test_task_with_interval_scheduler_deserialization(self):
        now = datetime.now(dateutils.local_tz())
        then = timedelta(seconds=10)
        task1 = Task(noop, scheduler=IntervalScheduler(then, now + then, 1))
        snapshot = task1.snapshot()
        task2 = snapshot.to_task()
        self.assertTrue(isinstance(task2.scheduler, ImmediateScheduler),
                        'deserialized interval task with %s scheduler' %
                        str(type(task2.scheduler)))

    def test_task_equality(self):
        task1 = Task(noop)
        snapshot = task1.snapshot()
        task2 = snapshot.to_task()
        # XXX fixme
        self.assertTrue(True)

    def test_method_serialization(self):
        obj = Class()
        task = Task(obj.method)
        snapshot = task.snapshot()
        self.assertTrue(isinstance(snapshot, TaskSnapshot))

    def test_method_deserialization(self):
        obj = Class()
        task = Task(obj.method)
        snapshot = task.snapshot()
        task2 = snapshot.to_task()
        self.assertTrue(isinstance(task2.callable, types.MethodType))

    def test_sync_task_serialization(self):
        task = RepoSyncTask(Class().method)
        snapshot = task.snapshot()
        self.assertTrue(isinstance(snapshot, TaskSnapshot))

    def test_sync_task_deserialization(self):
        task1 = RepoSyncTask(Class().method)
        snapshot = task1.snapshot()
        task2 = snapshot.to_task()
        self.assertTrue(isinstance(task2, RepoSyncTask))

    def test_db_storage(self):
        task = Task(noop)
        snapshot = task.snapshot()
        collection = TaskSnapshot.get_collection()
        collection.insert(snapshot, safe=True)
        count = collection.find().count()
        self.assertTrue(count == 1, 'count is %d' % count)

    def test_db_retrieval(self):
        task1 = RepoSyncTask(Class().method)
        snapshot1 = task1.snapshot()
        collection = TaskSnapshot.get_collection()
        collection.insert(snapshot1, safe=True)
        snapshot2 = TaskSnapshot(collection.find_one({'_id': snapshot1['_id']}))
        task2 = snapshot2.to_task()
        self.assertTrue(isinstance(task2, RepoSyncTask))

    def test_snapshot_with_hooks(self):
        task_1 = Task(noop)
        hook_1 = Hook()
        task_1.add_enqueue_hook(hook_1)
        snapshot_1 = task_1.snapshot()
        collection = TaskSnapshot.get_collection()
        collection.insert(snapshot_1, safe=True)
        snapshot_2 = TaskSnapshot(collection.find_one({'_id': snapshot_1['_id']}))
        task_2 = snapshot_2.to_task()
        hook_2 = task_2.hooks[task_enqueue][0]
        self.assertTrue(isinstance(hook_2, Hook))

# run the unit tests ----------------------------------------------------------

if __name__ == '__main__':
    unittest.main()
