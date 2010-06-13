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
import threading
import time
import traceback
import uuid

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
        
        self.status = task_created
        self.start_time = None
        self.finish_time = None
        self.next_time = None
        self.result = None
        self.exception = None
        self.traceback = None
        
    def _wrapper(self, args, kwargs):
        """
        Protected wrapper that executes the callable and captures and records any
        exceptions in a separate thread.
        @return: the return value of the callable
        """
        self.status = task_running
        self.start_time = datetime.datetime.now()
        try:
            result = self.func(*args, **kwargs)
        except Exception, e:
            self.exception = e
            exec_info = sys.exc_info()
            self.traceback = traceback.format_exception(*exec_info)
            self.status = task_error
        else:
            self.result = result
            if result is None:
                self.result = True # set to 'True' so we know it has run
            self.status = task_finished
        self.finish_time = datetime.datetime.now()
        if self.__queue is not None:
            self.__queue.finished(self)        
     
    def run(self, *args, **kwargs):
        """
        Run this task's callable in a separate thread.
        @return: None
        """
        self.result = None
        self.__thread = threading.Thread(target=self._wrapper,
                                        args=[args, kwargs])
        self.__thread.start()