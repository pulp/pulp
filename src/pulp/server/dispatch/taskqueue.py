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
import threading

from pulp.server.db.model.dispatch import ArchivedCall, QueuedCall
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.util import Singleton


_LOG = logging.getLogger(__name__)

# task queue class -------------------------------------------------------------

class TaskQueue(object):

    __metaclass__ = Singleton

    def __init__(self, concurrency_threshold, dispatch_interval=0.5):

        self.concurrency_threshold = concurrency_threshold
        self.dispatch_interval = dispatch_interval
        self.archived_call_collection = ArchivedCall.get_collection()
        self.queued_call_collection = QueuedCall.get_collection()

        self.__waiting_tasks = []
        self.__running_tasks = []
        self.__canceled_tasks = []

        self.__running_weight = 0
        self.__exit = False
        self.__lock = threading.RLock()
        self.__condition = threading.Condition(self.__lock)
        self.__dispatcher = None

    # task dispatch methods ----------------------------------------------------

    def __dispatch(self):
        """
        dispatcher thread loop
        """
        self.__lock.acquire()
        while True:
            self.__condition.wait(timeout=self.dispatch_interval)
            if self.__exit:
                if self.__lock is not None:
                    self.__lock.release()
                return
            for task in self._get_ready_tasks():
                self._run_ready_task(task)
            self._cancel_tasks()

    def _get_ready_tasks(self):
        """
        Algorithm at the heart of the task scheduler. Gets the tasks that are
        ready to run (i.e. not blocked) within the limits of the available
        concurrency threshold and returns them.
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
        self.__lock.acquire()
        try:
            self.__waiting_tasks.remove(task)
            self.__running_tasks.append(task)
            self.__running_weight += task.call_request.weight
            task_thread = threading.Thread(target=task.run)
            task_thread.start()
            task.call_execution_hooks(dispatch_constants.CALL_RUN_EXECUTION_HOOK)
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

    def start(self):
        """
        Start the task queue
        """
        assert self.__dispatcher is None
        self.__lock.acquire()
        try:
            self.__dispatcher = threading.Thread(target=self.__dispatch)
            self.__dispatcher.setDaemon(True)
            self.__dispatcher.start()
        finally:
            self.__lock.release()

    def stop(self):
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

    # task management methods --------------------------------------------------

    def enqueue(self, task):
        self.__lock.acquire()
        try:
            queued_call = QueuedCall(task.call_request)
            task.queued_call_id = queued_call['_id']
            self.queued_call_collection.save(queued_call, safe=True)
            task.complete_callback = self._complete
            self._validate_blocking_tasks(task)
            self.__waiting_tasks.append(task)
            task.call_execution_hooks(dispatch_constants.CALL_ENQUEUE_EXECUTION_HOOK)
            self.__condition.notify()
        finally:
            self.__lock.release()

    def _validate_blocking_tasks(self, task):
        self.__lock.acquire()
        try:
            valid_blocking_tasks = set()
            for potential_blocking_task in itertools.chain(self.__waiting_tasks, self.__running_tasks):
                if potential_blocking_task.id not in task.blocking_tasks:
                    continue
                valid_blocking_tasks.add(potential_blocking_task.id)
            task.blocking_tasks = valid_blocking_tasks
        finally:
            self.__lock.release()

    def dequeue(self, task):
        self.__lock.acquire()
        try:
            self.queued_call_collection.remove({'_id': task.queued_call_id}, safe=True)
            task.queued_call_id = None
            if task in self.__waiting_tasks:
                self.__waiting_tasks.remove(task)
            if task in self.__running_tasks:
                self.__running_tasks.remove(task)
            self._unblock_tasks(task)
            task.call_execution_hooks(dispatch_constants.CALL_DEQUEUE_EXECUTION_HOOK)
        finally:
            self.__lock.release()

    def _unblock_tasks(self, task):
        self.__lock.acquire()
        try:
            for potentially_blocked_task in self.__waiting_tasks:
                potentially_blocked_task.blocking_tasks.discard(task.id)
        finally:
            self.__lock.release()

    def _complete(self, task):
        self.__lock.acquire()
        try:
            archived_call = ArchivedCall(task.call_request, task.call_report)
            self.archived_call_collection.save(archived_call, safe=True)
            self.dequeue(task)
        finally:
            self.__lock.release()

    def cancel(self, task):
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
        self.__lock.acquire()
        try:
            for task in itertools.chain(self.__waiting_tasks, self.__running_tasks):
                if task.id != task_id:
                    continue
                return task
        finally:
            self.__lock.release()

    def find(self, *tags):
        self.__lock.acquire()
        try:
            tasks = []
            for task in itertools.chain(self.__waiting_tasks, self.__running_tasks):
                for tag in tags:
                    if tag not in task.call_request.tags:
                        break
                else:
                    tasks.append(task)
            return tasks
        finally:
            self.__lock.release()

    def waiting_tasks(self):
        self.__lock.acquire()
        try:
            return self.__waiting_tasks[:]
        finally:
            self.__lock.release()

    def running_tasks(self):
        self.__lock.acquire()
        try:
            return self.__running_tasks[:]
        finally:
            self.__lock.release()

    def all_tasks(self):
        self.__lock.acquire()
        try:
            return itertools.chain(self.__waiting_tasks[:], self.__running_tasks[:])
        finally:
            self.__lock.release()
