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
import time
import weakref

# globals ---------------------------------------------------------------------

# threading classes, tracked here for monkey-patching
_Thread = threading.Thread
_DummyThread = threading._DummyThread

# tracked thread descendant tree
_thread_tree = weakref.WeakKeyDictionary()

_log = logging.getLogger('pulp')

# debugging re-entrant lock ---------------------------------------------------

class DRLock(object):
    """
    Re-entrant lock that logs when it is acquired and when it is released at the
    debug log level.
    """
    def __init__(self):
        self.__lock = threading.RLock()
        # inherit some of the lock's api methods
        self._is_owned = self.__lock._is_owned
        self._acquire_restore = self.__lock._acquire_restore
        self._release_save = self.__lock._release_save

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

    # magic methods used with 'with' block

    __enter__ = acquire

    def __exit__(self, *args, **kwargs):
        self.release()

# descendant thread tracking api ----------------------------------------------

class TrackedThread(_Thread):
    """
    Derived thread class that records the thread hierarchy (ie the parent and
    the child threads) whenever this thread is started.
    """
    def start(self):
        """
        Start execution in a separate thread of control.
        """
        parent = threading.current_thread()
        _thread_tree.setdefault(parent, []).append(weakref.ref(self))
        return super(TrackedThread, self).start()


class _DummyTrackedThread(TrackedThread, _DummyThread):
    """
    Derived dummy thread class that records the thread hierarchy whenever this
    thread is started.
    """
    def __init__(self):
        _DummyThread.__init__(self)


# monkey-patch the threading module in order to track threads
# this allows us to cancel tasks that have spawned threads of their own
threading.Thread = TrackedThread
threading._DummyThread = _DummyTrackedThread


def get_descendants(thread):
    """
    Get a list of all the descendant threads for the given thread.
    @type thread: L{TrackedThread} instance
    @param thread: thread to find the descendants of
    @raise RuntimeError: if the thread is not an instance of TrackedThread
    @return: list of TrackedThread instances
    """
    if not isinstance(thread, TrackedThread):
        raise RuntimeError('Cannot find descendants of an untracked thread')
    descendants = _thread_tree.get(thread, [])
    for d in descendants:
        t = d()
        if t is None:
            continue
        descendants.extend(_thread_tree.get(t, []))
    return filter(lambda d: d is not None, [d() for d in descendants])

# thread interruption api -----------------------------------------------------

# based on an answer from stack overflow:
# http://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread-in-python

class _ThreadInterruptionError(Exception):
    """
    Exception class used to flag and catch exceptions thrown by this api.
    """
    pass


def _tid(thread):
    """
    Determine a thread's id.
    """
    if not thread.is_alive():
        raise _ThreadInterruptionError('Thread is not active')
    if hasattr(thread, '_thread_id'):
        return thread._thread_id
    for tid, tobj in threading._active.items():
        if tobj is thread:
            thread._thread_id = tid
            return tid
    raise _ThreadInterruptionError('Could not determine thread id')


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
        raise _ThreadInterruptionError('Invalid thread id')
    # NOTE if it returns a number greater than one, we're in trouble, and
    # should call it again with exc=NULL to revert the effect
    null_ptr = ctypes.py_object()
    ctypes.pythonapi.PyThreadState_SetAsyncExc(long_tid, null_ptr)
    raise _ThreadInterruptionError('PyThreadState_SetAsyncExc failed')

# task exceptions -------------------------------------------------------------

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

# task thread -----------------------------------------------------------------

class TaskThread(TrackedThread):
    """
    Derived task thread class that allows for task-specific interruptions.
    """
    def __init__(self, *args, **kwargs):
        super(TaskThread, self).__init__(*args, **kwargs)
        self.__default_timeout = 0.05
        self.__exception_event = threading.Event()

    # interrupt-able thread methods

    def exception_delivered(self):
        """
        Flag that an exception has been delivered to the thread and handled.
        This needs to be called by the task thread and will unblock the thread
        trying to deliver the exception.
        """
        _log.debug('Exception event deliverd to thread[%s]' % str(self.ident))
        self.__exception_event.set()

    def raise_exception(self, exc_type):
        """
        Raise an exception in this thread.
        
        NOTE this is executed in the context of the calling thread and blocks
        until the exception has been delivered to this thread and this thread
        exits.
        """
        # embedded methods to reduce code duplication
        def test_exception_event():
            return not self.__exception_event.is_set()

        def deliver_exception(thread, test, wait):
            _log.debug('Trying to deliver exception %s to thread[%s]' %
                       (exc_type.__name__, str(thread.ident)))
            while test():
                try:
                    _raise_exception_in_thread(_tid(thread), exc_type)
                    wait(self.__default_timeout)
                except _ThreadInterruptionError, e:
                    _log.error('Failed to deliver exception %s to thread[%s]: %s' %
                               (exc_type.__name__, str(thread.ident), e.message))
                    return
            _log.debug('Succeeded in delivering exception %s to thread[%s]' %
                       (exc_type.__name__, str(thread.ident)))

        # first, kill off all the descendants
        for thread in get_descendants(self):
            deliver_exception(thread, thread.is_alive, time.sleep)
        # then kill and wait for the task thread
        deliver_exception(self, test_exception_event, self.__exception_event.wait)

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
