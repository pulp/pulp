#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

"""
Contains locking classes.
"""

import os
import re
import fcntl
from threading import RLock


class LockFailed(Exception):
    pass

class NotLocked(Exception):
    pass


class LockFile:
    """
    File based locking.
    @ivar path: The absolute path to the lock file.
    @type path: str
    @ivar __fp: The I{file pointer} to the lock file.
    @ivar __fp: I{file-like} pointer.
    """

    def __init__(self, path):
        """
        @param path: The absolute path to the lock file.
        @type path: str
        """
        self.path = path
        self.__fp = None
        self.__mkdir(path)

    def acquire(self, blocking=True):
        """
        Acquire the lockfile.
        @param blocking: Wait for the lock.
        @type blocking: bool
        @return: self
        @rtype: L{LockFile}
        """
        fp = open(self.path, 'w')
        if not blocking:
            try:
                fcntl.flock(fp.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
            except IOError:
                fp.close()
                raise LockFailed(self.path)
        else:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
        self.__fp = fp
        self.setpid()
        return self

    def release(self):
        """
        Release the lockfile.
        """
        try:
            if self.__fp.closed:
                return
            fd = self.__fp.fileno()
            self.__fp.close()
        except:
            pass

    def getpid(self):
        """
        Get the process id.
        @return: The pid in the lock file, else the current pid.
        @rtype: int
        """
        pid = 0
        fp = open(self.path)
        content = fp.read()
        if content:
            pid = int(content)
        return pid

    def setpid(self, pid=os.getpid()):
        """
        Write our procecss id and flush.
        @param pid: The process ID.
        @type pid: int
        """
        self.__fp.seek(0)
        self.__fp.write(str(pid))
        self.__fp.flush()

    def __mkdir(self, path):
        dir = os.path.dirname(path)
        if not os.path.exists(dir):
            os.makedirs(dir)


class Lock:
    """
    File backed Reentrant lock.
    """

    def __init__(self, path):
        self.__depth = 0
        self.__mutex = RLock()
        self.__lockf = LockFile(path)

    def acquire(self, blocking=1):
        """
        Acquire the lock.
        Acquire the mutex; acquire the lockfile.
        @param blocking: Wait for the lock.
        @type blocking: bool
        @return: self
        @rtype: L{Lock}
        """
        self.__lock(blocking)
        if self.__push() == 1:
            try:
                self.__lockf.acquire(blocking)
            except:
                self.__pop()
                raise
        return self

    def release(self):
        """
        Release the lock.
        Release the lockfile; release the mutex.
        """
        if self.__pop() == 0:
            self.__lockf.release()
        self.__unlock()
        return self

    def setpid(self, pid):
        """
        Write our procecss id and flush.
        @param pid: The process ID.
        @type pid: int
        """
        self.__lock()
        try:
            self.__lockf.setpid(pid)
        finally:
            self.__unlock()

    def __push(self):
        """
        Increment the lock depth.
        @return: The incremented depth
        @rtype: int
        """
        self.__lock()
        try:
            self.__depth += 1
            return self.__depth
        finally:
            self.__unlock()

    def __pop(self):
        """
        Decrement the lock depth.
        @return: The decremented depth
        @rtype: int
        """
        self.__lock()
        try:
            if self.__depth > 0:
                self.__depth -= 1
            return self.__depth
        finally:
            self.__unlock()

    def __lock(self, blocking=1):
        if not self.__mutex.acquire(blocking):
            raise LockFailed()

    def __unlock(self):
        self.__mutex.release()
