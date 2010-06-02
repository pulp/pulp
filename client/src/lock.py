#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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

import os
import re
import time
import fcntl
from threading import RLock as Mutex


class LockFile:

    def __init__(self, path):
        self.path = path
        self.pid = None
        self.fp = None

    def open(self):
        if self.notcreated():
            self.fp = open(self.path, 'w')
            self.setpid()
            self.close()
        self.fp = open(self.path, 'r+')
        fd = self.fp.fileno()
        fcntl.flock(fd, fcntl.LOCK_EX)

    def getpid(self):
        if self.pid is None:
            content = self.fp.read().strip()
            if content:
                self.pid = int(content)
        return self.pid

    def setpid(self):
        self.fp.seek(0)
        content = str(os.getpid())
        self.fp.write(content)
        self.fp.flush()

    def mypid(self):
        return ( os.getpid() == self.getpid() )

    def valid(self):
        status = False
        try:
            os.kill(self.getpid(), 0)
            status = True
        except Exception, e:
            pass
        return status

    def delete(self):
        if self.mypid() or not self.valid():
            self.close()
            os.unlink(self.path)

    def close(self):
        try:
            fd = self.fp.fileno()
            fcntl.flock(fd, fcntl.LOCK_UN)
            self.fp.close()
        except:
            pass
        self.pid = None
        self.fp = None

    def notcreated(self):
        return ( not os.path.exists(self.path) )

    def __del__(self):
        self.close()


class Lock:

    mutex = Mutex()

    def __init__(self, path):
        self.depth = 0
        self.path = path
        dir, fn = os.path.split(self.path)
        if not os.path.exists(dir):
            os.makedirs(dir)

    def acquire(self):
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
                    time.sleep(0.5)
                else:
                    break
            self.P()
            f.setpid()
        finally:
            f.close()

    def release(self):
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
        mutex = self.mutex
        mutex.acquire()
        try:
            return ( self.depth > 0 )
        finally:
            mutex.release()

    def P(self):
        mutex = self.mutex
        mutex.acquire()
        try:
            self.depth += 1
        finally:
            mutex.release()
        return self

    def V(self):
        mutex = self.mutex
        mutex.acquire()
        try:
            if self.acquired():
                self.depth -= 1
        finally:
            mutex.release()

    def __del__(self):
        try:
            self.release()
        except:
            pass
