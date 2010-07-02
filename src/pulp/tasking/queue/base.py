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

# base task queue -------------------------------------------------------------

class TaskQueue(object):
    """
    Abstract base class for task queues for interface definition and typing.
    """
    def enqueue(self, task):
        """
        Add a task to the task queue
        @type task: pulp.tasking.task.Task
        @param task: Task instance
        """
        raise NotImplementedError()
    
    def run(self, task):
        """
        Run a task from this task queue
        @type task: pulp.tasking.task.Task
        @param task: Task instance
        """
        raise NotImplementedError()
    
    def complete(self, task):
        """
        Mark a task run as completed
        @type task: pulp.tasking.task.Task
        @param task: Task instance
        """
        raise NotImplementedError()
    
    def find(self, task_id):
        """
        Find a task in this task queue
        @type task_id: str
        @param task_id: task id
        @return: Task instance on success, None otherwise
        """
        raise NotImplementedError()
    
    def status(self, task_id):
        """
        Get the status of a task in this task queue
        @type task_id: str
        @param task_id: task id
        @return: TaskModel instance on success, None otherwise
        """
        raise NotImplementedError()
    
# no-frills task queue --------------------------------------------------------
    
class SimpleTaskQueue(TaskQueue):
    """
    Derived task queue that provides no special functionality
    """
    def enqueue(self, task):
        task.waiting()
    
    def run(self, task):
        task.run()
    
    def complete(self, task):
        pass
    
    def find(self, task_id):
        return None
    
    def status(self, task_id):
        return None
    
# base scheduling task queue --------------------------------------------------
    
class SchedulingTaskQueue(TaskQueue):
    """
    Base task queue that dispatches threads to run tasks based on a scheduler.
    """
    def __init__(self, storage, dispatcher_timeout=0.5):
        """
        @type dispatcher_timeout: float
        @param dispatcher_timeout: the max number of seconds before the
                                   dispatcher wakes up to run tasks
        """
        self._storage = storage
        
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        
        self._dispatcher_timeout = dispatcher_timeout
        self._dispatcher = threading.Thread(target=self._dispatch)
        self._dispatcher.daemon = True
        self._dispatcher.start()
        
    # protected methods: scheduling
        
    def _dispatch(self):
        """
        Scheduling method that that executes the scheduling hooks
        This should not be overridden by a derived class
        """
        self._lock.acquire()
        while True:
            self._condition.wait(self._dispatcher_timeout)
            self._initialize_runs()
            for task in self._get_tasks():
                self._pre_run(task)
                self.run(task)
                self._post_run(task)
            self._finalize_runs()
                
    def _initialize_runs(self):
        """
        Pre-task runs hook that may be overridden in a derived class
        """
        pass
    
    def _finalize_runs(self):
        """
        Post-task runs hook that may be overridden in a derived class
        """
        pass
    
    def _get_tasks(self):
        """
        Scheduling method that retrieve the tasks to be run on on a 
        @return: iterator of Task instances
        """
        raise NotImplementedError()
    
    def _pre_run(self, task):
        """
        Pre-individual task run hook that may be overridden in a derived class
        """
        pass
    
    def _post_run(self, task):
        """
        Post-individual task run hook that may be overridden in a derived class
        """
        pass
    
    # public methods: queue operations
    
    def enqueue(self, task):
        self._lock.acquire()
        try:
            task.queue = self
            task.waiting()
            self._storage.waiting_task(task)
        finally:
            self._lock.release()
    
    def run(self, task):
        self._lock.acquire()
        try:
            task.running()
            self._storage.running_task(task)
            thread = threading.Thread(target=task.run)
            thread.start()
        finally:
            self._lock.release()
    
    def complete(self, task):
        self._lock.acquire()
        try:
            self._storage.complete_task(task)
        finally:
            self._lock.release()
    
    def find(self, task_id):
        self._lock.acquire()
        try:
            return self._storage.find_task(task_id)
        finally:
            self._lock.release()
    
    def status(self, task_id):
        self._lock.acquire()
        try:
            return self._storage.task_status(task_id)
        finally:
            self._lock.release()