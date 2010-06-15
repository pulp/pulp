import pprint
import time
import unittest

from pulp.tasking.task import (
    Task, task_created, task_waiting, task_finished, task_error,
    task_complete_states)
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
        self.assertTrue(task.state == task_created)

    def test_task_noop(self):
        task = Task(noop_test)
        task.run()
        self.assertTrue(task.state == task_finished)

    def test_task_args(self):
        task = Task(args_test, 1, 2, 'foo')
        task.run()
        self.assertTrue(task.state == task_finished)

    def test_task_kwargs(self):
        task = Task(kwargs_test, arg1=1, arg2=2, argfoo='foo')
        task.run()
        self.assertTrue(task.state == task_finished)

    def test_task_result(self):
        task = Task(result_test)
        task.run()
        self.assertTrue(task.state == task_finished)
        self.assertTrue(task.result is True)

    def test_task_error(self):
        task = Task(error_test)
        task.run()
        self.assertTrue(task.state == task_error)
        self.assertTrue(task.traceback is not None)


class QueueTester(unittest.TestCase):
    
    def _wait_for_task(self, task):
        while task.state not in task_complete_states:
            time.sleep(0.005)
        if task.state == task_error:
            pprint.pprint(task.traceback)
            

class VolatileFIFOQueueTester(QueueTester):

    def setUp(self):
        self.queue = volatile_fifo_queue()

    def tearDown(self):
        pass
            
    def test_task_enqueue(self):
        task = Task(noop_test)
        self.queue.enqueue(task)
        self.assertTrue(task.state == task_waiting)

    def test_task_dispatch(self):
        task = Task(noop_test)
        self.queue.enqueue(task)
        self._wait_for_task(task)
        self.assertTrue(task.state == task_finished)
        
    def test_task_find(self):
        task1 = Task(noop_test)
        self.queue.enqueue(task1)
        task2 = self.queue.find(task1.id)
        self.assertTrue(task1 is task2)
        
    def test_task_status(self):
        task = Task(noop_test)
        self.queue.enqueue(task)
        self._wait_for_task(task)
        status = self.queue.status(task.id)
        self.assertTrue(status.state == task.state)
        
        
class MongoFIFOQueueTester(QueueTester):
    
    def setUp(self):
        self.queue = mongo_fifo_queue()
        
    def tearDown(self):
        pass
            
    def test_task_enqueue(self):
        task = Task(noop_test)
        self.queue.enqueue(task)
        self.assertTrue(task.state == task_waiting)

    def test_task_dispatch(self):
        task = Task(noop_test)
        self.queue.enqueue(task)
        self._wait_for_task(task)
        self.assertTrue(task.state == task_finished)
        
    def test_task_find(self):
        task1 = Task(noop_test)
        self.queue.enqueue(task1)
        task2 = self.queue.find(task1.id)
        self.assertTrue(task1 is task2)
        
    def test_task_status(self):
        task = Task(noop_test)
        self.queue.enqueue(task)
        self._wait_for_task(task)
        status = self.queue.status(task.id)
        self.assertTrue(status.state == task.state)
        
    def test_separate_queues(self):
        new_queue = mongo_fifo_queue()
        task = Task(noop_test)
        self.queue.enqueue(task)
        self._wait_for_task(task)
        status = new_queue.status(task.id)
        self.assertTrue(status.state == task.state)
        
            
# run the unit tests ----------------------------------------------------------

if __name__ == '__main__':
    unittest.main()