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

import pymongo
from pymongo.son_manipulator import NamespaceInjector, AutoReference

from pulp.tasking.task import (
    task_waiting, task_running, task_complete_states)

class Storage(object):
    """
    Base task queue storage class
    """
    def waiting_task(self, task):
        """
        Add a task to the queue's waiting tasks
        @type task: pulp.tasks.task.Task
        @param task: Task instance
        """
        raise NotImplementedError()
        
    def running_task(self, task):
        """
        Remove a task from the queue's waiting tasks and add it to its running tasks
        @type task: pulp.tasks.task.Task
        @param task: Task instance
        """
        raise NotImplementedError()
        
    def complete_task(self, task):
        """
        Remove a task from the queue's running tasks and add it to it complete tasks
        @type task: pulp.tasks.task.Task
        @param task: Task instance
        """
        raise NotImplementedError()
    
    def remove_task(self, task):
        """
        Remove a task from the queue completely
        @type task: pulp.tasks.task.Task
        @param task: Task instance
        """
        raise NotImplementedError()
    
    def all_tasks(self):
        """
        Get and iterator of all tasks in the queue
        @return: iterator of Task instances
        """
        raise NotImplementedError()
        
    def waiting_tasks(self):
        """
        Get and iterator of waiting tasks in the queue
        @return: iterator of Task instances
        """
        raise NotImplementedError()
    
    def running_tasks(self):
        """
        Get and iterator of running tasks in the queue
        @return: iterator of Task instances
        """
        raise NotImplementedError()
        
    def complete_tasks(self):
        """
        Get and iterator of completed tasks in the queue
        @return: iterator of Task instances
        """
        raise NotImplementedError()
            
# memory-resident task storage ------------------------------------------------

class VolatileStorage(Storage):
    """
    Task storage that stores tasks in memory.
    """
    def __init__(self):
        self.__waiting_tasks = []
        self.__running_tasks = []
        self.__complete_tasks = []
        
    def waiting_task(self, task):
        self.__waiting_tasks.append(task)
        
    def running_task(self, task):
        self.__waiting_tasks.remove(task)
        self.__running_tasks.append(task)
        
    def complete_task(self, task):
        self.__running_tasks.remove(task)
        self.__complete_tasks.append(task)
        
    def remove_task(self, task):
        if task in self.__waiting_tasks:
            self.__waiting_tasks.remove(task)
        if task in self.__running_tasks:
            self.__running_tasks.remove(task)
        if task in self.__complete_tasks:
            self.__complete_tasks.remove(task)
            
    def all_tasks(self):
        return itertools.chain(self.__waiting_tasks[:],
                               self.__running_tasks[:],
                               self.__complete_tasks[:])
        
    def waiting_tasks(self):
        return self.__waiting_tasks[:]
    
    def running_tasks(self):
        return self.__running_tasks[:]
        
    def complete_tasks(self):
        return self.__complete_tasks[:]
    
# mongo database task storage -------------------------------------------------

class MongoStorage(Storage):
    """
    Task storage that stores tasks in a mongo database.
    """
    def __init__(self):
        self._connection = pymongo.Connection()
        
        self._db = self._connection._database
        self._db.add_son_manipulator(NamespaceInjector())
        self._db.add_son_manipulator(AutoReference(self._db))
        
        self._objdb = self._db.fifo_tasks
        self._objdb.ensure_index([('id', pymongo.DESCENDING)], unique=True, background=True)
        self._objdb.ensure_index([('next_time', pymongo.ASCENDING)], background=True)
        
        
    def waiting_task(self, task):
        self._objdb.save(task, manipulate=True, safe=True)
    
    def running_task(self, task):
        self._objdb.save(task, manipulate=True, safe=True)
    
    def complete_task(self, task):
        self._objdb.save(task, manipulate=True, safe=True)
    
    def remove_task(self, task):
        self._objdb.remove({'id': task.id}, safe=True)
    
    def all_tasks(self):
        return self._objdb.find_all()
    
    def waiting_tasks(self):
        return self._objdb.find({'status': task_waiting})
    
    def running_tasks(self):
        return self._objdb.find({'status': task_running})
    
    def complete_tasks(self):
        tasks = []
        for status in task_complete_states:
            tasks.extend(self._objdb.find({'status': status}))
        return tasks
