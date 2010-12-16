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

import logging
import sys
import threading
import traceback
from datetime import datetime, timedelta

from pulp.server.tasking.queue.base import TaskQueue
from pulp.server.tasking.queue.thread import  DRLock, TaskThread
from pulp.server.tasking.queue.storage import VolatileStorage
from pulp.server.tasking.task import task_complete_states

# log file --------------------------------------------------------------------

_log = logging.getLogger('pulp')

# fifo task queue -------------------------------------------------------------

class FIFOTaskQueue(TaskQueue):
    """
    Task queue with threaded dispatcher that fires off tasks in the order in
    which they were enqueued and stores the finished tasks for a specified
    amount of time.
    """
    def __init__(self,
                 max_running=4,
                 finished_lifetime=timedelta(seconds=3600)):
        """
        @type max_running: int
        @param max_running: maximum number of tasks to run simultaneously
                        None means indefinitely
        @type finished_lifetime: datetime.timedelta instance
        @param finished_lifetime: length of time to keep finished tasks
        @return: FIFOTaskQueue instance
        """
        self.max_running = max_running
        self.finished_lifetime = finished_lifetime

        self.__lock = threading.RLock()
        #self.__lock = DRLock()
        self.__condition = threading.Condition(self.__lock)

        self.__running_count = 0
        self.__storage = VolatileStorage()
        self.__canceled_tasks = []

        self.__dispatcher_timeout = 0.5
        self.__dispatcher = threading.Thread(target=self._dispatch)
        self.__dispatcher.setDaemon(True)
        self.__dispatcher.start()

    # protected methods: scheduling

    def _dispatch(self):
        """
        Scheduling method that that executes the scheduling hooks.
        """
        self.__lock.acquire()
        try:
            try:
                while True:
                    self.__condition.wait(self.__dispatcher_timeout)
                    for task in self._get_tasks():
                        self.run(task)
                    self._cancel_tasks()
                    self._timeout_tasks()
                    self._cull_tasks()
            except Exception:
                _log.critical('Exception in FIFO Queue Dispatch Thread\n%s' %
                              ''.join(traceback.format_exception(*sys.exc_info())))
                raise
        finally:
            self.__lock.release()

    def _get_tasks(self):
        """
        Get the next 'n' tasks to run, where is max - currently running tasks
        """
        num_tasks = self.max_running - self.__running_count
        return self.__storage.waiting_tasks()[:num_tasks]

    def _cancel_tasks(self):
        """
        Stop any tasks that have been flagged as canceled.
        """
        for task in self.__canceled_tasks[:]:
            if task.state in task_complete_states:
                self.__canceled_tasks.remove(task)
                continue
            if task.thread is None:
                continue
            task.thread.cancel()
            self.__canceled_tasks.remove(task)

    def _timeout_tasks(self):
        """
        Stop tasks that have met or exceeded their timeout length.
        """
        running_tasks = self.__storage.running_tasks()
        if not running_tasks:
            return
        now = datetime.now()
        for task in running_tasks:
            # the task.start_time can be None if the task has been 'run' by the
            # queue, but the task thread has not had a chance to execute yet
            if None in (task.timeout, task.start_time):
                continue
            if now - task.start_time < task.timeout:
                continue
            task.thread.timeout()

    def _cull_tasks(self):
        """
        Clean up finished task data
        """
        complete_tasks = self.__storage.complete_tasks()
        if not complete_tasks:
            return
        now = datetime.now()
        for task in complete_tasks:
            if now - task.finish_time > self.finished_lifetime:
                self.__storage.remove_task(task)

    # public methods: queue operations

    def enqueue(self, task, unique=False):
        self.__lock.acquire()
        try:
            fields = ('method_name', 'args', 'kwargs')
            if unique and self.exists(task, fields, include_finished=False):
                return False
            task.complete_callback = self.complete
            self.__storage.add_waiting_task(task)
            self.__condition.notify()
            return True
        finally:
            self.__lock.release()

    def run(self, task):
        self.__lock.acquire()
        try:
            self.__running_count += 1
            self.__storage.add_running_task(task)
            task.thread = TaskThread(target=task.run)
            task.thread.start()
        finally:
            self.__lock.release()

    def complete(self, task):
        self.__lock.acquire()
        try:
            self.__running_count -= 1
            self.__storage.add_complete_task(task)
            task.thread = None
            task.complete_callback = None
        finally:
            self.__lock.release()

    def cancel(self, task):
        self.__lock.acquire()
        try:
            self.__canceled_tasks.append(task)
        finally:
            self.__lock.release()

    def find(self, **kwargs):
        self.__lock.acquire()
        try:
            return self.__storage.find_tasks(kwargs)
        finally:
            self.__lock.release()
