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

from threading import Condition, Lock, Thread


class TaskQueue(object):
    """
    Base task queue class to describe common functionality and interface
    """
    def __init__(self, max_dispatcher_sleep=1):
        self.max_dispatch_sleep = max_dispatcher_sleep
        
        self._lock = Lock()
        self._condition = Condition(self._lock)
        
        self._wait_queue = []
        self._running_tasks = {}
        self._finished_tasks = {}
        
        self._dispatcher = Thread(target=self._dispatch)
        self._dispatcher.daemon = True
        self._dispatcher.start()
    
    def _dispatch(self):
        raise NotImplementedError()
    
    def finished(self, task):
        raise NotImplementedError()
    
    def is_empty(self):
        """
        Check to see if there are any waiting or running tasks
        @return: True if there are no waiting or running tasks, False otherwise
        """
        return self._wait_queue or self._running_tasks
    
    def enqueue(self, task):
        raise NotImplementedError()
    
    def find(self, task_id):
        """
        Find a task in the task queue, given its task id
        @param task_id: Task instance id
        @return: Task instance with corresponding id if found, None otherwise
        """
        task = None
        self._lock.acquire()
        try:
            if task_id in self._finished_tasks:
                task = self._finished_tasks[task_id]
            elif task_id in self._running_tasks:
                task = self._running_tasks[task_id]
            else:
                for t in self._wait_queue:
                    if t.id == task_id:
                        task = t
                        break
        finally:
            self._lock.release()
        return task