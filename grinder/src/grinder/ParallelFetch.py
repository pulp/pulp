#!/usr/bin/env python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: John Matthews
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
import time
import logging
import threading
from threading import Thread
import Queue

from BaseFetch import BaseFetch

LOG = logging.getLogger("grinder.ParallelFetch")

class SyncReport:
    def __init__(self):
        self.successes = 0
        self.downloads = 0
        self.errors = 0
    def __str__(self):
        return "%s successes, %s downloads, %s errors" % (self.successes, self.downloads, self.errors)

class ParallelFetch(object):
    def __init__(self, fetcher, numThreads=3):
        self.toSyncQ = Queue.Queue()
        self.syncCompleteQ = Queue.Queue()
        self.syncErrorQ = Queue.Queue()
        self.threads = []
        self.numThreads = numThreads
        self.fetcher = fetcher
        for i in range(self.numThreads):
            wt = WorkerThread(self.toSyncQ, self.syncCompleteQ, self.syncErrorQ, fetcher)
            self.threads.append(wt)

    def addItem(self, item):
        self.toSyncQ.put(item)

    def addItemList(self, items):
        for p in items:
            self.toSyncQ.put(p)

    def start(self):
        for t in self.threads:
            t.start()

    def stop(self):
        for t in self.threads:
            t.stop()

    def _running(self):
        working = 0
        for t in self.threads:
            if (t.isAlive()):
                working += 1
        return (working > 0)

    def _waitForThreads(self):
        while (self._running()):
            LOG.debug("Wait 1.  check again")
            time.sleep(0.5)

    def waitForFinish(self):
        """
        Will wait for all worker threads to finish
        Returns (successList, errorList)
         successList is a list of all items successfully synced
         errorList is a list of all items which couldn't be synced
        """
        self._waitForThreads()

        LOG.info("All threads have finished.")
        successList = []
        while not self.syncCompleteQ.empty():
            p = self.syncCompleteQ.get_nowait()
            successList.append(p)
        errorList = []
        while not self.syncErrorQ.empty():
            p = self.syncErrorQ.get_nowait()
            errorList.append(p)
        report = SyncReport()
        for t in self.threads:
            report.successes = report.successes + t.syncStatusDict[BaseFetch.STATUS_DOWNLOADED]
            report.successes = report.successes + t.syncStatusDict[BaseFetch.STATUS_NOOP]
            report.downloads = report.downloads + t.syncStatusDict[BaseFetch.STATUS_DOWNLOADED]
            report.errors = report.errors + t.syncStatusDict[BaseFetch.STATUS_ERROR]
            report.errors = report.errors + t.syncStatusDict[BaseFetch.STATUS_MD5_MISSMATCH]
            report.errors = report.errors + t.syncStatusDict[BaseFetch.STATUS_SIZE_MISSMATCH]

        LOG.info("ParallelFetch: %s items successfully processed, %s downloaded, %s items had errors" %
            (report.successes, report.downloads, report.errors))

        return report


class WorkerThread(Thread):

    def __init__(self, toSyncQ, syncCompleteQ, syncErrorQ, fetcher):
        Thread.__init__(self)
        self.toSyncQ = toSyncQ
        self.syncCompleteQ = syncCompleteQ
        self.syncErrorQ = syncErrorQ
        self.fetcher = fetcher
        self.syncStatusDict = dict()
        self.syncStatusDict[BaseFetch.STATUS_NOOP] = 0
        self.syncStatusDict[BaseFetch.STATUS_DOWNLOADED] = 0
        self.syncStatusDict[BaseFetch.STATUS_SIZE_MISSMATCH] = 0
        self.syncStatusDict[BaseFetch.STATUS_MD5_MISSMATCH] = 0
        self.syncStatusDict[BaseFetch.STATUS_ERROR] = 0
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        LOG.debug("Run has started")
        while not self.toSyncQ.empty() and not self._stop.isSet():
            LOG.info("%s items left on Queue" % (self.toSyncQ.qsize()))
            try:
                itemInfo = self.toSyncQ.get_nowait()
                status = self.fetcher.fetchItem(itemInfo)
                if status in self.syncStatusDict:
                    self.syncStatusDict[status] = self.syncStatusDict[status] + 1
                else:
                    self.syncStatusDict[status] = 1
                if status != BaseFetch.STATUS_ERROR:
                    self.syncCompleteQ.put(itemInfo)
                else:
                    self.syncErrorQ.put(itemInfo)
            except Queue.Empty:
                LOG.debug("Queue is empty, thread will end")
        LOG.debug("Thread ending")



if __name__ == "__main__":
    # This a very basic test just to feel out the flow of the threads 
    # pulling items from a shared Queue and exiting cleanly
    # Create a simple fetcher that sleeps every few items
    class SimpleFetcher(object):
        def fetchItem(self, x):
            print "Working on item %s" % (x)
            if x % 3 == 0:
                print "Sleeping 1 second"
                time.sleep(1)
            return BaseFetch.STATUS_NOOP

    pf = ParallelFetch(SimpleFetcher(), 3)
    numPkgs = 20
    pkgs = range(0, numPkgs)
    pf.addItemList(pkgs)
    pf.start()
    report = pf.waitForFinish()
    print "Success: ", report.successes
    print "Error: ", report.errors
    assert(report.successes == numPkgs)

