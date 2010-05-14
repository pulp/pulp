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

"""
User-space thread management with higher-level synchronization primitives.

This module provides Thread objects and corresponding synchronization for
threads that can be repeatedly executed and paused instead of the run-once
semantics of python's built-in threading module
"""

import functools
import thread
import time

# debugging -------------------------------------------------------------------

def _sync_debug(method):
    if not __debug__:
        return method
    @functools.wraps(method)
    def sync_debug_decorator(self, *args, **kwargs):
        thread_id = thread.get_ident()
        print 'Thread %d called *%s* on %s' % (thread_id, method.__name__, repr(self))
        return method(self, *args, **kwargs)
    return sync_debug_decorator

# exceptions ------------------------------------------------------------------

class LockError(thread.error):
    pass


class RLockError(LockError):
    pass


class ConditionError(LockError):
    pass

# locks -----------------------------------------------------------------------

class Lock(object):
    """
    Lock class
    Inheritance-friendly wrapper around thread.allocate_lock
    """
    def __init__(self, locked=False):
        self._owner = None
        self._lock = thread.allocate_lock()
        if locked:
            self.acquire()
            
    def __repr__(self):
        return '<Lock: %s>' % repr(self._lock)
    
    @property
    def owner(self):
        return self._owner
    
    @_sync_debug
    def acquire(self, wait=True):
        acquired = self._lock.acquire(int(wait))
        if acquired:
            self._owner = thread.get_ident()
        return acquired
    
    @_sync_debug
    def release(self):
        self._owner = None
        self._lock.release()
        
    def locked(self):
        return self._owner is not None
    
    
class RLock(Lock):
    """
    RLock class
    Reentrant lock class that allows a thread to "acquire" the lock an arbitrary
    number of times, in-so-long-as it releases the lock the same number of times
    """
    def __init__(self, locked=False):
        super(RLock, self).__init__(locked)
        self._count = 0
            
    def __repr__(self):
        return '<RLock: %s>' % repr(self._lock)
    
    @_sync_debug
    def acquire(self, wait=True):
        acquired = True
        if thread.get_ident() != self._owner:
            acquired = super(RLock, self).acquire(wait)
        if acquired:
            self._count += 1
        return acquired
    
    @_sync_debug
    def release(self):
        if thread.get_ident() != self._owner:
            raise RLockError('release called on un-acquired rlock')
        self._count -= 1
        if self._count == 0:
            super(RLock, self).release()
            
    @_sync_debug
    def reset(self):
        if thread.get_ident() != self._owner:
            raise RLockError('reset called on un-acquired rlock')
        self._count = 0
        super(RLock, self).release()
    
# other synchronization primitives --------------------------------------------
    
class Semaphore(Lock):
    """
    Unimplemented
    """
    def __init__(self, count=1):
        raise NotImplemented()
    
    def __repr__(self):
        pass
    
    @_sync_debug
    def acquire(self):
        pass
    
    @_sync_debug
    def release(self):
        pass
    
    
class Condition(object):
    """
    Condition class
    Synchronization primitive that allows threads to wait (read block) until
    either a timeout occurs or they are notified by another thread.
    """
    def __init__(self, lock=None):
        """
        @param lock: lock object to use, None will create a new lock
        """
        assert lock is None or isinstance(lock, Lock)
        
        self.__lock = lock or Lock()
        
        self.acquire = self.__lock.acquire
        self.release = self.__lock.release
        
        self.__initial_sleep = 0.0005
        self.__max_sleep = 0.05
        
        self.__wait_locks = []
            
    def __repr__(self):
        return '<Condition: %s>' % repr(self.__lock)
        
    def _is_owned(self):
        return self.__lock.owner == thread.get_ident()
    
    @_sync_debug
    def wait(self, timeout=None):
        """
        Wait on this condition
        @param timeout: wait timeout in seconds or None for no timeout
        """
        if not self._is_owned():
            raise ConditionError('wait called on un-acquired condition')
        
        lock = Lock(locked=True)
        self.__wait_locks.append(lock)
        self.__lock.release()
        
        try:
            if timeout is None:
                lock.acquire()
            
            else:
                # poll for notification or timeout using exponential back-off
                sleep_time = self.__initial_sleep
                wake = time.time() + timeout
                
                while True:
                    remaining_time = wake - time.time()
                    notified = lock.acquire(False)
                    
                    if remaining_time <= 0 or notified:
                        break
                    
                    sleep_time = min(sleep_time * 2,
                                     remaining_time,
                                     self.__max_sleep)
                    time.sleep(sleep_time)
            
        finally:
            self.__wait_locks.remove(lock)
            self.__lock.acquire()
            
    @_sync_debug
    def notify(self, n=1):
        """
        Notify the first "n" threads waiting this condition
        @param n: number of threads to notify
        """
        if not self._is_owned():
            raise ConditionError('notify called on un-acquired condition')
        
        for lock in self.__wait_locks[:n]:
            lock.release()
            
    def notify_all(self):
        """
        Notify all the threads waiting on this condition
        """
        self.notify(len(self.__wait_locks))
    
# threads ---------------------------------------------------------------------
    
class Thread(object):
    """
    Thread class
    Thread objects that will call the target with the passed in arguments in a
    separate thread whenever execute() is called.
    Because of the difference in semantics from other thread classes, the
    thread will only exit with exit() is explicitly called.
    """
    def __init__(self, target, args=[], kwargs={}):
        """
        @param target: target callable to call on execute
        @param args: positional arguments for target callable
        @param kwargs: key word arguments for target callable
        """
        self.__ident = None
        self.__exit = False
        self.__call = functools.partial(target, *args, **kwargs)
        self.__block = Lock()
        self.__join = Condition()
        thread.start_new_thread(self.__bootstrap, ())
        # allow the new thread to bootstrap to avoid a race condition between
        # between the thread's __bootstrap and another thread calling execute
        time.sleep(0.0005)
        
    def __repr__(self):
        return '<Thread: %s>' % str(self.__ident)
        
    def __bootstrap(self):
        # only called by new thread
        self.__ident = thread.get_ident()
        self.__thread_loop()
    
    def __thread_loop(self):
        # only called by new thread
        while True:
            self.__yield()
            if self.__exit:
                thread.exit()
            self.__call()
            
    def __yield(self):
        # only called by new thread
        self.__block.acquire()
        self.__block.acquire()
    
    def __continue(self):
        # only called by other threads (most likely the parent)
        if not self.__block.locked():
            return
        self.__block.release()
       
    @property
    def ident(self):
        return self.__ident
    
    @_sync_debug
    def execute(self):
        """
        Execute the target callable in a separate thread
        """
        self.__continue()
        
    @_sync_debug
    def exit(self):
        """
        Allow the separate thread to exit
        """
        self.__exit = True
        self.__continue()
        self.__join.acquire()
        self.__join.notify_all()
        self.__join.release()
        
    @_sync_debug
    def join(self, timeout=None):
        """
        Block until this thread's exit() is called
        """
        self.__join.acquire()
        self.__join.wait(timeout)