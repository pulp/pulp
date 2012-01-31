#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import sys
import shutil
from time import sleep
from random import random
from threading import Thread

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.client.lib.lock import Lock

# test root dir
ROOTDIR = '/tmp/client/locking'
LOCKFILE = 'test.lock'
PATH = os.path.join(ROOTDIR,LOCKFILE)

lock = Lock(PATH)

pids = []

def child(pid):
    print '%d START' % pid
    for i in range(0,5):
      lock.acquire()
      print '\n%d ACQUIRED' % pid
      sleep(random())
      lock.release()
      print '%d RELEASED' % pid
    print '%d END' % pid


class TestThread(Thread):
    
    def __init__(self, name):
        Thread.__init__(self, name=name)
        self.setDaemon(True)

    def run(self):
        lock.acquire()
        print '\n(%d/%s) ACQUIRED' % \
            (os.getpid(), self.getName())
        sleep(random())
        lock.release()
        print '(%d/%s) RELEASED' % \
            (os.getpid(), self.getName())

class TestLock(testutil.PulpAsyncTest):

    def clean(self):
        shutil.rmtree(ROOTDIR, True)

    def spawn(self):
        pid = os.fork()
        if pid == 0:
            child(os.getpid())
            sys.exit(0)
        else:
            pids.append(pid)
    
    def test_basic(self):
        
        return # DISABLE FOR NOW
        
        for x in range(0,5):
            pid = self.spawn()
        lock.acquire()
        print '\n[TEST] ACQUIRED'
        sleep(random())
        lock.release()
        print '[TEST] RELEASED'
        for i in range(0,5):
            t = TestThread(name='Test-%d'%i)
            t.setDaemon(True)
            t.start()
        t.join()
        print 'Waiting on children'
        for pid in pids:
            status = os.waitpid(pid, 0)
            print 'pid=%d, status=%d' % status
            if status[1] != 0:
                raise Exception('child failed')
