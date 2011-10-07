#!/usr/bin/env python
import os
import shlex
import subprocess
import sys
import time

from datetime import datetime
from grinder.RepoFetch import YumRepoGrinder
from threading import Thread

PKGS_DIR="./packages"
MAX_SYNC_JOBS=4
THREADS=15
REPO_DIR="./repos"
VERIFY_OPTIONS = {"size":False, "checksum":False}
TIME_FMT_STR = "%b%d_%Y__%l:%M%p"

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

    def sync(self, repo_id, url, ca, cert):
        #print "%s sync(%s, %s)" % (datetime.now(), repo_id, url)
        start = time.time()
        yum_repo_grinder = YumRepoGrinder(repo_id, url, THREADS,
            cacert=ca, clicert=cert, packages_location=PKGS_DIR)
        report = yum_repo_grinder.fetchYumRepo(
            "%s/%s" % (REPO_DIR, repo_id),
            verify_options=VERIFY_OPTIONS)
        end = time.time()
        #print ("<%s> reported %s successes, %s downloads, %s errors" \
        #            % (repo_id, report.successes, report.downloads, report.errors))
        #print "<%s> took %s seconds" % (repo_id, end-start)

    def run(self):
        try:
            self.sync(self.repo_id, self.url, self.ca, self.cert)
        except Exception, e:
            print "\n\n\n%s Caught Exception: %s\n\n\n" % (self.repo_id, e)
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

def get_memory_usage():
    pid = os.getpid()
    cmd = "pmap -d %s" % (pid)
    cmd = shlex.split(cmd)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    mem_usage =  out.splitlines()[-1]
    return mem_usage

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: %s FEED_URLS_FILE_LIST" % (sys.argv[0])
        sys.exit(1)
    feed_urls = parse_feed_urls(sys.argv[1])
    print "%s Feed URLs found" % (len(feed_urls))
    count = 0
    while True:
        print "%s iteration %s.   %s" % (time.strftime(TIME_FMT_STR), count, get_memory_usage())
        threads = []
        for index, repo in enumerate(feed_urls):
            if len(threads) >= MAX_SYNC_JOBS:
                #print "Will wait: %s jobs running now" % (len(threads))
                threads = wait_till_one_free(threads)
            t = SyncThread(repo["id"], repo["url"], repo["feed_ca"], repo["feed_cert"])
            t.start()
            threads.append(t)
            #print "[%s/%s] sync job started." % (index, len(feed_urls))
        wait_for_all_complete(threads)
        count = count + 1



