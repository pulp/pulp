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
[oxymoron]
"""

import functools
import thread
import time

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
    """
    def __init__(self, locked=False):
        self._lock = thread.allocate_lock()
        if locked:
            self._lock.acquire()
    
    def acquire(self, wait=True):
        return self._lock.acquire(int(wait))
    
    def release(self):
        self._lock.release()
        
    def locked(self):
        self._lock.locked()
    
    
class RLock(Lock):
    """
    """
    def __init__(self, locked=False):
        super(RLock, self).__init__(locked)
        self._thread_id = None
        self._count = 0
    
    def acquire(self, wait=True):
        thread_id = thread.get_ident()
        if thread_id != self._thread_id:
            if not wait:
                return False
            self._lock.acquire()
            self._thread_id = thread_id
        self._count += 1
        return True
    
    def release(self):
        if thread.get_ident() != self._thread_id:
            raise RLockError('release called on un-acquired lock')
        self._count -= 1
        if self._count == 0:
            self._thread_id = None
            self._lock.release()
            
    def reset(self):
        if thread.get_ident() != self._thread_id:
            raise RLockError('reset called on un-acquired lock')
        self._thread_id = None
        self._count = 0
        self._lock.release()
    
# other synchronization primitives --------------------------------------------
    
class Semaphore(Lock):
    """
    """
    def __init__(self, count=1):
        raise NotImplemented()
    
    def acquire(self):
        pass
    
    def release(self):
        pass
    
    
class Condition(object):
    """
    """
    def __init__(self, lock=None):
        self.__lock = lock or RLock()
        
        self.acquire = self.__lock.acquire
        self.release = self.__lock.release
        
        self.__initial_sleep = 0.0005
        self.__max_sleep = 0.05
        
        self.__wait_locks = []
        
    def _is_owned(self):
        if self.__lock.acquire(0):
            self.__lock.release()
            return False
        return True
    
    def wait(self, timeout=None):
        if not self._is_owned():
            raise ConditionError('cannot wait on an un-acquired lock')
        
        wait_lock = Lock()
        wait_lock.acquire()
        self.__wait_locks.append(wait_lock)
        self.__lock.release()
        
        try:
            if timeout is None:
                wait_lock.acquire()
                return
            
            # poll for notification using exponential back-off
            sleep_time = self.__initial_sleep
            wake_time = time.time() + timeout
            
            while True:
                remaining_time = wake_time - time.time()
                notified = wait_lock.acquire(False)
                if notified or remaining_time <= 0:
                    break
                sleep_time = min(sleep_time * 2, remaining_time, self.__max_sleep)
                time.sleep(sleep_time)
            
        finally:
            self.__wait_locks.remove(wait_lock)
            self.__lock.acquire()
            
    def notify(self, n=1):
        if not self._is_owned():
            raise ConditionError('cannot notify on an un-acquired lock')
        
        for lock in self.__wait_locks[:n]:
            lock.release()
            
    def notify_all(self):
        self.notify(len(self.__wait_locks))
    
# thread management -----------------------------------------------------------

class _ThreadManager(object):
    """
    """
    def __init__(self):
        self.__lock = RLock()
        self.__threads = {}
        
    def register(self, thread):
        self.__lock.acquire()
        lock = self.__threads.setdefault(thread, Lock(locked=True))
        self.__lock.release()
        lock.acquire()
    
    def unregister(self, thread):
        self.__lock.acquire()
        thread._exit()
        lock = self.__threads.pop(thread)
        lock.release()
        self.__lock.release()
    
    def run(self, thread):
        self.__lock.acquire()
        self.__threads(thread).release()
        self.__lock.release()
    
    def stop(self, thread):
        self.__lock.acquire()
        self.__threads[thread].acquire()
        self.__lock.release()
        self.__threads[thread].acquire()
    
_thread_manager = _ThreadManager()
    
# threads ---------------------------------------------------------------------
    
class Thread(object):
    """
    """
    def __init__(self, call, args=[], kwargs={}):
        self.__ident = None
        self.__exit = False
        self.__call = functools.partial(call, args, kwargs)
        self.__join = Condition(Lock())
        thread.start_new_thread(self.__boostrap, ())
        
    def __del__(self):
        _thread_manager.unregister(self)
        # XXX will have to pause here long enough for the thread to exit
    
    def __bootstrap(self):
        self.__ident = thread.get_ident()
        _thread_manager.register(self)
        self.__wrapper()
    
    def __wrapper(self):
        while True:
            if self.__exit:
                raise SystemExit()
            self.__call()
            _thread_manager.stop(self)
       
    def _exit(self):
        self.__exit = True
        self.__join.notify_all()
         
    @property
    def ident(self):
        return self.__ident
    
    def run(self):
        _thread_manager.run(self)
        
    def join(self, timeout=None):
        self.__join.wait(timeout)