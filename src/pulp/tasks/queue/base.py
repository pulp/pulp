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

import itertools
import threading

# base task queue -------------------------------------------------------------

class TaskQueue(object):
    """
    Abstract base class for task queues for interface definition and typing.
    """
    def enqueue(self, task):
        """
        Add a task to the task queue
        """
        raise NotImplementedError()
    
    def run(self, task):
        """
        Run a task from this task queue
        """
        raise NotImplementedError()
    
    def complete(self, task):
        """
        Mark a task run as completed
        """
        raise NotImplementedError()
    
    def find(self, task_id):
        """
        Find a task in this task queue
        """
        raise NotImplementedError()
    
    def clear(self):
        """
        Clear this task queue of all tasks
        """
        raise NotImplementedError()
    
# dummy task queue ------------------------------------------------------------
    
class DummyTaskQueue(TaskQueue):
    """
    Derived task queue in which all operations are no-ops.
    """
    def enqueue(self, task):
        pass
    
    def run(self, task):
        pass
    
    def complete(self, task):
        pass
    
    def find(self, task_id):
        return None
    
    def clear(self):
        pass
    
# base scheduling task queue --------------------------------------------------
    
class SchedulingTaskQueue(TaskQueue):
    """
    Base task queue that dispatches threads to run tasks based on a scheduler.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        
        self._waiting_tasks = []
        self._running_tasks = []
        self._complete_tasks = []
        
        self._dispatcher = threading.Thread(target=self._dispatch)
        self._dispatcher.daemon = True
        self._dispatcher.start()
        
    def _dispatch(self):
        """
        Scheduling method that must be overridden in a derived class
        """
        raise NotImplementedError()
    
    def enqueue(self, task):
        self._lock.acquire()
        try:
            task.queue = self
            task.waiting()
            self._waiting_tasks.append(task)
        finally:
            self._lock.release()
    
    def run(self, task):
        self._lock.acquire()
        try:
            self._waiting_tasks.remove(task)
            self._running_tasks.append(task)
            thread = threading.Thread(target=task.run)
            thread.start()
        finally:
            self._lock.release()
    
    def complete(self, task):
        self._lock.acquire()
        try:
            self._running_tasks.remove(task)
            self._complete_tasks.append(task)
        finally:
            self._lock.release()
    
    def find(self, task_id):
        self._lock.aqcuire()
        try:
            for task in itertools.chain(self._waiting_tasks,
                                        self._running_tasks,
                                        self._complete_tasks):
                if task.id == task_id:
                    return task
            return None
        finally:
            self._lock.release()
    
    def clear(self):
        self._lock.acquire()
        try:
            del self._waiting_tasks[:]
            del self._running_tasks[:]
            del self._complete_tasks[:]
        finally:
            self._lock.release()
            
# base persistent task queue --------------------------------------------------

class PersistentTaskQueue(TaskQueue):
    """
    Task queue that stores tasks in a database.
    """
    def __init__(self, db):
        self._db = db
        self._id = None
        
    def enqueue(self, task):
        pass
    
    def run(self, task):
        pass
    
    def complete(self, task):
        pass
    
    def find(self, task_id):
        pass
    
    def clear(self):
        pass
    