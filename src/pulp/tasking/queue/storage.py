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

import itertools

import pymongo
from pymongo.son_manipulator import NamespaceInjector, AutoReference

from pulp.tasking.task import task2model, TaskModel, task_complete_states


class Storage(object):
    """
    Base task queue storage class
    """
    def waiting_task(self, task):
        """
        Add a task to the queue's waiting tasks
        @type task: pulp.tasking.task.Task
        @param task: Task instance
        """
        raise NotImplementedError()
        
    def running_task(self, task):
        """
        Remove a task from the queue's waiting tasks and add it to its running tasks
        @type task: pulp.tasking.task.Task
        @param task: Task instance
        """
        raise NotImplementedError()
        
    def complete_task(self, task):
        """
        Remove a task from the queue's running tasks and add it to it complete tasks
        @type task: pulp.tasking.task.Task
        @param task: Task instance
        """
        raise NotImplementedError()
    
    def find_task(self, task_id):
        """
        @type task_id: str
        @param task_id: Task id
        @return: pulp.tasking.task.Task instance
        """
        raise NotImplementedError()
    
    def task_status(self, task_id):
        """
        @type task_id: str
        @param task_id: Task id
        @return: pulp.tasking.task.TaskModel instance
        """
        raise NotImplementedError()
    
    def remove_task(self, task):
        """
        Remove a task from the queue completely
        @type task: pulp.tasking.task.Task
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
    
    def find_task(self, task_id):
        for task in self.all_tasks():
            if task.id == task_id:
                return task
        return None
    
    def task_status(self, task_id):
        task = self.find_task(task_id)
        if task is None:
            return None
        return task2model(task)
        
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
    
# hybrid mongo and volatile task storage --------------------------------------
    
class MongoFinishedStorage(VolatileStorage):
    """
    Task storage that store tasks in memory and finished tasks in a mongo db.
    """
    def __init__(self):
        super(MongoFinishedStorage, self).__init__()
        
        self._connection = pymongo.Connection()
        
        self._db = self._connection._database
        self._db.add_son_manipulator(NamespaceInjector())
        self._db.add_son_manipulator(AutoReference(self._db))
        
        self._objdb = self._db.tasks
        
    def _task_db2model(self, task_son):
        """
        Protected method to marshal mongodb son objects into the task model.
        @type task_son: pymongo.son.SON instance
        @param task_son: mongodb son representation of a task
        @return: pulp.tasking.task.TaskModel instance
        """
        model = TaskModel()
        model.update(task_son)
        return model
    
    def complete_task(self, task):
        model = task2model(task)
        self._objdb.save(model, manipulate=True, safe=True)
        super(MongoFinishedStorage, self).complete_task(task)
        
    def task_status(self, task_id):
        task_son = self._objdb.find_one({'_id': task_id})
        if task_son is not None:
            return self._task_db2model(task_son)
        return super(MongoFinishedStorage, self).task_status(task_id)
    
    def remove_task(self, task):
        if task.state in task_complete_states:
            self._objdb.remove({'_id': task.id}, safe=True)
        super(MongoFinishedStorage, self).remove_task(task)
    
# mongo database task storage -------------------------------------------------

class MongoStorage(MongoFinishedStorage):
    """
    Task storage that stores task status in a mongo database.
    """
    def __init__(self):
        super(MongoStorage, self).__init__()
        
    def waiting_task(self, task):
        model = task2model(task)
        self._objdb.save(model, manipulate=True, safe=True)
        super(MongoStorage, self).waiting_task(task)
    
    def running_task(self, task):
        model = task2model(task)
        self._objdb.save(model, manipulate=True, safe=True)
        super(MongoStorage, self).running_task(task)
        
    def task_status(self, task_id):
        task_son = self._objdb.find_one({'_id': task_id})
        if task_son is None:
            return None
        return self._task_db2model(task_son)
    
    def remove_task(self, task):
        self._objdb.remove({'_id': task.id}, safe=True)
        super(MongoFinishedStorage, self).remove_task(task)
