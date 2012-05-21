# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import itertools
import logging
import sys
import threading
import traceback
from datetime import datetime, timedelta
from gettext import gettext as _

from pulp.common import dateutils
from pulp.server.db.model.dispatch import QueuedCall
from pulp.server.dispatch import constants as dispatch_constants


_LOG = logging.getLogger(__name__)

# task queue class -------------------------------------------------------------

class TaskQueue(object):
    """
    TaskQueue class
    Manager and dispatcher of concurrent, asynchronous task execution
    @ivar concurrency_threshold: measurement of total allowed concurrency
    @type concurrency_threshold: int
    @ivar dispatch_interval: time, in seconds, between checks for ready tasks
    @type dispatch_interval: float
    @ivar completed_task_cache_life: time, in seconds, to cache completed tasks
    @type completed_task_cache_life: float
    """

    def __init__(self,
                 concurrency_threshold,
                 dispatch_interval=0.5,
                 completed_task_cache_life=20.0):

        self.concurrency_threshold = concurrency_threshold
        self.dispatch_interval = dispatch_interval
        self.completed_task_cache_life = timedelta(seconds=completed_task_cache_life)
        self.queued_call_collection = QueuedCall.get_collection()

        self.__waiting_tasks = []
        self.__running_tasks = []
        self.__canceled_tasks = []
        self.__completed_tasks = []

        self.__running_weight = 0
        self.__exit = False
        self.__lock = threading.RLock()
        self.__condition = threading.Condition(self.__lock)
        self.__dispatcher = None

    # task dispatch methods ----------------------------------------------------

    def __dispatch(self):
        """
        Dispatcher thread loop
        """
        self.__lock.acquire()
        while True:
            try:
                self.__condition.wait(timeout=self.dispatch_interval)
                if self.__exit:
                    if self.__lock is not None:
                        self.__lock.release()
                    return
                ready_tasks = self._get_ready_tasks()
                for task in ready_tasks:
                    self._run_ready_task(task)
                self._cancel_tasks()
                self._clear_completed_task_cache()
            except Exception, e:
                msg = _('Exception in task queue dispatcher thread:\n%(e)s')
                _LOG.critical(msg % {'e': traceback.format_exception(*sys.exc_info())})

    def _get_ready_tasks(self):
        """
        Algorithm at the heart of the task scheduler. Gets the tasks that are
        ready to run (i.e. not blocked) within the limits of the available
        concurrency threshold and returns them. Note that this algorithm checks
        all the tasks as some may have a weight of 0.
        """
        self.__lock.acquire()
        try:
            tasks = []
            available_weight = self.concurrency_threshold - self.__running_weight
            for task in self.__waiting_tasks:
                if task.blocking_tasks:
                    continue
                if task.call_request.weight > available_weight:
                    continue
                available_weight -= task.call_request.weight
                tasks.append(task)
            return tasks
        finally:
            self.__lock.release()

    def _run_ready_task(self, task):
        """
        Run a ready task in a new thread
        """
        self.__lock.acquire()
        try:
            self.__waiting_tasks.remove(task)
            self.__running_tasks.append(task)
            self.__running_weight += task.call_request.weight
            task_thread = threading.Thread(target=task.run)
            task_thread.start()
            task.call_life_cycle_callbacks(dispatch_constants.CALL_RUN_LIFE_CYCLE_CALLBACK)
        finally:
            self.__lock.release()

    def _cancel_tasks(self):
        """
        Asynchronously cancel tasks that have been marked for cancellation
        """
        self.__lock.acquire()
        try:
            for task in self.__canceled_tasks:
                try:
                    task.cancel()
                except Exception, e:
                    _LOG.exception(e)
        finally:
            self.__lock.release()

    def _clear_completed_task_cache(self):
        """
        Clear expired tasks from the completed tasks cache.
        """
        expired_cutoff = datetime.now(dateutils.utc_tz()) - self.completed_task_cache_life
        index = 0 # index of the first non-expired cached task
        for i, task in enumerate(self.__completed_tasks):
            if task.call_report.finish_time > expired_cutoff:
                index = i
                break
        self.__completed_tasks = self.__completed_tasks[index:]

    # queue control methods ----------------------------------------------------

    def start(self):
        """
        Start the task queue
        """
        assert self.__dispatcher is None
        self.__lock.acquire()
        self.__exit = False # needed for re-start
        try:
            self.__dispatcher = threading.Thread(target=self.__dispatch)
            self.__dispatcher.setDaemon(True)
            self.__dispatcher.start()
        finally:
            self.__lock.release()

    def stop(self, clear_queued_calls=False):
        """
        Stop the task queue
        """
        assert self.__dispatcher is not None
        self.__lock.acquire()
        self.__exit = True
        self.__condition.notify()
        self.__lock.release()
        self.__dispatcher.join()
        self.__dispatcher = None
        if clear_queued_calls:
            self.queued_call_collection.remove(safe=True)

    def lock(self):
        """
        Existentially lock the task queue
        """
        self.__lock.acquire()

    def unlock(self):
        """
        Existentially unlock the task queue
        """
        self.__lock.release()

    # task management methods --------------------------------------------------

    def enqueue(self, task):
        """
        Enqueue (i.e. add) a task to the task queue.
        @param task: task to be run
        @type  task: pulp.server.dispatch.task.Task
        """
        self.__lock.acquire()
        try:
            queued_call = QueuedCall(task.call_request)
            task.queued_call_id = queued_call['_id']
            self.queued_call_collection.save(queued_call, safe=True)
            task.complete_callback = self._complete
            self._validate_blocking_tasks(task)
            self.__waiting_tasks.append(task)
            task.call_life_cycle_callbacks(dispatch_constants.CALL_ENQUEUE_LIFE_CYCLE_CALLBACK)
            self.__condition.notify()
        finally:
            self.__lock.release()

    def _validate_blocking_tasks(self, task):
        """
        Validate a task's blocking tasks.
        NOTE: A task cannot be blocked by a task that is not currently (already)
              in the task queue
        @param task: task to have its blockers validated
        @type  task: pulp.server.dispatch.task.Task
        """
        self.__lock.acquire()
        try:
            valid_blocking_tasks = set()
            for potential_blocking_task in itertools.chain(self.__running_tasks, self.__waiting_tasks):
                if potential_blocking_task.id not in task.blocking_tasks:
                    continue
                valid_blocking_tasks.add(potential_blocking_task.id)
            task.blocking_tasks = valid_blocking_tasks
        finally:
            self.__lock.release()

    def dequeue(self, task):
        """
        Dequeue (i.e. remove) a task from the task queue
        NOTE: This has no direct effect on whether the task gets run or not
        @param task: task to be removed
        @type  task: pulp.server.dispatch.task.Task
        """
        self.__lock.acquire()
        try:
            task.complete_callback = None
            self.queued_call_collection.remove({'_id': task.queued_call_id}, safe=True)
            task.queued_call_id = None
            if task in self.__waiting_tasks:
                self.__waiting_tasks.remove(task)
            if task in self.__running_tasks:
                self.__running_tasks.remove(task)
            self._unblock_tasks(task)
            task.call_life_cycle_callbacks(dispatch_constants.CALL_DEQUEUE_LIFE_CYCLE_CALLBACK)
        finally:
            self.__lock.release()

    def _unblock_tasks(self, task):
        """
        Remove a task from all other tasks' list of blockers
        @param task: task to be removed
        @type  task: pulp.server.dispatch.task.Task
        """
        self.__lock.acquire()
        try:
            for potentially_blocked_task in self.__waiting_tasks:
                potentially_blocked_task.blocking_tasks.discard(task.id)
        finally:
            self.__lock.release()

    def _complete(self, task):
        """
        Go through the necessary steps for a task that has completed its
        execution
        NOTE: This method is used as a callback for the task itself
        @param task: task that has completed
        @type  task: pulp.server.dispatch.task.Task
        """
        self.__lock.acquire()
        try:
            self.__running_weight -= task.call_request.weight
            self.dequeue(task)
            self.__completed_tasks.append(task)
        finally:
            self.__lock.release()

    def cancel(self, task):
        """
        Cancel a task's execution, if it has a cancel control hook
        @param task: task to be canceled
        @type  task: pulp.server.dispatch.task.Task
        @return: True if the task was marked for cancellation, False otherwise
        @rtype:  bool
        """
        self.__lock.acquire()
        try:
            if task.call_request.control_hooks[dispatch_constants.CALL_CANCEL_CONTROL_HOOK] is None:
                return False
            self.__canceled_tasks.append(task)
            return True
        finally:
            self.__lock.release()

    # task query methods -------------------------------------------------------

    def get(self, task_id):
        """
        Get a single task by its id
        @param task_id: unique task id
        @type  task_id: str
        @return: task instance if found, otherwise None
        @rtype:  pulp.server.dispatch.task.Task or None
        """
        self.__lock.acquire()
        try:
            for task in itertools.chain(self.__completed_tasks,
                                        self.__running_tasks,
                                        self.__waiting_tasks):
                if task.id != task_id:
                    continue
                return task
            return None
        finally:
            self.__lock.release()

    def find(self, *tags):
        """
        Find tasks that match the given call request tags
        @param tags: list of tags to match
        @type  tags: list of str
        @return: (potentially empty) list of tasks with matching tags
        @rtype:  list of pulp.server.dispatch.task.Task
        """
        self.__lock.acquire()
        try:
            tasks = []
            for task in itertools.chain(self.__completed_tasks,
                                        self.__running_tasks,
                                        self.__waiting_tasks):
                for tag in tags:
                    if tag not in task.call_request.tags:
                        break
                else:
                    tasks.append(task)
            return tasks
        finally:
            self.__lock.release()

    def waiting_tasks(self):
        """
        List all of the tasks waiting to be executed
        @return: (potentially empty) list of tasks that are waiting
        @rtype:  list of pulp.server.dispatch.task.Task
        """
        self.__lock.acquire()
        try:
            return self.__waiting_tasks[:]
        finally:
            self.__lock.release()

    def running_tasks(self):
        """
        List of all the tasks currently being executed
        @return: (potentially empty) list of tasks that are running
        @rtype:  list of pulp.server.dispatch.task.Task
        """
        self.__lock.acquire()
        try:
            return self.__running_tasks[:]
        finally:
            self.__lock.release()

    def all_tasks(self):
        """
        List of all tasks currently in the queue
        @return: (potentially empty) iterator of all tasks in the queue
        @rtype:  iterator over pulp.server.dispatch.task.Task
        """
        self.__lock.acquire()
        try:
            return itertools.chain(self.__running_tasks[:], self.__waiting_tasks[:])
        finally:
            self.__lock.release()
