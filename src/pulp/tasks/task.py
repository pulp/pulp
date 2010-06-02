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

from pulp.tasks.queue.base import TaskQueue


CREATED = 'created'
RESET = 'reset'
RUNNING = 'running'
FINISHED = 'finished'
ERROR = 'error'

    
class Task(object):
    """
    Task class
    Execute a long-running task in its own thread
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
        
        self.status = CREATED
        self.start_time = None
        self.finish_time = None
        self.next_time = None
        self.exception = None
        self.traceback = None
        
        self.__queue = None
        self.__thread = None
        
    def __cmp__(self, other):
        """
        Next run time based comparison used by At and Cron task queues
        """
        return cmp(self.next_time, other.next_time)
     
    @property
    def thread_id(self):
        if self.__thread is None:
            return None
        return self.__thread.ident
  
    def _wrapper(self, args, kwargs):
        """
        Protected wrapper that executes the callable and captures and records any
        exceptions in a separate thread.
        @return: the return value of the callable
        """
        self.status = RUNNING
        self.start_time = datetime.datetime.now()
        try:
            self.func(*args, **kwargs)
        except Exception, e:
            self.exception = e
            exec_info = sys.exc_info()
            self.traceback = traceback.format_exception(*exec_info)
            self.status = ERROR
        else:
            self.status = FINISHED
        self.finish_time = datetime.datetime.now()
        if self.__queue is not None:
            self.__queue.finished(self)        
     
    def set_queue(self, task_queue):
        """
        Called by a TaskQueue instance for setting a back reference to the queue
        itself.
        @param task_queue: a TaskQueue instance or None
        @return: None
        """
        assert task_queue is None or isinstance(task_queue, TaskQueue)
        self.__queue = task_queue
         
    def run(self, *args, **kwargs):
        """
        Run this task's callable in a separate thread.
        @return: None
        """
        self.__thread = threading.Thread(target=self._wrapper,
                                        args=[args, kwargs])
        # XXX set thread to daemon here?
        #self.__thread.daemon = True
        self.__thread.start()
        
    def wait(self):
        """
        Wait for a single run of this task
        @return: None
        """
        while self.__thread is None:
            time.sleep(0.0005)
        self.__thread.join()