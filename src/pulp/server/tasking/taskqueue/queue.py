# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
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

from pulp.server.tasking.scheduler import ImmediateScheduler
from pulp.server.tasking.taskqueue.thread import  (
    DRLock, TaskThread, ThreadStateError)
from pulp.server.tasking.taskqueue.storage import VolatileStorage
from pulp.server.tasking.task import task_complete_states, task_running

# log file --------------------------------------------------------------------

_log = logging.getLogger('pulp')

# fifo task queue -------------------------------------------------------------

class TaskQueue(object):
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
        @return: TaskQueue instance
        """
        self.max_running = max_running
        self.finished_lifetime = finished_lifetime

        self.__lock = threading.RLock()
        #self.__lock = DRLock()
        self.__condition = threading.Condition(self.__lock)

        self.__running_count = 0
        self.__storage = VolatileStorage()
        self.__canceled_tasks = []
        self.__exit = False

        self.__dispatcher_timeout = 0.5
        self.__dispatcher = threading.Thread(target=self._dispatch)
        self.__dispatcher.setDaemon(True)
        self.__dispatcher.start()

    def __del__(self):
        """
        Cleanly shutdown the dispatcher thread
        """
        self.__lock.acquire()
        self.__exit = True
        self.__condition.notify()
        self.__lock.release()
        self.__dispatcher.join()

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
                    if self.__exit: # exit immediately after waking up
                        return
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
        ready_tasks = []
        num_tasks = self.max_running - self.__running_count
        now = datetime.utcnow()
        while len(ready_tasks) < num_tasks:
            if self.__storage.num_waiting() == 0:
                break
            if self.__storage.peek_waiting().scheduled_time > now:
                break
            ready_tasks.append(self.__storage.dequeue_waiting())
        return ready_tasks

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

            # If the cancel call indicates that the thread is not in a cancellable state,
            # leave it on the queue so we attempt to cancel it again the next time the
            # dispatcher runs a cancel.
            try:
                task.cancel()
                self.__canceled_tasks.remove(task)
            except ThreadStateError:
                task.cancel_attempts += 1
                _log.warn('Attempt to cancel task for method [%s] was unable to complete at this time. ' % task.method_name +
                          'This is the [%s] attempt to cancel the task. The task will be resubmitted ' % task.cancel_attempts +
                          'for cancellation. This does not represent an error but is logged so ' +
                          'we can get metrics on the regularity at which this occurs.')

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
                self.__storage.remove_complete(task)

    # public methods: queue operations

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
        self.__lock.acquire()
        try:
            fields = ('class_name', 'method_name', 'args', 'kwargs')
            if unique and self.exists(task, fields, include_finished=False):
                return False
            if not task.schedule():
                return False
            task.complete_callback = self.complete
            self.__storage.enqueue_waiting(task)
            self.__condition.notify()
            return True
        finally:
            self.__lock.release()

    def remove(self, task):
        self.__lock.acquire()
        try:
            task.scheduler = ImmediateScheduler()
            if task.state is task_running:
                return
            if task.state not in task_complete_states:
                self.__storage.remove_waiting(task)
        finally:
            self.__lock.release()

    def run(self, task):
        """
        Run a task from this task queue
        @type task: pulp.tasking.task.Task
        @param task: Task instance
        """
        self.__lock.acquire()
        try:
            self.__running_count += 1
            self.__storage.store_running(task)
            task.thread = TaskThread(target=task.run)
            task.thread.start()
        finally:
            self.__lock.release()

    def complete(self, task):
        """
        Mark a task run as completed
        @type task: pulp.tasking.task.Task
        @param task: Task instance
        """
        self.__lock.acquire()
        try:
            self.__running_count -= 1
            self.__storage.remove_running(task)
            self.__storage.store_complete(task)
            task.thread = None
            task.complete_callback = None
            # try to re-enqueue to handle recurring tasks
            if self.enqueue(task):
                self.__storage.remove_complete(task)
        finally:
            self.__lock.release()

    def cancel(self, task):
        """
        Cancel a running task.
        @type task: pulp.tasking.task.Task
        @param task: Task instance
        """
        self.__lock.acquire()
        try:
            self.__canceled_tasks.append(task)
        finally:
            self.__lock.release()

    def find(self, **kwargs):
        """
        Find tasks in this task queue.
        @type kwargs: dict
        @param kwargs: task attributes and values as search criteria
        @type include_finished: bool
        @return: list of L{Task} instances, empty if no tasks match
        """
        self.__lock.acquire()
        try:
            return self.__storage.find(kwargs)
        finally:
            self.__lock.release()

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
        tasks = self.find(**find_criteria)
        if not tasks:
            return False
        if include_finished:
            return True
        for t in tasks:
            if t.state not in task_complete_states:
                return True
        return False
