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

from datetime import datetime, timedelta

from pulp.tasking.queue.base import SchedulingTaskQueue
from pulp.tasking.queue.storage import (
    VolatileStorage, MongoFinishedStorage, MongoStorage)

# fifo task queue -------------------------------------------------------------

class FIFOTaskQueue(SchedulingTaskQueue):
    """
    Task queue with threaded dispatcher that fires off tasks in the order in
    which they were enqueued and stores the finished tasks for a specified
    amount of time.
    """
    def __init__(self,
                 storage,
                 max_running=4,
                 finished_lifetime=timedelta(seconds=3600)):
        """
        @param max_running: the maximum number of tasks to have running
                            simultaneously
        @param finished_lifetime: timedelta object representing the length of
                                  time to keep information on finished tasks
        @return: FIFOTaskQueue instance
        """
        super(FIFOTaskQueue, self).__init__(storage)
        
        self.__running_count = 0
        self.max_running = max_running
        self.finished_lifetime = finished_lifetime
        
    # protected methods: scheduling
        
    def _finalilize_runs(self):
        # Clean up finished task data
        complete_tasks = self._storage.complete_tasks()
        if not complete_tasks:
            return
        now = datetime.now()
        for task in complete_tasks:
            if now - task.finish_time > self.finished_lifetime:
                self._storage.remove_task(task)
                
    def _get_tasks(self):
        # Get the next 'n' tasks to run, where is max - currently running tasks
        num_tasks = self.max_running - self.__running_count
        return self._storage.waiting_tasks()[:num_tasks]
    
    def _pre_run(self, task):
        # Adjust the running count
        self.__running_count += 1
        
    # public methods: queue operations
    
    def enqueue(self, task):
        # Set the 'next_time' scheduled run time on the task
        task.next_time = datetime.now()
        super(FIFOTaskQueue, self).enqueue(task)
        
    def complete(self, task):
        # Adjust the running count
        self.__running_count -= 1
        super(FIFOTaskQueue, self).complete(task)
        
# factory functions for volatile and mongo backed fifo queues -----------------

def volatile_fifo_queue():
    """
    Create a memory-backed fifo queue
    @return: FIFOTaskQueue instance with VolatileStorage storage
    """
    return FIFOTaskQueue(VolatileStorage())


def mongo_fifo_queue():
    """
    Create a memory-backed fifo queue
    @return: FIFOTaskQueue instance with MongoStorage storage
    """
    return FIFOTaskQueue(MongoFinishedStorage())