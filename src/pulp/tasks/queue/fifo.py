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

from pulp.tasks.task import Task
from pulp.tasks.queue.base import TaskQueue


class FIFOTaskQueue(TaskQueue):
    """
    Task queue with threaded dispatcher that fires off tasks in the order in
    which they were enqueued and stores the finished tasks for a specified
    amount of time.
    """
    def __init__(self,
                 max_dispatcher_sleep=1,
                 max_running=4,
                 finished_lifetime=timedelta(seconds=3600)):
        """
        @param max_dispatch_sleep: maximum amount of time, in seconds, before
                                   the dispatcher wakes and performs its duties
        @param max_running: the maximum number of tasks to have running
                            simultaneously
        @param finished_lifetime: timedelta object representing the length of
                                  time to keep information on finished tasks
        @return: FIFOTaskQueue instance
        """
        super(FIFOTaskQueue, self).__init__(max_dispatcher_sleep)
        
        self._running_count = 0
        self.max_running = max_running
        self.finished_lifetime = finished_lifetime
        
    def __del__(self):
        # try to head-off a race condition on shutdown
        self._finished_tasks.clear()
        
    def _clean_finished_tasks(self):
        """
        Protected method to clean up finished task data
        @return: None
        """
        # try to head-off a race condition on shutdown
        if not self._finished_tasks:
            return
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
        try:
            self._finished_tasks[task.id] = self._running_tasks.pop(task.id)
            self._running_count -= 1
            self._condition.notify()
        finally:
            self._lock.release()
        
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
        try:
            task.set_queue(self)
            self._wait_queue.append(task)
            self._condition.notify()
        finally:
            self._lock.release()