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

__author__ = 'Jason L Connor <jconnor@redhat.com>'

import sys
import threading
import traceback
from datetime import datetime


CREATED = 'created'
RUNNING = 'running'
FINISHED = 'finished'
ERROR = 'error'


class Task(object):
    """
    Task class
    Used to run long-running tasks in their own thread.
    """
    def __init__(self, callable, args=[], kwargs={}):
        """
        Create a Task for the passed in callable and arguments.
        @param callable: function, method, lambda, or object implementing __call__
        @param args: list of positional arguments to be passed into the callable
        @param kwargs: dictionary of keyword arguments to be passed into the callable
        """
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
        
        self.status = CREATED
        self.start_time = None
        self.finish_time = None
        self.exception = None
        self.traceback = None
        
        self.__queue = None
        
        self.__thread = threading.Thread(target=self.wrapper)
        self.__thread.start()
        
    @property
    def id(self):
        return self.__thread.ident
    
    def _set_queue(self, task_queue):
        """
        Semi-private method when used in conjunction with a
        pulp.tasks.queue.TaskQueue instance for setting a back reference to the
        queue itself.
        """
        self.__queue = task_queue
        
    def __wrapper(self):
        """
        Private wrapper that executes the callable and captures and records any
        exceptions in a separate thread.
        """
        self.status = RUNNING
        self.start_time = datetime.now()
        try:
            self.callable(*self.args, **self.kwargs)
        except Exception, e:
            self.exception = e
            exec_info = sys.exc_info()
            self.traceback = traceback.format_exception(*exec_info)
            self.status = ERROR
        else:
            self.status = FINISHED
        self.finish_time = datetime.now()
        if self.__queue is not None:
            self.__queue._finished(self)        
        
    def run(self):
        """
        Run this task's callable in a separate thread.
        """
        self.__thread.run()