import thread
import time
import unittest
from pprint import pprint

from pulp.tasks.threads import Condition
from pulp.tasks.task import Task, FINISHED
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

#    def test_t_allocation(self):
#        t = Task(print_thread_id)

    def test_t(self):
        t = Task(thread_id)
        print 'task id: %s' % str(t.id)
        t.reset(args=[t.id])
        t.run()
        time.sleep(0.0005)
        self.assertTrue(t.status == FINISHED)

    def test_multi_runs(self):
        t = Task(thread_id)
        print 'task id: %s' % str(t.id)
        t.reset(args=[t.id])
        t.run()
        time.sleep(0.0005)
        self.assertTrue(t.status == FINISHED)
        t.run()
        time.sleep(0.0005)
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
        print 'task id: %s' % str(t.id)
        q.enqueue(t)
        time.sleep(0.005)
        self.assertTrue(t.status == FINISHED)
        del q
        del t


class ConditionTester(unittest.TestCase):

    def setUp(self):
        self.condition = Condition()

    def tearDown(self):
        pass

    def __condition_callback(self):
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()

    def test_condition(self):
        self.condition.acquire()
        t = Task(self.__condition_callback)
        q = FIFOTaskQueue()
        q.enqueue(t)
        self.condition.wait()
        self.assertTrue(t.status == FINISHED)


if __name__ == '__main__':
    #unittest.main()
    cases = [TaskTester, FIFOQueueTester, ConditionTester]
    for c in cases:
        suite = unittest.TestLoader().loadTestsFromTestCase(c)
        unittest.TextTestRunner(verbosity=1).run(suite)
