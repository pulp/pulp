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

import datetime
import logging
import pickle
import sys
import time
import traceback
import threading
import uuid
from gettext import gettext as _

from pulp.common import dateutils
from pulp.server.db import model
from pulp.server.tasking.exception import (
    TimeoutException, CancelException, UnscheduledTaskException,
    SnapshotFailure)
from pulp.server.tasking.scheduler import ImmediateScheduler
from pulp.common.util import encode_unicode, decode_unicode

_log = logging.getLogger(__name__)

# task events ------------------------------------------------------------------

task_enqueue = 'enqueue'
task_dequeue = 'dequeue'
task_exit = 'exit' # task completed in any state

task_events = (task_enqueue, task_dequeue, task_exit)

# task states ------------------------------------------------------------------

task_waiting = 'waiting'
task_running = 'running'
task_suspended = 'suspended'
task_finished = 'finished'
task_error = 'error'
task_timed_out = 'timed out'
task_canceled = 'canceled'

task_states = (task_waiting,
               task_running,
               task_suspended,
               task_finished,
               task_error,
               task_timed_out,
               task_canceled)

task_ready_states = (task_waiting,)

task_incomplete_states = (task_waiting, task_running, task_suspended)

task_complete_states = (task_finished, task_error, task_timed_out, task_canceled)

