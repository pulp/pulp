import pprint
import time
import unittest

from pulp.tasking.task import (
    Task, task_created, task_finished, task_error, task_complete_states)
from pulp.tasking.queue.fifo import volatile_fifo_queue, mongo_fifo_queue


def noop_test():
    pass

def args_test(*args):
    assert args
    
def kwargs_test(**kwargs):
    assert kwargs

def result_test():
    return True

def error_test():
    raise Exception('Aaaargh!')


class TaskTester(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass
    
    def test_task_create(self):
        task = Task(noop_test)
        self.assertTrue(task.status == task_created)

    def test_task_noop(self):
        task = Task(noop_test)
        task.run()
        self.assertTrue(task.status == task_finished)

    def test_task_args(self):
        task = Task(args_test, 1, 2, 'foo')
        task.run()
        self.assertTrue(task.status == task_finished)

    def test_task_kwargs(self):
        task = Task(kwargs_test, arg1=1, arg2=2, argfoo='foo')
        task.run()
        self.assertTrue(task.status == task_finished)

    def test_task_result(self):
        task = Task(result_test)
        task.run()
        self.assertTrue(task.status == task_finished)
        self.assertTrue(task.result is True)

    def test_task_error(self):
        task = Task(error_test)
        task.run()
        self.assertTrue(task.status == task_error)
        self.assertTrue(task.traceback is not None)


class VolatileFIFOQueueTester(unittest.TestCase):

    def setUp(self):
        self.queue = volatile_fifo_queue()

    def tearDown(self):
        pass
    
    def __wait_for_task(self, task):
        while task.status not in task_complete_states:
            time.sleep(0.005)

    def test_task_dispatch(self):
        task = Task(noop_test)
        self.queue.enqueue(task)
        self.__wait_for_task(task)
        if task.status == task_error:
            pprint.pprint(task.traceback)
        self.assertTrue(task.status == task_finished)
        
# run the unittests -----------------------------------------------------------

if __name__ == '__main__':
    unittest.main()