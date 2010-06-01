import thread
import time
import unittest
from pprint import pprint

from pulp.tasks.task import Task, FINISHED
from pulp.tasks.queue.fifo import FIFOTaskQueue


THREAD_ID = None
def thread_id():
    global THREAD_ID
    THREAD_ID = thread.get_ident()

def print_thread_id():
    print 'thread id: %s' % str(thread.get_ident())


class TaskTester(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_task(self):
        t = Task(thread_id)
        print 'task id: %s' % str(t.id)
        t.run()
        t.wait()
        self.assertTrue(t.thread_id == THREAD_ID)

    def test_multi_runs(self):
        t = Task(thread_id)
        print 'task id: %s' % str(t.id)
        t.run()
        t.wait()
        self.assertTrue(t.status == FINISHED)
        t.run()
        t.wait()
        self.assertTrue(t.status == FINISHED)


class FIFOQueueTester(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_queue_allocation(self):
        q = FIFOTaskQueue()

    def test_task_dispatch(self):
        q = FIFOTaskQueue()
        t = Task(print_thread_id)
        q.enqueue(t)
        t.wait()
        self.assertTrue(t.status == FINISHED)


if __name__ == '__main__':
    unittest.main()