#!/usr/bin/env python

import os
import shlex
import subprocess
import sys
import time

from grinder.GrinderCallback import ProgressReport
from grinder.ParallelFetch import ParallelFetch
from grinder.RepoFetch import RepoFetch, YumRepoGrinder

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../utils")
from memory_usage import MemoryUsage

TIME_FMT_STR = "%b%d_%Y__%l:%M%p"
LOG = open("%s.metadata_parse.output" % (time.strftime(TIME_FMT_STR)), "w")


def log(msg):
    print msg
    LOG.write("%s\n" % (msg))
    LOG.flush()

class YumRepoGrinderModified(YumRepoGrinder):

    def fetchYumRepo(self, basepath="./", callback=None, verify_options=None):
        startTime = time.time()
        self.yumFetch = RepoFetch(self.repo_label, repourl=self.repo_url, \
                            cacert=self.sslcacert, clicert=self.sslclientcert, \
                            clikey=self.sslclientkey, mirrorlist=self.mirrors, \
                            download_dir=basepath, proxy_url=self.proxy_url, \
                            proxy_port=self.proxy_port, proxy_user=self.proxy_user, \
                            proxy_pass=self.proxy_pass, sslverify=self.sslverify,
                            max_speed=self.max_speed,
                            verify_options=verify_options)
        self.fetchPkgs = ParallelFetch(self.yumFetch, self.numThreads, callback=callback)
        try:
            if not verify_options:
                verify_options = {"size":False, "checksum":False}
            self.yumFetch.setupRepo()
            # first fetch the metadata
            self.fetchPkgs.processCallback(ProgressReport.DownloadMetadata)
            self.yumFetch.getRepoData()
            if self.stopped:
                return None
            if not self.skip.has_key('packages') or self.skip['packages'] != 1:
                # get rpms to fetch
                self.prepareRPMS()
                # get drpms to fetch
                self.prepareDRPMS()
            else:
                log("Skipping packages preparation from sync process")
            if not self.skip.has_key('distribution') or self.skip['distribution'] != 1:
                # get Trees to fetch
                self.prepareTrees()
            else:
                log("Skipping distribution preparation from sync process")
            # prepare for download
            self.fetchPkgs.addItemList(self.downloadinfo)
            self.fetchPkgs.start()
            report = self.fetchPkgs.waitForFinish()
            self.yumFetch.finalizeMetadata()
            endTime = time.time()
            #log("Processed <%s> items in [%d] seconds" % (len(self.downloadinfo), \
            #      (endTime - startTime)))
            if not self.skip.has_key('packages') or self.skip['packages'] != 1:
                if self.purge_orphaned:
                    #log("Cleaning any orphaned packages..")
                    self.fetchPkgs.processCallback(ProgressReport.PurgeOrphanedPackages)
                    self.purgeOrphanPackages(self.yumFetch.getPackageList(), self.yumFetch.repo_dir)
                if self.remove_old:
                    log("Removing old packages to limit to %s" % self.numOldPackages)
                    self.fetchPkgs.processCallback(ProgressReport.RemoveOldPackages)
                    gutils = GrinderUtils()
                    gutils.runRemoveOldPackages(self.pkgsavepath, self.numOldPackages)
            self.yumFetch.deleteBaseCacheDir()
            #log("Processed <%s> in %s seconds" % (report, endTime - startTime))
            return report, (endTime - startTime)
        finally:
            self.fetchPkgs.stop()
            self.yumFetch.closeRepo()


def parse_metadata(label, url, download_dir, cacert=None, clientcert=None):
    yumFetch = None
    try:
        yumFetch = RepoFetch(label, repourl=url, \
        cacert=cacert, clicert=clientcert, \
        download_dir=download_dir)
        yumFetch.setupRepo()
        yumFetch.getRepoData()
        pkglist = yumFetch.getPackageList()
        return len(pkglist)
    finally:
        # Note, if we don't execute closeRepo() then we will leak memory.
        # running with closeRepo() and I am not seeing any memory leaked
        yumFetch.closeRepo()
        del yumFetch

def test_simple_repo(url=None, label=None, download_dir=None):
    memUsage = MemoryUsage()
    print "Initial %s" % (memUsage.get_time_memory_stamp())
    if not url:
        #url = "http://repos.fedorapeople.org/repos/pulp/pulp/fedora-15/x86_64/"
        url = "http://jmatthews.fedorapeople.org/repo_500/"
    if not label:
        label = "pulp_f15_x86_64"
    if not download_dir:
        download_dir = "./data/%s" % (label)
    log("Fetching metadata for: %s" % (url))
    count = 0
    while True:
        yum_repo_grinder = YumRepoGrinderModified(label, url)
        report, time_delta = yum_repo_grinder.fetchYumRepo(basepath=download_dir)
        count = count + 1
        log("Iteration: %s, %s, [%s] in %d seconds" % (count, memUsage.get_time_memory_stamp(), report, time_delta))
        LOG.flush()

def test_protected_repo(url=None, label=None, download_dir=None, clientcert=None, cacert=None):
    memUsage = MemoryUsage()
    print "Initial %s" % (memUsage.get_time_memory_stamp())
    if not url:
        url = "https://cdn.redhat.com/content/dist/rhel/rhui/server/6/6Server/i386/os"
    if not label:
        label = "rhel-server-6-6Server-i386"
    if not download_dir:
        download_dir = "./data/%s" % (label)
    if not cacert:
        cacert = "/etc/pki/content/rhel-server-6-6Server-i386/feed-rhel-server-6-6Server-i386.ca"
    if not clientcert:
        clientcert = "/etc/pki/content/rhel-server-6-6Server-i386/feed-rhel-server-6-6Server-i386.cert"
    log("Fetching protected metadata for: %s" % (url))
    count = 0
    while True:
        yum_repo_grinder = YumRepoGrinderModified(label, url, cacert=cacert, clicert=clientcert)
        report, time_delta = yum_repo_grinder.fetchYumRepo(basepath=download_dir)
        log("Iteration: %s, %s, [%s] in %d seconds" % (count, memUsage.get_time_memory_stamp(), report, time_delta))
        LOG.flush()
        count = count + 1

if __name__ == "__main__":
    test_simple_repo()
    #test_protected_repo()
