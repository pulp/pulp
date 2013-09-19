# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Red Hat, Inc.
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
from pulp.server.util import subdict


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
                self._purge_completed_task_cache()
            except:
                msg = _('Exception in task queue dispatcher thread:\n%(e)s')
                _LOG.critical(msg % {'e': traceback.format_exception(*sys.exc_info())})

    def _get_ready_tasks(self):
        """
        Algorithm at the heart of the task dispatcher. Gets the tasks that are
        ready to run (i.e. not blocked) within the limits of the available
        concurrency threshold and returns them. Note that this algorithm checks
        all the tasks as some may have a weight of 0.
        """
        self.__lock.acquire()
        try:
            tasks = []
            available_weight = self.concurrency_threshold - self.__running_weight
            for task in self.__waiting_tasks:
                if task.call_request.dependencies:
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
            task.run()
        finally:
            self.__lock.release()

    def _purge_completed_task_cache(self):
        """
        Purge expired tasks from the completed tasks cache.
        """
        expired_cutoff = datetime.now(dateutils.utc_tz()) - self.completed_task_cache_life
        index = 0 # index of the first non-expired cached task
        # the tasks stored in the cache are in ascending order of finish time
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
        Externally lock the task queue
        """
        self.__lock.acquire()

    def unlock(self):
        """
        Externally unlock the task queue
        """
        self.__lock.release()

    # task management methods --------------------------------------------------

    def batch_enqueue(self, task_list):
        """
        Enqueue multiple tasks so that dependency validation occurs while the
        queue is locked, eliminating race conditions where one task can complete
        before dependent tasks have time to validate their dependencies.
        @param task_list: list of tasks to enqueue
        @type task_list: list or tuple
        """
        self.__lock.acquire()
        try:
            map(self.enqueue, task_list)
        finally:
            self.__lock.release()

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
            self._validate_call_request_dependencies(task)
            self.__waiting_tasks.append(task)
            task.call_life_cycle_callbacks(dispatch_constants.CALL_ENQUEUE_LIFE_CYCLE_CALLBACK)
            self.__condition.notify()
        finally:
            self.__lock.release()

    def _validate_call_request_dependencies(self, task):
        """
        Validate a task's call request dependencies.
        NOTE: A task cannot be blocked by a task that is not currently (already)
              in the task queue
        @param task: task to have its call request dependencies validated
        @type  task: pulp.server.dispatch.task.Task
        """
        self.__lock.acquire()
        try:
            valid_call_request_dependency_ids = []
            for potential_blocking_task in itertools.chain(self.__running_tasks, self.__waiting_tasks):
                if potential_blocking_task.call_request.id not in task.call_request.dependencies:
                    continue
                valid_call_request_dependency_ids.append(potential_blocking_task.call_request.id)
            # DANGER this ignores valid call complete states of dependencies!!
            task.call_request.dependencies = subdict(task.call_request.dependencies, valid_call_request_dependency_ids)
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
        Remove a task call request id from all other task call requests' dependencies
        @param task: task to be removed
        @type  task: pulp.server.dispatch.task.Task
        """
        self.__lock.acquire()
        try:
            for potentially_blocked_task in self.__waiting_tasks[:]:

                if task.call_request.id not in potentially_blocked_task.call_request.dependencies:
                    continue

                valid_states = potentially_blocked_task.call_request.dependencies[task.call_request.id]

                if task.call_request_exit_state not in valid_states:
                    potentially_blocked_task.call_report.dependency_failures[task.call_request.id] = {'expected': valid_states,
                                                                                                      'actual': task.call_request_exit_state}
                    self.skip(potentially_blocked_task)
                else:
                    # remove the task from the blocking_tasks dict
                    potentially_blocked_task.call_request.dependencies.pop(task.call_request.id)

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
            # only decrement the running weight if the task was running
            if task in self.__running_tasks:
                self.__running_weight -= task.call_request.weight
            self.dequeue(task)
            self.__completed_tasks.append(task)
        finally:
            self.__lock.release()

    def skip(self, task):
        self.__lock.acquire()
        try:
            if task not in self.__waiting_tasks:
                return
            return task.skip()
        finally:
            self.__lock.release()

    def cancel(self, task):
        """
        Cancel a task's execution
        @param task: task to be canceled
        @type  task: pulp.server.dispatch.task.Task
        """
        self.__lock.acquire()
        try:
            return task.cancel()
        finally:
            self.__lock.release()

    # task query methods -------------------------------------------------------

    def get(self, call_request_id):
        """
        Get a single task by its id
        @param call_request_id: unique task id
        @type  call_request_id: str
        @return: task instance if found, otherwise None
        @rtype:  pulp.server.dispatch.task.Task or None
        """
        self.__lock.acquire()
        try:
            for task in itertools.chain(self.__completed_tasks,
                                        self.__running_tasks,
                                        self.__waiting_tasks):
                if task.call_request.id != call_request_id:
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

    def incomplete_tasks(self):
        """
        List of all tasks that have not yet completed
        @return: (potentially empty) iterator of incomplete tasks
        @rtype: iterator
        """
        self.__lock.acquire()
        try:
            return itertools.chain(self.__running_tasks[:],
                                   self.__waiting_tasks[:])
        finally:
            self.__lock.release()

    def completed_tasks(self):
        """
        List all of the completed tasks in the queue cache
        @return (potentially empty) list of tasks that are completed
        @rtype: list of pulp.server.dispatch.task.Task
        """
        self.__lock.acquire()
        try:
            return self.__completed_tasks[:]
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
            return itertools.chain(self.__completed_tasks[:],
                                   self.__running_tasks[:],
                                   self.__waiting_tasks[:])
        finally:
            self.__lock.release()
