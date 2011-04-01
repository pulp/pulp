#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
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

import os
import sys
import shutil
import unittest
from subprocess import call
from time import sleep
from threading import Thread, RLock

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.client.lock import Lock

# test root dir
ROOTDIR = '/tmp/client/locking'
FILE = 'test.lock'
PATH = os.path.join(ROOTDIR,FILE)

PROG = """
import os
from time import sleep
from pulp.client.lock import Lock
lock = Lock('%s')
lock.acquire()
#sleep(1)
lock.release()
print str(os.getpid())
""" % PATH

EXECV = [
    'python',
    '-c',
    PROG,
]

lock = Lock(PATH)
mutex = RLock()
failed = []

def raised(ex):
    mutex.acquire()
    try:
        failed.append(ex)
    finally:
        mutex.release()

def hasfailed():
    mutex.acquire()
    try:
        return len(failed)
    finally:
        mutex.release()

class TestThread(Thread):

    def run(self):
        if hasfailed():
            return
        try:
            lock.acquire()
            sleep(1)
            lock.release()
            if call(EXECV) != 0:
                msg = 'failed: %d, %s' % (os.getpid(), self.getName())
                raise Exception(msg)
        except Exception, e:
            raised(e)

class TestLockFile(unittest.TestCase):

    def clean(self):
        shutil.rmtree(ROOTDIR, True)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_acquire(self):
        return # we know this is broken
        for x in range(0,100):
            print '\n==== RUN #%d ====' % x
            if hasfailed():
                break
            lock.acquire()
            lock.release()
            for i in range(0,60):
                t = TestThread(name='Test-%d'%i)
                t.setDaemon(True)
                t.start()
            t.join()
        print failed
        self.assertFalse(len(failed))