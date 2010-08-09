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

import ctypes
import inspect
import threading
import time

# interruptable thread base class ---------------------------------------------

# based on an answer from stack overflow:
# http://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread-in-python

def _raise_exception_in_thread(tid, exctype):
    """
    Raises an exception in the threads with id tid.
    """
    if not inspect.isclass(exctype):
        raise TypeError('Only types can be raised (not instances)')
    # NOTE this returns the number of threads that it modified, which should
    # only be 1 or 0 (if the thread id wasn't found)
    excptr = ctypes.py_object(exctype)
    num = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, excptr)
    if num == 1:
        return
    if num == 0:
        raise ValueError('Invalid thread id')
    # NOTE if it returns a number greater than one, you're in trouble, 
    # and you should call it again with exc=NULL to revert the effect
    nullptr = ctypes.py_object()
    ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, nullptr)
    raise SystemError('PyThreadState_SetAsyncExc failed')
    
    
class InterruptableThread(threading.Thread):
    """
    A thread class that supports raising exception in the thread from another
    thread.
    """
    
    @property
    def _tid(self):
        """
        Determine this thread's id.

        CAREFUL : method is executed in the context of the caller thread,
        to get the identity of the thread represented by this instance.
        """
        if not self.is_alive():
            raise threading.ThreadError('Thread is not active')

        # do we have it cached?
        if hasattr(self, '_thread_id'):
            return self._thread_id

        # no, look for it in the _active dict
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid

        raise AssertionError('Could not determine thread id')


    def raise_exception(self, exctype):
        """
        Raises the given exception type in the context of this thread.

        If the thread is busy in a system call
        (time.sleep(), socket.accept(), ...) the exception is simply ignored.

        If you are sure that your exception should terminate the thread, one way
        to ensure that it works is:
        t = InterruptableThread(...)
        ...
        t.raise_exception(SomeException)
        while t.isAlive():
            time.sleep(0.1)
            t.raise_exception(SomeException)

        If the exception is to be caught by the thread, you need a way to check
        that your thread has caught it.

        CAREFUL : this method is executed in the context of the caller thread,
        to raise an exception in the context of the thread represented by this
        instance.
        """
        _raise_exception_in_thread(self._tid, exctype)

# task thread -----------------------------------------------------------------

class TaskThreadException(Exception):
    """
    Base class for task-specific exceptions to be raised in a task thread.
    """
    pass


class TimeoutException(TaskThreadException):
    """
    Exception to interrupt a task with a time out.
    """
    pass


class CancelException(TaskThreadException):
    """
    Exception to interrupt a task with a cancellation.
    """
    pass


class TaskThread(InterruptableThread):
    """
    Derived task thread class that allows for task-specific interruptions.
    """
    _default_sleep = 0.0005
    
    def _ensure_exception(self, exctype):
        """
        Ensure that the exception gets raised in the thread or that the thread
        is already dead.
        @type exctype: type or class
        @param exctype: type or class of exception to raise in the tread
        """
        try:
            while self.is_alive():
                self.raise_exception(exctype)
                time.sleep(self._default_sleep)
        except threading.ThreadError:
            # a threading.ThreadError gets raised if the thread is already dead
            pass
    
    def timeout(self):
        """
        Raise a TimeoutException in the thread.
        """
        self._ensure_exception(TimeoutException)
            
    def cancel(self):
        """
        Raise a CancelException in the thread.
        """
        self._ensure_exception(CancelException)
        