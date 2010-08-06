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
from datetime import datetime, timedelta

from pulp.tasking.queue.base import TaskQueue, VolatileStorage

# fifo task queue -------------------------------------------------------------

class FIFOTaskQueue(TaskQueue):
    """
    Task queue with threaded dispatcher that fires off tasks in the order in
    which they were enqueued and stores the finished tasks for a specified
    amount of time.
    """
    def __init__(self,
                 max_running=4,
                 finished_lifetime=timedelta(seconds=3600)):
        """
        @param max_running: the maximum number of tasks to have running
                            simultaneously
        @param finished_lifetime: timedelta object representing the length of
                                  time to keep information on finished tasks
        @return: FIFOTaskQueue instance
        """
        self.__lock = threading.RLock()
        self.__condition = threading.Condition(self.__lock)
        
        self.__storage = VolatileStorage()
        
        self.__dispatcher_timeout = 0.5
        self.__dispatcher = threading.Thread(target=self._dispatch)
        self.__dispatcher.daemon = True
        
        self.__running_count = 0
        self.max_running = max_running
        self.finished_lifetime = finished_lifetime

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
            self._cull_tasks()
                
    def _get_tasks(self):
        # Get the next 'n' tasks to run, where is max - currently running tasks
        num_tasks = self.max_running - self.__running_count
        return self.__storage.waiting_tasks()[:num_tasks]
                
    def _cull_tasks(self):
        # Clean up finished task data
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
            thread = threading.Thread(target=task.run)
            thread.start()
        finally:
            self.__lock.release()
        
    def complete(self, task):
        
        self.__lock.acquire()
        try:
            self.__running_count -= 1
            self.__storage.add_complete_task(task)
        finally:
            self.__lock.release()
    
    def find(self, **kwargs):
        self.__lock.acquire()
        try:
            return self.__storage.find_task(kwargs)
        finally:
            self.__lock.release()