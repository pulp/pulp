#
# Copyright (c) 2010 Red Hat, Inc.
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
#

"""
Contains locking classes.
"""

import os
import re
import time
import fcntl
from threading import RLock as Mutex


class LockFailed(Exception):
    pass


class LockFile:
    """
    File based locking.
    @ivar path: The absolute path to the lock file.
    @type path: str
    @ivar pid: current process id.
    @type pid: int
    @ivar fp: The I{file pointer} to the lock file.
    @ivar fp: I{file-like} pointer.
    """

    def __init__(self, path):
        """
        @param path: The absolute path to the lock file.
        @type path: str
        """
        self.path = path
        self.pid = None
        self.fp = None

    def open(self):
        """
        Open the lock file.
        Created in not exists.  Opened with file locking.
        """
        if self.notcreated():
            self.fp = open(self.path, 'w')
            self.setpid()
            self.close()
        self.fp = open(self.path, 'r+')
        fd = self.fp.fileno()
        fcntl.flock(fd, fcntl.LOCK_EX)

    def getpid(self):
        """
        Get the process id.
        @return: The pid in the lock file, else the current pid.
        @rtype: int
        """
        if self.pid is None:
            content = self.fp.read().strip()
            if content:
                self.pid = int(content)
        return self.pid

    def setpid(self, pid=os.getpid()):
        """
        Write our procecss id and flush.
        @param pid: The process ID.
        @type pid: int
        """
        self.fp.seek(0)
        content = str(pid)
        self.fp.write(content)
        self.fp.flush()

    def mypid(self):
        """
        Get the current process id.
        @return: This process id.
        @rtype: int
        """
        return ( os.getpid() == self.getpid() )

    def valid(self):
        """
        Get whether the pid in the file is valid.
        @return: True if valid.
        @rtype: bool
        """
        status = False
        try:
            os.kill(self.getpid(), 0)
            status = True
        except Exception, e:
            pass
        return status

    def delete(self):
        """
        Delete the lock file.
        """
        if self.mypid() or not self.valid():
            self.close()
            os.unlink(self.path)

    def close(self):
        """
        Close the file and release the file lock.
        Reset pid & fp to (None).
        """
        try:
            fd = self.fp.fileno()
            fcntl.flock(fd, fcntl.LOCK_UN)
            self.fp.close()
        except:
            pass
        self.pid = None
        self.fp = None

    def notcreated(self):
        """
        Get if file not created.
        @return: True if file not created.
        @rtype: bool
        """
        return ( not os.path.exists(self.path) )

    def __del__(self):
        """ cleanup """
        self.close()


class Lock:
    """
    File backed Reentrant lock.
    @cvar mutex: A thread mutex.
    @type mutex: L{Mutex}
    """

    mutex = Mutex()

    def __init__(self, path):
        self.depth = 0
        self.path = path
        dir, fn = os.path.split(self.path)
        if not os.path.exists(dir):
            os.makedirs(dir)

    def acquire(self, wait=True):
        """
        Acquire the lock.
        @param wait: Indicates call will block and wait for the lock.
        @type wait: boolean
        """
        f = LockFile(self.path)
        try:
            while True:
                f.open()
                pid = f.getpid()
                if f.mypid():
                    self.P()
                    return
                if f.valid():
                    f.close()
                    if wait:
                        time.sleep(0.5)
                    else:
                        raise LockFailed()
                else:
                    break
            self.P()
            f.setpid()
        finally:
            f.close()
            
    def update(self, pid):
        """
        Update the process ID.
        @param pid: The process ID.
        @type pid: int
        """
        if not self.acquired():
            raise Exception, 'not acquired'
        f = LockFile(self.path)
        try:
            f.open()
            f.setpid(pid)
        finally:
            f.close()

    def release(self):
        """
        Release the lock.
        """
        if not self.acquired():
            return
        self.V()
        if self.acquired():
            return
        f = LockFile(self.path)
        try:
            f.open()
            f.delete()
        finally:
            f.close()

    def acquired(self):
        """
        Test to see if acquired.
        @return: True if acquired.
        @rtype: bool
        """
        mutex = self.mutex
        mutex.acquire()
        try:
            return ( self.depth > 0 )
        finally:
            mutex.release()

    def P(self):
        """
        Do semiphore (P) operation.
        @return: self
        @rtype: L{Lock}
        """
        mutex = self.mutex
        mutex.acquire()
        try:
            self.depth += 1
        finally:
            mutex.release()
        return self

    def V(self):
        """
        Do semiphore (V) operation.
        @return: self
        @rtype: L{Lock}
        """
        mutex = self.mutex
        mutex.acquire()
        try:
            if self.acquired():
                self.depth -= 1
        finally:
            mutex.release()
        return self

    def __del__(self):
        try:
            self.release()
        except:
            pass