# task -------------------------------------------------------------------------

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
                 args=None,
                 kwargs=None,
                 scheduler=None,
                 timeout=None,
                 weight=1):
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
        @type weight: int
        @param weight: the weight this task lends toward the task queue's
                       concurrency threshold
        """
        # validation
        if weight < 0:
            msg = _('Task for %(n)s created with a weight less than 0, reseting to default of 1')
            _log.error(msg % {'n': callable.__name__})
            weight = 1

        # identification
        self.id = str(uuid.uuid1(clock_seq=int(time.time() * 1000)))
        self.class_name = None
        if hasattr(callable, 'im_class'):
            self.class_name = callable.im_class.__name__
        self.method_name = callable.__name__
        self.snapshot_id = None

        # task resources
        self.callable = callable

        # encode args and kwargs using 'utf-8' encoding to allow i18n strings
        if args:
            self.args = [encode_unicode(arg) for arg in args]
        else:
            self.args = []
        if kwargs:
            for k, v in kwargs.items():
                kwargs[k] = encode_unicode(v)
        self.kwargs = dict(kwargs or {})

        self.scheduler = scheduler or ImmediateScheduler()
        self.timeout_delta = timeout
        self.weight = weight
        self._progress_callback = None

        # resources managed by the task queue to deliver events
        self.hooks = {}
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
        self.cancel_attempts = 0
        self.job_id = None

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
            return - 1
        if other.scheduled_time is None:
            return 1
        return cmp(self.scheduled_time, other.scheduled_time)

    def __eq__(self, other):
        """
        Keep from using the overridden __cmp__ for equality testing and
        membership testing.
        """
        # Without this, we run into an interesting little dilema, that if two
        # tasks have the same scheduled_time, they are considered equal.
        # This is great for sorting, but awful for testing equality, or more to
        # the point, membership.
        # This lead to a bug that would give off assertion errors in storage
        # when testing to make sure a task was not in two places at once, when
        # there was simply tasks with the same scheduled_time in two different
        # places.
        if not isinstance(other, Task):
            raise TypeError('No comparison defined between task and %s' %
                            type(other))
        # only return True if it's the same task
        return self.id == other.id

    def __str__(self):
        """
        Build  a string representation of the task.
        """
        # task name
        def _name():
            if self.class_name is None:
                return self.method_name
            return '.'.join((self.class_name, self.method_name))
        # task arguments
        def _args():
            return ', '.join([str(encode_unicode(a)) for a in self.args])
        # task keyword arguments
        def _kwargs():
            return ', '.join(['='.join((str(encode_unicode(k)), str(encode_unicode(v)))) for k, v in self.kwargs.items()])

        # put it all together
        return 'Task %s: %s(%s, %s)' % (self.id, _name(), _args(), _kwargs())

    # attribute setters --------------------------------------------------------

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

    # hook management ----------------------------------------------------------

    def add_enqueue_hook(self, hook):
        """
        Provide a hook to be called when the task is enqueued.
        The hook's only argument is the task.
        @type hook: callable
        """
        assert callable(hook)
        hook_list = self.hooks.setdefault(task_enqueue, [])
        hook_list.append(hook)

    def remove_enqueue_hook(self, hook):
        """
        Remove a hook to be called when the task is enqueued.
        @type hook: callable
        """
        hook_list = self.hooks.get(task_enqueue, [])
        try:
            hook_list.remove(hook)
        except ValueError:
            pass

    def add_dequeue_hook(self, hook):
        """
        Provide a hook to be called when the task is dequeued.
        The hook's only argument is the task.
        @type hook: callable
        """
        assert callable(hook)
        hook_list = self.hooks.setdefault(task_dequeue, [])
        hook_list.append(hook)

    def remove_dequeue_hook(self, hook):
        """
        Remove a hook to be called when the task is dequeued.
        @type hook: callable
        """
        hook_list = self.hooks.get(task_dequeue, [])
        try:
            hook_list.remove(hook)
        except ValueError:
            pass

    # snapshot methods ---------------------------------------------------------

    _copy_fields = ('id', 'class_name', 'method_name', 'failure_threshold',
                    'state', 'progress', 'consecutive_failures',
                    'cancel_attempts', 'job_id', 'weight')

    _pickle_fields = ('callable', 'args', 'kwargs', 'timeout_delta',
                      'schedule_threshold', '_progress_callback', 'start_time',
                      'finish_time', 'result', 'exception', 'traceback',
                      'hooks',)

    def snapshot(self):
        """
        Serialize the task into snapshot and store it in db
        """
        # start recording pertinent data
        data = {}
        data['task_class'] = pickle.dumps(self.__class__)
        # self-grooming
        callback = self.kwargs.pop('progress_callback', None) # self-referential
        # store the attributes of the task
        for field in self._copy_fields:
            data[field] = getattr(self, field)
        for field in self._pickle_fields:
            try:
                data[field] = pickle.dumps(getattr(self, field))
            except Exception, e:
                msg = _('Snapshot of %s failed error pickling field: %s') % (str(self), field)
                _log.error(msg + '\n%s\n%s' % (traceback.format_exc(), e.args[0]))
                raise SnapshotFailure('\n'.join((msg, e.args[0]))), None, sys.exc_info()[2]
        # restore groomed state
        if callback is not None:
            self.set_progress('progress_callback', self._progress_callback)
        # build the snapshot
        snapshot = model.TaskSnapshot(data)
        self.snapshot_id = snapshot._id
        return snapshot

    @classmethod
    def from_snapshot(cls, snapshot):
        """
        Retrieve task from a snapshot
        """
        def _dummy_callable():
            pass
        task = cls(_dummy_callable)
        for field in task._copy_fields:
            if field not in snapshot:
                continue
            setattr(task, field, snapshot[field])
        for field in task._pickle_fields:
            if field not in snapshot:
                continue
            setattr(task, field, pickle.loads(snapshot[field]))
        # NOTE: Ok, so this is tricky, but we no longer pickle the scheduler
        # field. This is because tasks are only snapshot-ed when they are
        # running, and since only snapshots are re-constituted into tasks on
        # start up, this means the tasks were running on shutdown. Therefore we
        # set the scheduler to an immediate scheduler, so the interrupted tasks
        # are resumed immediately. If the task was scheduled, the scheduling on
        # startup will create a new, different task for that.
        task.scheduler = ImmediateScheduler()
        # reset the progress callback
        if task._progress_callback is not None:
            task.set_progress('progress_callback', task._progress_callback)
        # record the current snapshot id
        task.snapshot_id = snapshot._id
        return task

    # scheduling methods -------------------------------------------------------

    def reset(self):
        """
        Reset this task to run again.
        """
        self.snapshot_id = None
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
        @raise UnscheduledTaskException: if the task scheduler does not return
                                         a next scheduled_time
        """
        if self.failure_threshold is not None:
            if self.consecutive_failures == self.failure_threshold:
                _log.warn(_('%s has had %d failures and will not be scheduled again') %
                          (str(self), self.consecutive_failures))
                raise UnscheduledTaskException(_('Too many consecutive failures for task: %s') % str(self))
        adjustments, scheduled_time = self.scheduler.schedule(self.scheduled_time)
        if scheduled_time is None:
            self.scheduled_time = None
            raise UnscheduledTaskException(_('No more scheduled runs for task: %s') % str(self))
        if adjustments > 1:
            _log.warn(_('%s missed %d scheduled runs') % (str(self), adjustments - 1))
        self.scheduled_time = scheduled_time

    # run the task -------------------------------------------------------------

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
        assert self.state in task_ready_states
        self.state = task_running
        self.start_time = datetime.datetime.now(dateutils.local_tz())
        self._check_threshold()
        try:
            result = self.callable(*self.args, **self.kwargs)
            self.invoked(result)
        except TimeoutException, e:
            _log.info(_('Task timed out: %s') % str(self))
            self.state = task_timed_out
            self._exception_delivered()
            self._complete()
        except CancelException, e:
            _log.info(_('Task canceled: %s') % str(self))
            self.state = task_canceled
            self._exception_delivered()
            self._complete()
        except Exception, e:
            self.failed(e)

    # state methods ------------------------------------------------------------

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
        self.state = task_finished
        self.result = result
        self.consecutive_failures = 0
        _log.info(_('Task succeeded: %s') % str(self))
        self._complete()

    def failed(self, exception, tb=None):
        """
        Task I{method} invoked and raised an exception.
        @param exception: The I{representation} of the raised exception.
        @type exception: str
        @param tb: The formatted traceback.
        @type tb: str
        """
        self.state = task_error
        try:
            self.exception = str(exception)
        except UnicodeEncodeError:
            self.exception = encode_unicode(exception)
        except UnicodeDecodeError:
            self.exception = decode_unicode(exception)
        self.traceback = tb or traceback.format_exception(*sys.exc_info())
        self.consecutive_failures += 1
        _log.error(_('Task failed: %s\n%s') % (str(self), ''.join(self.traceback)))
        self._complete()

    def _complete(self):
        """
        Safely call the complete callback
        """
        assert self.state in task_complete_states
        self.finish_time = datetime.datetime.now(dateutils.local_tz())
        if self.complete_callback is None:
            return
        try:
            self.complete_callback(self)
        except Exception, e:
            _log.exception(e)

    # premature termination ----------------------------------------------------

    def cancel(self):
        """
        Cancel a running task.
        NOTE: this is a noop if the task is already complete.
        """
        _log.warn(_('Deprecated base class Task.cancel() called for [%s]') % str(self))
        if self.state in task_complete_states:
            return
        if hasattr(self.thread, 'cancel'):
            self.thread.cancel()
        else:
            self.state = task_canceled
            _log.info(_('Task canceled: %s') % str(self))
            self._complete()

    def timeout(self):
        """
        Timeout a running task.
        NOTE: this is a noop if the task is already comlete.
        """
        _log.warn(_('Deprecated base class Task.timeout() called for [%s]') % str(self))
        if self.state in task_complete_states:
            return
        if hasattr(self.thread, 'timeout'):
            self.thread.timeout()
        else:
            self.state = task_timed_out
            _log.info(_('Task timed out: %s') % str(self))
            self._complete()

# asynchronous task ------------------------------------------------------------

class AsyncTask(Task):
    """
    Asynchronous Task class
    Meta data for executing a long-running I{asynchronous} task.
    The I{method} is also expected to be asynchronous.  The I{method}
    execution is the first part of running the task and does not result in
    transition to a finished state.  Rather, the Task state is advanced
    by external processing.
    @cvar __current: The current task running in the thread.
    @type __current: L{AsyncTask}
    """

    __current = threading.local()

    def __init__(self,
                 callable,
                 args=None,
                 kwargs=None,
                 scheduler=None,
                 timeout=None,
                 weight=0):
        # overriden only to provided a different default weight of 0
        super(AsyncTask, self).__init__(callable, args, kwargs, scheduler,
                                        timeout, weight)

    @classmethod
    def current(cls):
        """
        The current running task.
        @return: The current running task.
        @rtype: L{AsyncTask}
        """
        return cls.__current.task

    def run(self):
        """
        Set current running task and call super.
        """
        try:
            AsyncTask.__current.task = self
            return Task.run(self)
        finally:
            AsyncTask.__current.task = None

    def invoked(self, result):
        """
        The I{method} has been successfully invoked.
        Do __not__ advance the task state as this is managed
        by external processing.
        """
        pass
