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

import datetime
import logging
import sys
import time
import traceback
import uuid

from pulp.server.tasking.queue.thread import TimeoutException, CancelException


_log = logging.getLogger(__name__)

# task states -----------------------------------------------------------------

task_waiting = 'waiting'
task_running = 'running'
task_finished = 'finished'
task_error = 'error'
task_timed_out = 'timed out'
task_canceled = 'canceled'
task_reset = 'reset'
task_suspended = 'suspended'

task_states = (
    task_waiting,
    task_running,
    task_finished,
    task_error,
    task_timed_out,
    task_canceled,
    task_reset,
    task_suspended,
)

task_ready_states = (
    task_waiting,
    task_reset,
)

task_complete_states = (
    task_finished,
    task_error,
    task_timed_out,
    task_canceled,
)

# task ------------------------------------------------------------------------

class Task(object):
    """
    Task class
    Meta data for executing a long-running task.
    """
    def __init__(self, callable, args=[], kwargs={}, timeout=None):
        """
        Create a Task for the passed in callable and arguments.
        @param callable: function, method, lambda, or object with __call__
        @param args: positional arguments to be passed into the callable
        @param kwargs: keyword arguments to be passed into the callable
        @type timeout: datetime.timedelta instance or None
        @param timeout: maximum length of time to allow task to run,
                        None means indefinitely
        """
        # task resources
        self.id = str(uuid.uuid1(clock_seq=int(time.time() * 1000)))
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
        self._progress_callback = None
        self.timeout = timeout
        self.cancel_attempts = 0

        # resources managed by the task queue to deliver events
        self.complete_callback = None
        self.thread = None

        # resources for a task run
        self.method_name = callable.__name__
        self.state = task_waiting
        self.progress = None
        self.start_time = None
        self.finish_time = None
        self.result = None
        self.exception = None
        self.traceback = None
        self.scheduled_time = 0

    def _exception_delivered(self):
        """
        Let the contextual thread know that an exception has been received.
        """
        if not hasattr(self.thread, 'exception_delivered'):
            return
        self.thread.exception_delivered()

    def set_progress(self, arg, callback):
        """
        Setup a progress callback for the task, if it accepts one
        @type arg: str
        @param arg: name of the callable's progress callback argument
        @type callback: callable, returning a dict
        @param callback: value of the callable's progress callback argument
        """
        self.kwargs[arg] = self.progress_callback
        self._progress_callback = callback

    def run(self):
        """
        Run this task and record the result or exception.
        """
        assert self.state in task_ready_states
        self.state = task_running
        self.start_time = datetime.datetime.now()
        try:
            result = self.callable(*self.args, **self.kwargs)
            self.invoked(result)
        except TimeoutException:
            self.state = task_timed_out
            self._exception_delivered()
            _log.error('Task id:%s, method_name:%s: TIMED OUT' %
                       (self.id, self.method_name))
        except CancelException:
            self.state = task_canceled
            self._exception_delivered()
            _log.info('Task id:%s, method_name:%s: CANCELLED' %
                      (self.id, self.method_name))
        except Exception, e:
            self.failed(e)

    def progress_callback(self, *args, **kwargs):
        """
        Provide a callback for runtime progress reporting.
        """
        try:
            # NOTE, the self._progress_callback method should return a dict
            self.progress = self._progress_callback(*args, **kwargs)
        except Exception, e:
            _log.error('Exception, %s, in task %s progress callback: %s' %
                       (repr(e), self.id, self._progress_callback.__name__))
            raise

    def reset(self):
        """
        Reset this task's recorded data.
        """
        if self.state not in task_complete_states:
            return
        self.state = task_reset
        self.progress = None
        self._progress_callback = None
        self.start_time = None
        self.finish_time = None
        self.result = None
        self.exception = None
        self.traceback = None

    def succeeded(self, result):
        """
        Task I{method} invoked and succeeded.
        The task status is updated and the I{complete_callback}.
        @param result: The object returned by the I{method}.
        @type result: object.
        """
        self.result = result
        self.state = task_finished
        self.finish_time = datetime.datetime.now()
        self.__complete()

    def failed(self, exception, tb=None):
        """
        Task I{method} invoked and raised an exception.
        @param exception: The I{representation} of the raised exception.
        @type exception: str
        @param tb: The formatted traceback.
        @type tb: str
        """
        self.state = task_error
        self.finish_time = datetime.datetime.now()
        self.exception = repr(exception)
        self._exception_delivered()
        self.__complete()
        if tb:
            self.traceback = tb
        else:
            self.traceback = \
                traceback.format_exception(*sys.exc_info())
        _log.error(
            'Task id:%s, method_name:%s:\n%s' %
            (self.id,
             self.method_name,
             ''.join(self.traceback)))

    def invoked(self, result):
        """
        Post I{method} invoked behavior.
        For synchronous I{methods}, we simply call I{succeeded()}
        @param result: The object returned by the I{method}.
        @type result: object.
        """
        self.succeeded(result)

    def __complete(self):
        """
        Safely call the complete callback
        """
        if self.complete_callback is None:
            return
        try:
            self.complete_callback(self)
        except Exception, e:
            _log.exception(e)

    def stop(self):
        if self.thread:
            self.thread.cancel()
        self.state = task_canceled
        self.finish_time = datetime.datetime.now()
        self.__complete()


class AsyncTask(Task):
    """
    Asynchronous Task class
    Meta data for executing a long-running I{asynchronous} task.
    The I{method} is also expected to be asynchronous.  The I{method}
    execution is the first part of running the task and does not result in
    transition to a finished state.  Rather, the Task state is advanced
    by external processing.
    """

    def invoked(self, result):
        """
        The I{method} has been successfully invoked.
        Do __not__ advance the task state as this is managed
        by external processing.
        """
        pass

# Note: We want the "invoked" from Task, so we are not inheriting from
# AsyncTask
class RepoSyncTask(Task):
    """
    Repository Synchronization Task
    This task is responsible for implementing stop logic for a 
    repository synchronization 
    """
    def __init__(self, callable, args=[], kwargs={}, timeout=None):
        super(RepoSyncTask, self).__init__(callable, args, kwargs, timeout)
        self.synchronizer = None

    def set_synchronizer(self, sync_obj):
        self.synchronizer = sync_obj
        self.kwargs['synchronizer'] = self.synchronizer

    def stop(self):
        _log.info("RepoSyncTask stop invoked")
        if self.synchronizer:
            self.synchronizer.stop()
            # All synchronization work should be stopped
            # when this returns.  Will pass through to 
            # default stop behavior as a backup in case
            # something didn't stop
        super(RepoSyncTask, self).stop()
