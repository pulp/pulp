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

# storage class for in-memory task queues -------------------------------------
   
class VolatileStorage(object):
    """
    In memory queue storage class.
    """
    def __init__(self):
        self.__waiting_tasks = []
        self.__running_tasks = []
        self.__complete_tasks = []
    
    # iterable methods
            
    def all_tasks(self):
        """
        Return an iterator over all tasks currently in the queue in descending
        order by length of time in the queue.
        @return: iterator
        """
        return itertools.chain(self.__complete_tasks[:],
                               self.__running_tasks[:],
                               self.__waiting_tasks[:])

    def unfinished_tasks(self):
        """
        Return an iterator over all unfinished tasks in the queue in descending
        order by length of time in the queue.
        @return: iterator
        """
        return itertools.chain(self.__running_tasks[:], self.__waiting_tasks[:])

    def waiting_tasks(self):
        """
        Return an iterator over all waiting tasks in the queue, in descending
        order by the length of time in the queue.
        @return: iterator
        """
        return self.__waiting_tasks[:]
    
    def running_tasks(self):
        """
        Return an iterator over all running tasks in the queue, in descending
        order by the length of time in the queue.
        @return: iterator
        """
        return self.__running_tasks[:]
        
    def complete_tasks(self):
        """
        Return an iterator over all complete tasks in the queue, in descending
        order by the length of time in the queue.
        @return: iterator
        """
        return self.__complete_tasks[:]
    
    # add/remove tasks methods
                
    def add_waiting_task(self, task):
        """
        Add a task to the wait queue.
        @type task: Task instance
        @param task: task to add
        """
        self.__waiting_tasks.append(task)
        
    def add_running_task(self, task):
        """
        Remove a task from the wait queue and add it to the running queue.
        @type task: Task instance
        @param task: task to add
        """
        self.__waiting_tasks.remove(task)
        self.__running_tasks.append(task)
        
    def add_complete_task(self, task):
        """
        Remove a task from the running queue and add it to the complete queue.
        @type task: Task instance
        @param task: task to add
        """
        self.__running_tasks.remove(task)
        self.__complete_tasks.append(task)
    
    def remove_task(self, task):
        """
        Remove a task from storage.
        @type task: Task instance
        @param task: task to remove
        """
        if task in self.__waiting_tasks:
            self.__waiting_tasks.remove(task)
            return
        if task in self.__running_tasks:
            self.__running_tasks.remove(task)
            return
        if task in self.__complete_tasks:
            self.__complete_tasks.remove(task)
            
    # query methods
    
    def find_task(self, criteria):
        """
        Find a task in the storage based on the given criteria.
        @type criteria: dict
        @param criteria: dict of task attr -> value to match against
        @type include_finished: bool
        @return: the last (newest) task in the queue that matches on success,
                 None otherwise
        """
        num_criteria = len(criteria)
        # In order to get the newest task and punch out early in the search algorithm,
        # reverse the tasks before starting the search (reversed returns a list, so
        # this call isn't destructive).
        for task in reversed(self.all_tasks()):
            matches = 0
            for attr, value in criteria.items():
                if not hasattr(task, attr):
                    break;
                if getattr(task, attr) != value:
                    break;
                matches += 1
            if matches == num_criteria:
                return task
        return None