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

import threading
import time
from datetime import datetime, timedelta

from pulp.tasking.queue.base import TaskQueue
from pulp.tasking.queue.thread import  TaskThread
from pulp.tasking.queue.storage import VolatileStorage
from pulp.tasking.task import task_complete_states

# fifo task queue -------------------------------------------------------------

class FIFOTaskQueue(TaskQueue):
    """
    Task queue with threaded dispatcher that fires off tasks in the order in
    which they were enqueued and stores the finished tasks for a specified
    amount of time.
    """
    def __init__(self,
                 max_running=4,
                 timeout=None,
                 finished_lifetime=timedelta(seconds=3600)):
        """
        @type max_running: int
        @param max_running: maximum number of tasks to run simultaneously
        @type timeout: datetime.timedelta instance or None
        @param timeout: maximum length of time to allow tasks to run,
                        None means indefinitely
        @type finished_lifetime: datetime.timedelta instance
        @param finished_lifetime: length of time to keep finished tasks
        @return: FIFOTaskQueue instance
        """
        self.max_running = max_running
        self.timeout = timeout
        self.finished_lifetime = finished_lifetime
        
        self.__lock = threading.RLock()
        self.__condition = threading.Condition(self.__lock)
        
        self.__running_count = 0
        self.__storage = VolatileStorage()
        self.__threads = {}
        
        self.__dispatcher_timeout = 0.5
        self.__dispatcher = threading.Thread(target=self._dispatch)
        self.__dispatcher.daemon = True
        self.__dispatcher.start()

    # protected methods: scheduling
        
    def _dispatch(self):
        """
        Scheduling method that that executes the scheduling hooks.
        """
        self.__lock.acquire()
        while True:
            self.__condition.wait(self.__dispatcher_timeout)
            for task in self._get_tasks():
                self.run(task)
            self._timeout_tasks()
            self._cull_tasks()
                
    def _get_tasks(self):
        """
        Get the next 'n' tasks to run, where is max - currently running tasks
        """
        num_tasks = self.max_running - self.__running_count
        return self.__storage.waiting_tasks()[:num_tasks]
    
    def _timeout_tasks(self):
        """
        """
        if self.timeout is None:
            return
        running_tasks = self.__storage.running_tasks()
        if not running_tasks:
            return
        now = datetime.now()
        for task in running_tasks:
            if now - task.start_time < self.timeout:
                continue
            thread = self.__threads[task]
            # this will cause a deadlock because we are holding the lock and the
            # task needs to call self.complete which tries to grab the lock and
            # thread.timeout waits for the task! (actually we don't wait for the
            # task, so there may not be a problem)
            thread.timeout()
            while task.state not in task_complete_states:
                time.sleep(0.0005)
            task.timeout()
                
    def _cull_tasks(self):
        """
        Clean up finished task data
        """
        complete_tasks = self.__storage.complete_tasks()
        if not complete_tasks:
            return
        now = datetime.now()
        for task in complete_tasks:
            if now - task.finish_time > self.finished_lifetime:
                self.__storage.remove_task(task)
    
    # public methods: queue operations
    
    def enqueue(self, task):
        self.__lock.acquire()
        try:
            task.queue = self
            task.next_time = datetime.now()
            task.wait()
            self.__storage.add_waiting_task(task)
        finally:
            self.__lock.release()
    
    def run(self, task):
        self.__lock.acquire()
        try:
            self.__running_count += 1
            self.__storage.add_running_task(task)
            thread = TaskThread(target=task.run)
            self.__threads[task] = thread
            thread.start()
        finally:
            self.__lock.release()
        
    def complete(self, task):
        self.__lock.acquire()
        try:
            self.__running_count -= 1
            self.__storage.add_complete_task(task)
            self.__threads.pop(task)
        finally:
            self.__lock.release()
            
    def cancel(self, task):
        self.__lock.acquire()
        try:
            thread = self.__threads[task]
            thread.cancel()
            while task.state not in task_complete_states:
                time.sleep(0.0005)
            task.cancel()
        finally:
            self.__lock.release()
    
    def find(self, **kwargs):
        self.__lock.acquire()
        try:
            return self.__storage.find_task(kwargs)
        finally:
            self.__lock.release()