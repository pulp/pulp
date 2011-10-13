#!/usr/bin/env python
import os
import shlex
import subprocess
import sys
import time

from datetime import datetime
from grinder.RepoFetch import YumRepoGrinder
from threading import Thread

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../utils")
from memory_usage import MemoryUsage

PKGS_DIR="./packages"
MAX_SYNC_JOBS=2
THREADS=15
REPO_DIR="./repos"
VERIFY_OPTIONS = {"size":False, "checksum":False}
TIME_FMT_STR = "%b%d_%Y__%l:%M%p"
LOG = open("%s.%s.output" % (time.strftime(TIME_FMT_STR), os.path.basename(__file__)), "w")

def log(msg):
    print msg
    LOG.write("%s\n" % (msg))
    LOG.flush()


def parse_feed_urls(file_name):
    feed_urls = []
    f = open(file_name, "r")
    raw_lines = f.readlines()
    for line in raw_lines:
        pieces = line.strip().split(",")
        feed = {}
        feed["id"] = pieces[0].strip()
        feed["url"] = pieces[1].strip()
        feed["feed_ca"] = pieces[2].strip()
        feed["feed_cert"] = pieces[3].strip()
        feed_urls.append(feed)
    return feed_urls


class SyncThread(Thread):
    def __init__(self, repo_id, url, ca, cert):
        Thread.__init__(self)
        self.repo_id = repo_id
        self.url = url
        self.ca = ca
        self.cert = cert
        self.finished = False
        self.report = None 

    def sync(self, repo_id, url, ca, cert):
        start = time.time()
        yum_repo_grinder = YumRepoGrinder(repo_id, url, THREADS,
            cacert=ca, clicert=cert, packages_location=PKGS_DIR)
        self.report = yum_repo_grinder.fetchYumRepo(
            "%s/%s" % (REPO_DIR, repo_id),
            verify_options=VERIFY_OPTIONS)
        end = time.time()

    def run(self):
        try:
            self.sync(self.repo_id, self.url, self.ca, self.cert)
        except Exception, e:
            log("\n\n\n%s Caught Exception: %s\n\n\n" % (self.repo_id, e))
        self.finished = True


def wait_till_one_free(threads):
    # Worried about modifying a list we are iterating over, so copying to new list
    ret_val = list(threads)
    while True:
        time.sleep(1)
        for t in threads:
            if t.finished:
                ret_val.remove(t)
                return ret_val

def wait_for_all_complete(threads):
    loop_again = True
    while loop_again:
        loop_again = False
        time.sleep(1)
        for t in threads:
            if t.finished:
                continue
            loop_again = True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: %s FEED_URLS_FILE_LIST" % (sys.argv[0])
        sys.exit(1)
    feed_urls = parse_feed_urls(sys.argv[1])
    log("%s Feed URLs found, may run up to %s YumRepoGrinder jobs at a time" % (len(feed_urls), MAX_SYNC_JOBS))

    memUsage = MemoryUsage()
    count = 0
    time_mem_stamp = memUsage.get_time_memory_stamp()
    log("Initial  %s" % (time_mem_stamp))
    while True:
        if MAX_SYNC_JOBS == 1:
            for index, repo in enumerate(feed_urls):
                t = SyncThread(repo["id"], repo["url"], repo["feed_ca"], repo["feed_cert"])
                t.start()
                while not t.finished:
                    time.sleep(2)
                report = "%s" % (t.report)
                del t
                time_mem_stamp = memUsage.get_time_memory_stamp()
                log("<%s> %s iteration  [%s] %s, %s" % (time_mem_stamp, count, report, repo["id"], repo["url"]))
            log("<%s> Completed iteration: %s\n" % (memUsage.get_time_memory_stamp(), count))
        else:
            threads = []
            for index, repo in enumerate(feed_urls):
                if len(threads) >= MAX_SYNC_JOBS:
                    threads = wait_till_one_free(threads)
                t = SyncThread(repo["id"], repo["url"], repo["feed_ca"], repo["feed_cert"])
                t.start()
                threads.append(t)
            wait_for_all_complete(threads)
            del threads
            threads = None
            time_mem_stamp = memUsage.get_time_memory_stamp()
            log("%s %s iteration" % (time_mem_stamp, count))
        count = count + 1


