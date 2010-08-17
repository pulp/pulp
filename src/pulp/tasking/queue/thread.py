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
import logging
import threading


_log = logging.getLogger(__name__)

# debugging re-entrant lock ---------------------------------------------------

class DRLock(object):
    """
    Re-entrant lock that logs when it is acquired and when it is released at the
    debug log level.
    """
    def __init__(self):
        self.__lock = threading.RLock()
        self._is_owned = self.__lock._is_owned
        #self._acquire_restore = self.__lock._acquire_restore
        #self._release_save = self.__lock._release_save

    def __repr__(self):
        return repr(self.__lock)

    def acquire(self, blocking=1):
        _log.debug('Thread %s called acquire' % threading.current_thread())
        if not self.__lock.acquire(blocking):
            return False
        _log.debug('Lock %s ACQUIRED' % repr(self))
        return True

    def release(self):
        _log.debug('Thread %s called release' % threading.current_thread())
        self.__lock.release()
        _log.debug('Lock %s RELEASED' % repr(self))

    __enter__ = acquire

    def __exit__(self, *args, **kwargs):
        self.release()

# interruptable thread base class ---------------------------------------------

# based on an answer from stack overflow:
# http://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread-in-python

def _raise_exception_in_thread(tid, exc_type):
    """
    Raises an exception in the threads with id tid.
    """
    assert inspect.isclass(exc_type)
    # NOTE this returns the number of threads that it modified, which should
    # only be 1 or 0 (if the thread id wasn't found)
    long_tid = ctypes.c_long(tid)
    exc_ptr = ctypes.py_object(exc_type)
    num = ctypes.pythonapi.PyThreadState_SetAsyncExc(long_tid, exc_ptr)
    if num == 1:
        return
    if num == 0:
        raise ValueError('Invalid thread id')
    # NOTE if it returns a number greater than one, you're in trouble, 
    # and you should call it again with exc=NULL to revert the effect
    null_ptr = ctypes.py_object()
    ctypes.pythonapi.PyThreadState_SetAsyncExc(long_tid, null_ptr)
    raise SystemError('PyThreadState_SetAsyncExc failed')


class InterruptableThread(threading.Thread):
    """
    A thread class that supports raising exception in the thread from another
    thread.
    """

    def __init__(self, *args, **kwargs):
        super(InterruptableThread, self).__init__(*args, **kwargs)
        self.__default_timeout = 0.05
        self.__exception_event = threading.Event()

    @property
    def _tid(self):
        """
        Determine this thread's id.
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

    def exception_event(self):
        """
        Flag that an exception has been delivered to the thread and handled.
        This will unblock the thread trying to deliver the exception.
        """
        self.__exception_event.set()

    def raise_exception(self, exc_type):
        """
        Raise and exception in this thread.
        
        NOTE this is executed in the context of the calling thread and blocks
        until the exception has been delivered to this thread and this thread
        exists.
        """
        while not self.__exception_event.is_set():
            try:
                _raise_exception_in_thread(self._tid, exc_type)
                self.__exception_event.wait(self.__default_timeout)
            except (threading.ThreadError, AssertionError,
                    ValueError, SystemError), e:
                _log.error('Failed to deliver exception %s to thread[%s]: %s' %
                           (exc_type.__name__, str(self.ident), e.message))
                break

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
    def timeout(self):
        """
        Raise a TimeoutException in the thread.
        """
        self.raise_exception(TimeoutException)

    def cancel(self):
        """
        Raise a CancelException in the thread.
        """
        self.raise_exception(CancelException)
