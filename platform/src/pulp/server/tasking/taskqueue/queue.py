# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging
import sys
import threading
import traceback
from datetime import datetime, timedelta
from gettext import gettext as _

from pulp.common import dateutils
from pulp.server.tasking.exception import (
    TaskThreadStateError, UnscheduledTaskException, NonUniqueTaskException)
from pulp.server.tasking.scheduler import (
    AtScheduler, ImmediateScheduler, IntervalScheduler)
from pulp.server.tasking.taskqueue.taskthread import TaskThread
from pulp.server.tasking.taskqueue.storage import VolatileStorage
from pulp.server.tasking.task import (
    task_enqueue, task_dequeue, task_exit, task_running, task_finished,
    task_error, task_timed_out, task_canceled, task_complete_states)

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
                 max_concurrency=4,
                 finished_lifetime=timedelta(seconds=3600),
                 failure_threshold=None,
                 schedule_threshold=None,
                 storage=None,
                 dispatch_interval=0.5):
        """
        @type max_concurrency: int
        @param max_concurrency: maximum sum of task weights to run simultaneously
        @type finished_lifetime: datetime.timedelta instance
        @param finished_lifetime: length of time to keep finished tasks
                                  None means indefinitely
        @type failures_threhold: int
        @param failure_threshold: number of consecutive failures a task can
                                  have before it will no longer be scheduled
                                  to run
        @type schedule_threshold: None or datetime.timedelta instance
        @param schedule_threshold: a time length that if exceeded by the
                                   difference between a task's scheduled time
                                   and the task's start time, constitutes a
                                   warning
        @type storage: L{pulp.server.tasking.taskqueue.storage.Storage}
        @param storage: the task storage backend to use,
                        defaults to VolatileStorage
        @type dispatch_interval: float
        @param dispatch_interval: time interval, in seconds, between runs of
                                  the task dispatcher
        @return: TaskQueue instance
        """
        self.max_concurrency = max_concurrency
        self.finished_lifetime = finished_lifetime
        self.failure_threshold = failure_threshold
        self.schedule_threshold = schedule_threshold

        self.__lock = threading.RLock()
        self.__condition = threading.Condition(self.__lock)

        self.__running_weight = 0
        self.__storage = storage or VolatileStorage()
        self.__canceled_tasks = []
        self.__exit = False

        self.__dispatcher_timeout = dispatch_interval
        self.__dispatcher = threading.Thread(target=self._dispatch)
        self.__dispatcher.setDaemon(True)
        self.__dispatcher.start()

    def __del__(self):
        """
        Destroy the TaskQueue.
        All that is needed is to cleanly shutdown the dispatcher thread
        """
        self._cancel_dispatcher()

    def _cancel_dispatcher(self):
        """
        Shutdown the dispatcher thread.
        """
        self.__lock.acquire()
        self.__exit = True
        self.__condition.notify()
        self.__lock.release()
        self.__dispatcher.join()

    # scheduling ---------------------------------------------------------------

    def _dispatch(self):
        """
        Scheduling method that that executes the scheduling hooks.
        """
        self.__lock.acquire()
        while True:
            try:
                self.__condition.wait(self.__dispatcher_timeout)
                if self.__exit: # exit immediately after waking up
                    if self.__lock is not None:
                        self.__lock.release()
                    return
                for task in self._get_tasks():
                    self.run(task)
                self._cancel_tasks()
                self._timeout_tasks()
                self._cull_tasks()
            except Exception:
                _log.critical('Exception in FIFO Queue Dispatch Thread\n%s' %
                              ''.join(traceback.format_exception(*sys.exc_info())))

    def _get_tasks(self):
        """
        Get the next 'n' tasks to run, where n is max - currently running tasks
        """
        ready_tasks = []
        ready_weight = 0
        available_weight = self.max_concurrency - self.__running_weight
        now = datetime.now(dateutils.local_tz())
        while ready_weight < available_weight:
            if self.__storage.num_waiting() == 0:
                break
            task = self.__storage.peek_waiting()
            if task.scheduled_time is not None and task.scheduled_time > now:
                break
            if task.weight + ready_weight > available_weight:
                break
            ready_weight += task.weight
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
            except TaskThreadStateError:
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
        now = datetime.now(dateutils.local_tz())
        for task in running_tasks:
            # the task.start_time can be None if the task has been 'run' by the
            # queue, but the task thread has not had a chance to execute yet
            if None in (task.timeout_delta, task.start_time):
                continue
            if now - task.start_time < task.timeout_delta:
                continue
            task.timeout()

    def _cull_tasks(self):
        """
        Clean up finished task data
        """
        complete_tasks = self.__storage.complete_tasks()
        if not complete_tasks:
            return
        now = datetime.now(dateutils.local_tz())
        for task in complete_tasks:
            if now - task.finish_time > self.finished_lifetime:
                self.__storage.remove_complete(task)

    # task hook execution ------------------------------------------------------

    def _execute_hooks(self, task, key):
        hook_list = task.hooks.get(key, [])
        for hook in hook_list:
            try:
                hook(task)
            except Exception, e:
                msg = _('Task %(t)s\nException in task %(k)s hook\n%(tb)s')
                _log.critical(msg % {'k': key, 't': str(task),
                                     'tb': ''.join(traceback.format_exception(*sys.exc_info()))})

    # queue operations ---------------------------------------------------------

    def _test_uniqueness(self, task, unique):
        """
        Does nothing if the task is unique, raise an exception otherwise.
        @raises: NonUniqueTaskException
        """
        def _raise_exception(match):
            msg = _('Task [%s] %s %s conflicts with [%s] %s %s and cannot be enqueued')
            raise NonUniqueTaskException(msg % (task.id, str(task), str(task.scheduler),
                                                match.id, str(match), str(match.scheduler)))

        fields = ('class_name', 'method_name', 'args')
        for match in self.exists(task, fields, include_finished=False):
            if isinstance(task.scheduler, ImmediateScheduler):
                # if unique is True, do not allow more than one immediate task
                if unique and isinstance(match.scheduler, ImmediateScheduler):
                    _raise_exception(match)
            elif isinstance(task.scheduler, AtScheduler):
                # at scheduled tasks can only conflict if there's another at
                # scheduled task for the same time
                if isinstance(match.scheduler, AtScheduler) and \
                   task.scheduler.scheduled_time == match.scheduler.scheduled_time:
                    _raise_exception(match)
            elif isinstance(task.scheduler, IntervalScheduler):
                # there may be only one interval scheduled task at a time
                if isinstance(match.scheduler, IntervalScheduler):
                    _raise_exception(match)

    def enqueue(self, task, unique=False):
        """
        Add a task to the task queue
        @type task: pulp.tasking.task.Task
        @param task: Task instance
        @type unique: bool
        @param unique: If True, the task will only be added if there are no
                       non-finished tasks with the same method_name, args,
                       and kwargs; otherwise the task will always be added
        @raise NonUniqueTaskException: if the unique flag is True and the task
                                       is not unique
        @raise UnscheduledTaskException: if the enqueued task cannot be scheduled
        """
        self.__lock.acquire()
        try:
            self._test_uniqueness(task, unique) # NonUniqueTaskException
            task.schedule() # UnscheduledTaskException
            task.reset()
            task.complete_callback = self.complete
            # setup error condition parameters, if not overridden by the task
            if task.failure_threshold is None:
                task.failure_threshold = self.failure_threshold
            if task.schedule_threshold is None:
                task.schedule_threshold = self.schedule_threshold
            self.__storage.enqueue_waiting(task)
            self._execute_hooks(task, task_enqueue)
            self.__condition.notify()
        finally:
            self.__lock.release()

    def remove(self, task):
        """
        Remove a task from task queue, ensuring that a running task finishes and
        continues to be tracked by the system.
        """
        self.__lock.acquire()
        try:
            task.scheduler = ImmediateScheduler()
            if task.state is task_running:
                return
            if task.state not in task_complete_states:
                self.__storage.remove_waiting(task)
                self._execute_hooks(task, task_dequeue)
        finally:
            self.__lock.release()

    def drop_complete(self, task):
        """
        Stop tracking a completed task.
        Used to remove task history for deleted resources.
        """
        self.__lock.acquire()
        try:
            if task not in self.__storage.complete_tasks():
                return
            self.__storage.remove_complete(task)
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
            self.__running_weight += task.weight
            self.__storage.store_running(task)
            task.thread = TaskThread(target=task.run)
            task.thread.start()
            self._execute_hooks(task, task_running)
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
            self.__running_weight -= task.weight
            self.__storage.remove_running(task)
            task.thread = None
            task.complete_callback = None
            # execute the task hooks
            self._execute_hooks(task, task_exit)
            if task.state is task_canceled:
                self._execute_hooks(task, task_canceled)
            elif task.state is task_error:
                self._execute_hooks(task, task_error)
            elif task.state is task_finished:
                self._execute_hooks(task, task_finished)
            elif task.state is task_timed_out:
                self._execute_hooks(task, task_timed_out)
            self._execute_hooks(task, task_dequeue)
            # it is important for completed tasks to be in the completed task
            # storage, however briefly
            self.__storage.store_complete(task)
            try:
                # try to re-enqueue recurring tasks
                self.enqueue(task)
            except UnscheduledTaskException:
                pass
            else:
                # if successful, remove them from completed storage
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

    def reschedule(self, task, scheduler):
        """
        Reschedule an already scheduled task.
        @type task: pulp.server.tasking.task.Task instance
        @param task: task to reschedule
        @type scheduler: pulp.server.tasking.scheduler.Scheduler instance
        @param scheduler: scheduler representing task's new schedule
        """
        # NOTE this needs to be done here to ensure the scheduler is assigned
        # before the task changes state
        self.__lock.acquire()
        try:
            task.scheduler = scheduler
            # most likely we won't be rescheduling tasks that have completed
            # but just in case...
            if task in self.__storage.complete_tasks():
                self.__storage.remove_complete(task)
                self.enqueue(task)
        finally:
            self.__lock.release()

    # task query operations ----------------------------------------------------

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
        @rtype: list
        @return: list of all the matching tasks, empty if there are none
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
        # NOTE This method used to return a boolean, it now returns a list of
        # all the tasks matching the criteria. The list is empty if no matching
        # tasks are found. This allows the same boolean semantics to be used
        # as an empty list evaluates to False and a non-empty one to True.
        if not tasks or include_finished:
            return tasks
        return [t for t in tasks if t.state not in task_complete_states]

    def waiting_tasks(self):
        self.__lock.acquire()
        try:
            return tuple(self.__storage.waiting_tasks())
        finally:
            self.__lock.release()

    def running_tasks(self):
        self.__lock.acquire()
        try:
            return tuple(self.__storage.running_tasks())
        finally:
            self.__lock.release()

    def incomplete_tasks(self):
        self.__lock.acquire()
        try:
            return tuple(self.__storage.incomplete_tasks())
        finally:
            self.__lock.release()

    def complete_tasks(self):
        self.__lock.acquire()
        try:
            return tuple(self.__storage.complete_tasks())
        finally:
            self.__lock.release()

    def all_tasks(self):
        self.__lock.acquire()
        try:
            return tuple(self.__storage.all_tasks())
        finally:
            self.__lock.release()
