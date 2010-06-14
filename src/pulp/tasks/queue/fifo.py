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

_author_ = 'Jason L Connor <jconnor@redhat.com>'

from datetime import datetime, timedelta

from pulp.tasks.queue.base import SchedulingTaskQueue, VolatileTaskQueue


class FIFOTaskQueue(SchedulingTaskQueue, VolatileTaskQueue):
    """
    Task queue with threaded dispatcher that fires off tasks in the order in
    which they were enqueued and stores the finished tasks for a specified
    amount of time.
    """
    def __init__(self,
                 max_running=4,
                 finished_lifetime=timedelta(seconds=3600)):
        """
        @param max_running: the maximum number of tasks to have running
                            simultaneously
        @param finished_lifetime: timedelta object representing the length of
                                  time to keep information on finished tasks
        @return: FIFOTaskQueue instance
        """
        SchedulingTaskQueue.__init__(self)
        VolatileTaskQueue.__init__(self)
        
        self._running_count = 0
        self.max_running = max_running
        self.finished_lifetime = finished_lifetime
        
    # private methods: scheduling
        
    def _initialize_runs(self):
        """
        Clean up finished task data
        """
        # try to head-off a race condition on shutdown
        if not self._finished_tasks:
            return
        now = datetime.now()
        for id, task in self._finished_tasks.items():
            if now - task.finish_time > self.finished_lifetime:
                self._finished_tasks.pop(id)
                
    def _get_tasks(self):
        """
        Get the next 'n' tasks to run, where is max - currently running tasks
        """
        num_tasks = self.max_running - self._running_count
        return self._waiting_tasks[:num_tasks]
    
    def _pre_run(self):
        """
        Adjust the running count
        """
        self._running_count += 1
        
    # public methods: queue operations
        
    def complete(self, task):
        """
        Adjust the running count
        """
        self._running_count -= 1
        super(FIFOTaskQueue, self).complete(task)