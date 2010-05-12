import os
import pprint
import StringIO
import sys
import thread
import unittest

#module_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../src/'))
#sys.path.insert(0, module_path)

from pulp.tasks.task import Task
from pulp.tasks.queue.fifo import FIFOTaskQueue


SYS_OUT = None

def swap_sys_out():
    global SYS_OUT
    if SYS_OUT is None:
        SYS_OUT = sys.stdout
        sys.stdout = StringIO.StringIO()
    else:
        sys.stdout = SYS_OUT
        SYS_OUT = None


def thread_id():
    print 'thread id: %s' % str(thread.get_ident())


class TaskTester(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_task(self):
        task = Task(thread_id)
        print 'task id: %s' % str(task.id)
        task.run()
#        pprint.pprint(task.__dict__)


if __name__ == '__main__':
    unittest.main()
