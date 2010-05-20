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

import functools
import sys
import threading
import traceback
from datetime import datetime

from pulp.tasks.queue.base import TaskQueue


CREATED = 'created'
RESET = 'reset'
RUNNING = 'running'
FINISHED = 'finished'
ERROR = 'error'


class TaskThread(threading.Thread):
    """
    TaskThread class
    Thread objects that will call the target with the passed in arguments in a
    separate thread whenever execute() is called.
    Because of the difference in semantics from other thread classes, the
    thread will only exit with exit() is explicitly called.
    """
    def __init__(self, target, args=[], kwargs={}):
        super(TaskThread, self).__init__(target=target, args=args, kwargs=kwargs)
        self.__call = functools.partial(target, *args, **kwargs)
        self.__lock = threading.Lock()
        self.__exit = False
        self.daemon = True
        
        
    def __cmp__(self, other):
        """
        Next run time based comparison used by At and Cron task queues
        """
        return cmp(self.next, other.next)
    
    def __yield(self):
        self.__lock.acquire()
        self.__lock.acquire()
    
    def __continue(self):
        if not self.__lock.locked():
            return
        self.__lock.release()
    
    def run(self):
        while True:
            self.__yield()
            if self.__exit:
                return
            self.__call()
    
    def execute(self):
        """
        Execute the target callable in a separate thread
        """
        self.__continue()
    
    def exit(self):
        """
        Allow the separate thread to exit
        """
        self.__exit = True
        self.__continue()

    
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
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
        
        self.status = CREATED
        self.start_time = None
        self.finish_time = None
        self.next_time = None
        self.exception = None
        self.traceback = None
        
        self._queue = None
        
        self._thread = TaskThread(target=self._wrapper)
        self._thread.start()
        
    def __del__(self):
        self._thread.exit()
        
    @property
    def id(self):
        return self._thread.ident
  
    def _wrapper(self):
        """
        Protected wrapper that executes the callable and captures and records any
        exceptions in a separate thread.
        """
        ret = None
        self.status = RUNNING
        self.start_time = datetime.now()
        try:
            ret = self.callable(*self.args, **self.kwargs)
        except Exception, e:
            self.exception = e
            exec_info = sys.exc_info()
            self.traceback = traceback.format_exception(*exec_info)
            self.status = ERROR
        else:
            self.status = FINISHED
        self.finish_time = datetime.now()
        if self._queue is not None:
            self._queue.finished(self)        
        return ret
     
    def set_queue(self, task_queue):
        """
        Called by a TaskQueue instance for setting a back reference to the queue
        itself.
        """
        assert task_queue is None or isinstance(task_queue, TaskQueue)
        self._queue = task_queue
         
    def run(self):
        """
        Run this task's callable in a separate thread.
        """
        self._thread.execute()