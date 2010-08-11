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

import pulp.tasking.task

# base task queue -------------------------------------------------------------

class TaskQueue(object):
    """
    Abstract base class for task queues for interface definition and typing.
    """
    def enqueue(self, task, unique=False):
        """
        Add a task to the task queue
        @type task: pulp.tasking.task.Task
        @param task: Task instance
        @type unique: bool
        @param unique: If True, the task will only be added if there are no
                       non-finished tasks with the same method_name, args,
                       and kwargs; otherwise the task will always be added
        @return: True if a new task was created; False if it was rejected (due to
                 the unique flag
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
    
    def cancel(self, task):
        """
        Cancel a running task.
        @type task: pulp.tasking.task.Task
        @param task: Task instance
        """
        raise NotImplementedError()
    
    def find(self, **kwargs):
        """
        Find a task in this task queue. Only the oldest task in the queue will be
        returned.
        @type kwargs: dict
        @param kwargs: task attributes and values as search criteria
        @type include_finished: bool
        @return: Task instance on success, None otherwise
        """
        raise NotImplementedError()

    def exists(self, task, criteria, include_finished=True):
        """
        Returns whether or not the given task exists in this queue. The list
        of which attributes that will be checked on the task for equality is
        determined by the entries in the criteria list.

        @type  task: Task instance
        @param task: Values in this task will be used to test for this task's
                     existence in the queue

        @type  criteria: List; cannot be None
        @param criteria: List of attribute names in the Task class; a task is
                         considered equal to the given task if the values for
                         all attributes listed in here are equal in an existing
                         task in the queue

        @type  include_finished: bool
        @param include_finished: If True, finished tasks will be included in the search;
                                 otherwise only running and waiting tasks are searched
                                 (defaults to True)
        """
        
        # Convert the list of attributes to check into a criteria dict used
        # by the storage API, using the task to test as the values
        find_criteria = {}
        for attr_name in criteria:
            if not hasattr(task, attr_name):
                raise ValueError('Task has no attribute named [%s]' % attr_name)
            find_criteria[attr_name] = getattr(task, attr_name)

        # Use the find functionality to determine if a task matches
        task = self.find(**find_criteria)
        if task is None or (not include_finished and
                            task.state in pulp.tasking.task.task_complete_states):
            return False
        return True
        
    
# no-frills task queue --------------------------------------------------------
    
class SimpleTaskQueue(TaskQueue):
    """
    Derived task queue that provides no special functionality
    """
    def enqueue(self, task, unique=False):
        pass
    
    def run(self, task):
        task.run()
    
    def complete(self, task):
        pass
    
    def find(self, **kwargs):
        return None
