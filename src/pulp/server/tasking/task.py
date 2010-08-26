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

task_states = (
    task_waiting,
    task_running,
    task_finished,
    task_error,
    task_timed_out,
    task_canceled,
    task_reset,
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

    def _exception_event(self):
        """
        Let the contextual thread know that an exception has been received.
        """
        if not hasattr(self.thread, 'exception_event'):
            return
        self.thread.exception_event()

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
        except TimeoutException:
            self.state = task_timed_out
            self._exception_event()
            _log.error('Task id:%s, method_name:%s: TIMED OUT' %
                       (self.id, self.method_name))
        except CancelException:
            self.state = task_canceled
            self._exception_event()
            _log.info('Task id:%s, method_name:%s: CANCELLED' %
                      (self.id, self.method_name))
        except Exception, e:
            self.state = task_error
            self.exception = repr(e)
            self.traceback = traceback.format_exception(*sys.exc_info())
            self._exception_event()
            _log.error('Task id:%s, method_name:%s:\n%s' %
                       (self.id, self.method_name, ''.join(self.traceback)))
        else:
            self.state = task_finished
            self.result = result
        self.finish_time = datetime.datetime.now()
        if self.complete_callback is not None:
            self.complete_callback(self)

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
