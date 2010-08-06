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
    
    def find(self, **kwargs):
        """
        Find a task in this task queue
        @type kwargs: dict
        @param kwargs: task attributes and values as search criteria
        @return: Task instance on success, None otherwise
        """
        raise NotImplementedError()
    
# no-frills task queue --------------------------------------------------------
    
class SimpleTaskQueue(TaskQueue):
    """
    Derived task queue that provides no special functionality
    """
    def enqueue(self, task):
        task.wait()
    
    def run(self, task):
        task.run()
    
    def complete(self, task):
        pass
    
    def find(self, **kwargs):
        return None
    