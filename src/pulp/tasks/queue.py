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

__author__ = 'Jason L Connor <jconnor@redhat.com>'

import threading
from datetime import datetime, timedelta
from pulp.tasks.task import Task


class DispatcherTaskQueue(object):
    """
    Task queue with threaded dispatcher that fires off enqueued tasks and stores
    the finished tasks for a specified amount of time.
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
        """
        self.max_running = max_running
        self.max_dispatch_sleep = max_dispatcher_sleep
        self.finished_lifetime = finished_lifetime
        
        self.__dispatcher = threading.Thread(target=self.__dispatch)
        self.__lock = threading.Lock()
        self.__condition = threading.Condition(self.__lock)
        self.__running_count = 0
        
        self.__wait_queue = []
        self.__running_tasks = {}
        self.__finished_tasks = {}
        
        self.__dispatcher.start()
        self.__dispatcher.run()
        
    def __clean_finished_tasks(self):
        """
        Private method to clean up finished task data
        """
        now = datetime.now()
        for id, task in self.__finished_tasks.items():
            if now - task.finish_time > self.finished_lifetime:
                self.__finished_tasks.pop(id)
        
    def __dispatch(self):
        """
        Private dispatch method executed by dispatch thread
        * clean up finished tasks
        * dequeue and dispatch up max_running tasks
        """
        self.lock.acquire()
        while True:
            self.condition.wait(self.max_dispatch_sleep)
            self.__clean_finished_tasks()
            while self.__running_count < self.max_running and self.__wait_queue:
                task = self.__wait_queue.pop(0)
                task.run()
                self.__running_tasks[task.id] = task
                self.__running_count += 1
                
    def enqueue(self, task):
        """
        Add a pulp.tasks.task.Task instance to the task queue
        @param task: Task instance
        """
        assert isinstance(task, Task)
        self.__lock.acquire()
        task._set_queue(self)
        self.__wait_queue.append(task)
        self.__condition.notify()
        self.__lock.release()
    
    def _finished(self, task):
        """
        Semi-private method, called by tasks on finishing
        @param task: Task instance
        """
        self.__lock.acquire()
        self.__finished_tasks[task.id] = self.__running_tasks.pop(task.id)
        self.__running_count -= 1
        self.__condition.notify()
        self.__lock.release()
     
    def find(self, task_id):
        """
        Find a task in the task queue, given its task id
        @param task_id: Task instance id
        """
        task = None
        self.__lock.acquire()
        if task_id in self.__finished_tasks:
            task = self.__finished_tasks[task_id]
        elif task_id in self.__running_tasks:
            task = self.__running_tasks[task_id]
        else:
            for t in self.__wait_queue:
                if t.id == task_id:
                    task = t
                    break
        self.__lock.release()
        return task