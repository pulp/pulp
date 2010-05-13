#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

_author_ = 'Jason L Connor <jconnor@redhat.com>'

from datetime import datetime, timedelta

from pulp.tasks.threads import Lock, Condition, Thread
from pulp.tasks.task import Task
from pulp.tasks.queue.base import TaskQueue


class FIFOTaskQueue(TaskQueue):
    """
    Task queue with threaded dispatcher that fires off tasks in the order in
    which they were enqueued and stores the finished tasks for a specified
    amount of time.
    """
    def __init__(self,
                 max_running=4,
                 max_dispatcher_sleep=1,
                 finished_lifetime=timedelta(seconds=3600)):
        """
        @param max_running: the maximum number of tasks to have running
                            simultaneously
        @param max_dispatch_sleep: maximum amount of time, in seconds, before
                                   the dispatcher wakes and performs its duties
        @param finished_lifetime: timedelta object representing the length of
                                  time to keep information on finished tasks
        @return: FIFOTaskQueue instance
        """
        super(FIFOTaskQueue, self).__init__()
        
        self.max_running = max_running
        self.max_dispatch_sleep = max_dispatcher_sleep
        self.finished_lifetime = finished_lifetime
        
        self._dispatcher = Thread(target=self._dispatch)
        self._lock = Lock()
        self._condition = Condition(self._lock)
        self._running_count = 0
        
        self._wait_queue = []
        self._running_tasks = {}
        self._finished_tasks = {}
        
        self._dispatcher.execute()
        
    def __del__(self):
        self._dispatcher.exit()
        
    def _clean_finished_tasks(self):
        """
        Protected method to clean up finished task data
        @return: None
        """
        now = datetime.now()
        for id, task in self._finished_tasks.items():
            if now - task.finish_time > self.finished_lifetime:
                self._finished_tasks.pop(id)
        
    def _dispatch(self):
        """
        Protected dispatch method executed by dispatch thread
        * clean up finished tasks
        * dequeue and dispatch up max_running tasks
        @return: None
        """
        self._lock.acquire()
        while True:
            self._condition.wait(self.max_dispatch_sleep)
            self._clean_finished_tasks()
            while self._running_count < self.max_running and self._wait_queue:
                task = self._wait_queue.pop(0)
                self._running_tasks[task.id] = task
                self._running_count += 1
                task.run()
    
    def finished(self, task):
        """
        Called by tasks on finishing
        @param task: Task instance
        @return: None
        """
        self._lock.acquire()
        self._finished_tasks[task.id] = self._running_tasks.pop(task.id)
        self._running_count -= 1
        self._condition.notify()
        self._lock.release()
        
    def is_empty(self):
        """
        Check to see if there are any waiting or running tasks
        @return: True if there are no waiting or running tasks, False otherwise
        """
        return self._wait_queue or self._running_tasks
    
    def finished_tasks(self):
        """
        Get a list of all the finished tasks
        @return: list of Task instances
        """
        return self._finished_tasks.values()
                 
    def enqueue(self, task):
        """
        Add a pulp.tasks.task.Task instance to the task queue
        @param task: Task instance
        @return: None
        """
        assert isinstance(task, Task)
        self._lock.acquire()
        task.set_queue(self)
        self._wait_queue.append(task)
        self._condition.notify()
        self._lock.release()
    
    def find(self, task_id):
        """
        Find a task in the task queue, given its task id
        @param task_id: Task instance id
        @return: Task instance with corresponding id if found, None otherwise
        """
        task = None
        self._lock.acquire()
        if task_id in self._finished_tasks:
            task = self._finished_tasks[task_id]
        elif task_id in self._running_tasks:
            task = self._running_tasks[task_id]
        else:
            for t in self._wait_queue:
                if t.id == task_id:
                    task = t
                    break
        self._lock.release()
        return task