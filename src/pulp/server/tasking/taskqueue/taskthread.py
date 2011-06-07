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

import ctypes
import inspect
import logging
import threading
import time
import weakref

from pulp.server.tasking.exception import (
    TimeoutException, CancelException, TaskThreadStateError,
    TaskThreadInterruptionError)

# globals ---------------------------------------------------------------------

# threading classes, tracked here for monkey-patching
_Thread = threading.Thread
_DummyThread = threading._DummyThread

# tracked thread descendant tree
_thread_tree = weakref.WeakKeyDictionary()

_log = logging.getLogger('pulp')

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
        parent = threading.currentThread()
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

def _tid(thread):
    """
    Checks if the given thread is available to be cancelled. There are three possible outcomes
    to this call:

    1. If the thread reports it is not alive, it has finished executing and there is no further
       action that needs to take place. In this case, None is returned.
    2. If the thread is capable of being cancelled, its thread ID is returned.
    3. If the thread object that was passed into the call exists however the underlying kernel
       thread has not yet been started, the thread cannot be cancelled at this time.
    """
    if not thread.isAlive():
        return None

    if hasattr(thread, '_thread_id'):
        return thread._thread_id
    for tid, tobj in threading._active.items():
        if tobj is thread:
            thread._thread_id = tid
            return tid

    raise TaskThreadStateError()


def _raise_exception_in_thread(tid, exc_type):
    """
    Raises an exception in the threads with id tid.
    """
    assert inspect.isclass(exc_type)
    # NOTE this returns the number of threads that it modified, which should
    # only be 1 or 0 (if the thread has already exited)
    long_tid = ctypes.c_long(tid)
    exc_ptr = ctypes.py_object(exc_type)
    num = ctypes.pythonapi.PyThreadState_SetAsyncExc(long_tid, exc_ptr)
    # if num == 0, it's not an error condition as the net effect is the same,
    # the thread has ended
    if num in (0, 1):
        return
    # NOTE if it returns a number greater than one, we're in trouble, and
    # should call it again with exc=NULL to revert the effect
    null_ptr = ctypes.py_object()
    ctypes.pythonapi.PyThreadState_SetAsyncExc(long_tid, null_ptr)
    raise TaskThreadInterruptionError('PyThreadState_SetAsyncExc failed')

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
        _log.debug('Exception event deliverd to thread[%s]' % str(_tid(self)))
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
            return self.isAlive() and not self.__exception_event.isSet()

        def deliver_exception(thread, test, wait):
            _log.debug('Trying to deliver exception %s to thread[%s]' %
                       (exc_type.__name__, str(_tid(thread))))
            while test():
                try:
                    _raise_exception_in_thread(_tid(thread), exc_type)
                    wait(self.__default_timeout)
                except TaskThreadInterruptionError, e:
                    # _TaskInterruptionError gets thrown if the exception was
                    # delivered to more than 1 thread at a time
                    _log.error('Failed to deliver exception %s to thread[%s]: %s' %
                               (exc_type.__name__, str(_tid(thread)), e.message))
                    return
            _log.debug('Succeeded in delivering exception %s to thread[%s]' %
                       (exc_type.__name__, str(_tid(thread))))

        # first, kill off all the descendants
        for thread in get_descendants(self):
            deliver_exception(thread, thread.isAlive, time.sleep)
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
