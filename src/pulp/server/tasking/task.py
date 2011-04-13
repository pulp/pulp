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

import datetime
import logging
import sys
import time
import traceback
import uuid
from gettext import gettext as _

from pulp.server.tasking.taskqueue.thread import TimeoutException, CancelException
from pulp.server.tasking.scheduler import ImmediateScheduler


_log = logging.getLogger(__name__)

# task states -----------------------------------------------------------------

task_waiting = 'waiting'
task_running = 'running'
task_finished = 'finished'
task_error = 'error'
task_timed_out = 'timed out'
task_canceled = 'canceled'
task_suspended = 'suspended'

task_states = (
    task_waiting,
    task_running,
    task_finished,
    task_error,
    task_timed_out,
    task_canceled,
    task_suspended,
)

task_ready_states = (
    task_waiting,
)

task_incomplete_states = (
    task_waiting,
    task_running,
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
    Callable wrapper that schedules the call to take place at some later time
    than the immediate future. Provides framework for progress, result, and 
    error reporting as well as time limits on the call runtime in the form of a
    timeout and the ability to cancel the call.
    """
    def __init__(self,
                 callable,
                 args=[],
                 kwargs={},
                 scheduler=None,
                 timeout=None):
        """
        Create a Task for the passed in callable and arguments.
        @type callable: python callable
        @param callable: function, method, lambda, or object with __call__
        @type args: list
        @param args: positional arguments to be passed into the callable
        @type kwargs: dict
        @param kwargs: keyword arguments to be passed into the callable
        @type scheduler: None or L{scheduler.Scheduler} instance
        @param scheduler: scheduler to use when scheduling the task
                          defaults to ImmediateSchedule if None is passed in
        @type timeout: datetime.timedelta instance or None
        @param timeout: maximum length of time to allow task to run,
                        None means indefinitely
        """
        # identification
        self.id = str(uuid.uuid1(clock_seq=int(time.time() * 1000)))
        self.class_name = None
        if hasattr(callable, 'im_class'):
            self.class_name = callable.im_class.__name__
        self.method_name = callable.__name__

        # task resources
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
        self.scheduler = scheduler or ImmediateScheduler()
        self.timeout = timeout
        self.cancel_attempts = 0
        self._progress_callback = None

        # resources managed by the task queue to deliver events
        self.complete_callback = None
        self.failure_threshold = None
        self.schedule_threshold = None
        self.thread = None

        # resources for a task run
        self.state = task_waiting
        self.scheduled_time = None
        self.start_time = None
        self.finish_time = None

        # task progress, result, and error reporting
        self.progress = None
        self.result = None
        self.exception = None
        self.traceback = None
        self.consecutive_failures = 0

    def __cmp__(self, other):
        """
        Use the task's scheduled time to order them.
        """
        if not isinstance(other, Task):
            raise TypeError('No comparison defined between task and %s' %
                            type(other))
        if self.scheduled_time is None and other.scheduled_time is None:
            return 0
        if self.scheduled_time is None:
            return -1
        if other.scheduled_time is None:
            return 1
        return cmp(self.scheduled_time, other.scheduled_time)

    def __str__(self):

        def _name():
            if self.class_name is None:
                return self.method_name
            return '.'.join((self.class_name, self.method_name))

        def _args():
            return ', '.join([str(a) for a in self.args])

        def _kwargs():
            return ', '.join(['='.join((str(k), str(v))) for k, v in self.kwargs])

        return 'Task %s: %s(%s, %s)' % (self.id, _name(), _args(), _kwargs())

    def reset(self):
        """
        Reset this task to run again.
        """
        self.state = task_waiting
        self.start_time = None
        self.finish_time = None
        self.progress = None
        self.result = None
        self.exception = None
        self.traceback = None

    def schedule(self):
        """
        Schedule the task's next run time.
        @rtype: bool
        @return: True if the task is scheduled to run again, False if it's not
        """
        if self.failure_threshold is not None:
            if self.consecutive_failures == self.failure_threshold:
                _log.warn(_('%s has had %d failures and will not be scheduled again') %
                          (str(self), self.consecutive_failures))
                return False
        adjustments, scheduled_time = self.scheduler.schedule(self.scheduled_time)
        if scheduled_time is None:
            self.scheduled_time = None
            return False
        if adjustments:
            _log.warn(_('%s missed %d scheduled runs') % (str(self), adjustments))
        self.scheduled_time = scheduled_time
        return True

    # -------------------------------------------------------------------------

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

    def progress_callback(self, *args, **kwargs):
        """
        Provide a callback for runtime progress reporting.
        This is a pass-through to the function set by the set_progress method
        that records the results.
        """
        try:
            # NOTE, the self._progress_callback method should return a dict
            self.progress = self._progress_callback(*args, **kwargs)
        except Exception, e:
            _log.error('Exception, %s, in task %s progress callback: %s' %
                       (repr(e), self.id, self._progress_callback.__name__))
            raise

    # -------------------------------------------------------------------------

    def _exception_delivered(self):
        """
        Let the contextual thread know that an exception has been received.
        NOTE: this is a protected callback used for deliberate exception
        delivery, as in the case of a task cancellation or timeout
        it is not for error conditions, as they will not block the thread
        """
        if not hasattr(self.thread, 'exception_delivered'):
            return
        self.thread.exception_delivered()

    def _check_threshold(self):
        """
        Log when a task starts later than some timedelta threshold after it was
        scheduled to run.
        """
        if None in (self.start_time, self.schedule_threshold):
            return
        difference = self.start_time - self.scheduled_time
        if difference <= self.schedule_threshold:
            return
        _log.warn(_('%s\nstarted %s after its scheduled start time') %
                  (str(self), str(difference)))

    def run(self):
        """
        Run this task and record the result or exception.
        """
        if self.state is not task_waiting:
            self.reset()
        self.state = task_running
        self.start_time = datetime.datetime.now()
        self._check_threshold()
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

    # -------------------------------------------------------------------------

    def invoked(self, result):
        """
        Post I{method} invoked behavior.
        For synchronous I{methods}, we simply call I{succeeded()}
        @param result: The object returned by the I{method}.
        @type result: object.
        """
        self.succeeded(result)

    def succeeded(self, result):
        """
        Task I{method} invoked and succeeded.
        The task status is updated and the I{complete_callback}.
        @param result: The object returned by the I{method}.
        @type result: object.
        """
        self.consecutive_failures = 0
        self.result = result
        self.state = task_finished
        self.finish_time = datetime.datetime.now()
        self._complete()

    def failed(self, exception, tb=None):
        """
        Task I{method} invoked and raised an exception.
        @param exception: The I{representation} of the raised exception.
        @type exception: str
        @param tb: The formatted traceback.
        @type tb: str
        """
        self.consecutive_failures += 1
        self.exception = repr(exception)
        self.traceback = tb or traceback.format_exception(*sys.exc_info())
        _log.error('Task id:%s, method_name:%s:\n%s' % (self.id,
                                                        self.method_name,
                                                        ''.join(self.traceback)))
        self.state = task_error
        self.finish_time = datetime.datetime.now()
        self._complete()

    def _complete(self):
        """
        Safely call the complete callback
        """
        assert self.state in task_complete_states
        if self.complete_callback is None:
            return
        try:
            self.complete_callback(self)
        except Exception, e:
            _log.exception(e)

    # -------------------------------------------------------------------------

    def cancel(self):
        """
        Cancel a running task.
        NOTE: this is a noop if the task is already complete.
        """
        if self.state in task_complete_states:
            return
        if hasattr(self.thread, 'cancel'):
            self.thread.cancel()
        self.state = task_canceled
        self.finish_time = datetime.datetime.now()
        self._complete()

# asynchronous task -----------------------------------------------------------

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
