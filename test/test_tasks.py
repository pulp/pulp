import thread
import unittest

from pulp.tasks.task import Task
from pulp.tasks.queue.fifo import FIFOTaskQueue


def thread_id(id):
    assert thread.get_ident() == id

def print_thread_id():
    print 'thread id: %s' % str(thread.get_ident())


class TaskTester(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_task_allocation(self):
        task = Task(print_thread_id)

    def test_task(self):
        task = Task(thread_id)
        print 'task id: %s' % str(task.id)
        task.reset(args=[task.id])
        task.run()

    def test_multi_runs(self):
        task = Task(thread_id)
        print 'task id: %s' % str(task.id)
        task.reset(args=[task.id])
        task.run()
        task.run()


class FIFOQueueTester(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_queue_allocation(self):
        queue = FIFOTaskQueue()

    def test_task_dispatch(self):
        queue = FIFOTaskQueue()
        task = Task(print_thread_id)
        print 'task id: %s' % str(task.id)
        queue.enqueue(task)


if __name__ == '__main__':
    #unittest.main()
    #cases = [TaskTester, FIFOQueueTester]
    cases = [FIFOQueueTester]
    for c in cases:
        suite = unittest.TestLoader().loadTestsFromTestCase(c)
        unittest.TextTestRunner(verbosity=1).run(suite)
