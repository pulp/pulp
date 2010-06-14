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

_author_ = 'Jason L Connor <jconnor@redhat.com>'

import datetime
import functools
import sys
import time
import traceback
import uuid

from pulp.tasks.queue.base import SimpleTaskQueue

# task states -----------------------------------------------------------------

task_created = 'created'
task_reset = 'reset'
task_waiting = 'waiting'
task_running = 'running'
task_finished = 'finished'
task_error = 'error'

task_states = (
    task_created,
    task_reset,
    task_waiting,
    task_running,
    task_finished,
    task_error,
)

task_ready_states = (
    task_created,
    task_reset,
    task_waiting,
)

task_complete_states = (
    task_finished,
    task_error,
)

# task ------------------------------------------------------------------------
    
class Task(object):
    """
    Task class
    Meta data to be stored in the database for executing a long-running task and
    querying the status and results.
    """
    def __init__(self, callable, args=[], kwargs={}):
        """
        Create a Task for the passed in callable and arguments.
        @param callable: function, method, lambda, or object implementing _call_
        @param args: list of positional arguments to be passed into the callable
        @param kwargs: dictionary of keyword arguments to be passed into the callable
        """
        self.func = functools.partial(callable, *args, **kwargs)
        self.id = uuid.uuid1(clock_seq=int(time.time() * 1000))
        self.queue = SimpleTaskQueue()
        
        self.status = task_created
        self.start_time = None
        self.finish_time = None
        self.next_time = None
        self.result = None
        self.exception = None
        self.traceback = None

    def waiting(self):
        """
        Mark this task as waiting
        """
        assert self.status in task_ready_states
        self.status = task_waiting
        
    def run(self):
        """
        Run this task and record the result or exception
        """
        self.status = task_running
        self.start_time = datetime.datetime.now()
        try:
            result = self.func()
        except Exception, e:
            self.exception = e
            exc_info = sys.exc_info() # returns tuple (class, exception, traceback)
            self.traceback = traceback.format_exception(*exc_info)
            self.status = task_error
        else:
            self.result = result
            self.status = task_finished
        self.finish_time = datetime.datetime.now()
        self.queue.complete(self)
        
    def reset(self):
        """
        Reset this task's recorded data
        """
        if self.status not in task_complete_states:
            return
        self.status = task_reset
        self.start_time = None
        self.finish_time = None
        self.next_time = None
        self.result = None
        self.exception = None
        self.traceback = None
