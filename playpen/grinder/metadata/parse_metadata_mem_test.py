#!/usr/bin/env python

import os
import shlex
import subprocess
import sys
import time

from grinder.RepoFetch import RepoFetch
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../utils")
from memory_usage import MemoryUsage

TIME_FMT_STR = "%b%d_%Y__%l:%M%p"

LOG = open("%s.metadata_parse.output" % (time.strftime(TIME_FMT_STR)), "w")


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

def parse_metadata(label, url, download_dir, cacert=None, clientcert=None):
    try:
        yumFetch = RepoFetch(label, repourl=url, \
            cacert=cacert, clicert=clientcert, \
            download_dir=download_dir)
        yumFetch.setupRepo()
        yumFetch.getRepoData()
        #pkglist = yumFetch.getPackageList()
        #return len(pkglist)
        return 0
    finally:
        # Note, if we don't execute closeRepo() then we will leak memory.
        # running with closeRepo() and I am not seeing any memory leaked
        yumFetch.closeRepo()
        yumFetch.deleteBaseCacheDir()
        del yumFetch

def test_from_feed_urls(feed_urls, base_dir="./data"):
    feeds = parse_feed_urls(feed_urls)
    count = 0
    memUsage = MemoryUsage()
    while True:
        for f in feeds:
            download_dir = "./%s/%s" % (base_dir, f["id"])
            length = parse_metadata(f["id"], f["url"], download_dir, f["feed_ca"], f["feed_cert"])
            log("%s, %s, %s packages, iteration %s" % (memUsage.get_time_memory_stamp(), f["id"], length, count))
        count = count + 1
            

def test_simple_repo(url=None, label=None, download_dir=None):
    if not url:
        url = "http://repos.fedorapeople.org/repos/pulp/pulp/fedora-15/x86_64/"
    if not label:
        label = "pulp_f15_x86_64"
    if not download_dir:
        download_dir = "./data/%s" % (label)
    log("Fetching metadata for: %s" % (url))
    count = 0
    memUsage = MemoryUsage()
    while True:
        length = parse_metadata(label, url, download_dir)
        log("%s, %s, %s packages, iteration %s" % (memUsage.get_time_memory_stamp(), label, length, count))
        count = count + 1

def test_protected_repo(url=None, label=None, download_dir=None, clientcert=None, cacert=None):
    if not url:
        #url = "https://cdn.redhat.com/content/dist/rhel/rhui/server/6/6Server/i386/os"
        url = "https://cdn.redhat.com/content/dist/rhel/rhui/server/5/5.6/i386/source/SRPMS"
    if not label:
        #label = "rhel-server-6-6Server-i386"
        label = "rhel-server-srpms-5-5.6-i386"
    if not download_dir:
        download_dir = "./data/%s" % (label)
    if not cacert:
        #cacert = "/etc/pki/content/rhel-server-6-6Server-i386/feed-rhel-server-6-6Server-i386.ca"
        cacert = "/etc/pki/content/rhel-server-srpms-5-5.6-i386/feed-rhel-server-srpms-5-5.6-i386.ca"
    if not clientcert:
        #clientcert = "/etc/pki/content/rhel-server-6-6Server-i386/feed-rhel-server-6-6Server-i386.cert"
        clientcert = "/etc/pki/content/rhel-server-srpms-5-5.6-i386/feed-rhel-server-srpms-5-5.6-i386.cert"
    log("Fetching protected metadata for: %s" % (url))
    count = 0
    memUsage = MemoryUsage()
    while True:
        length = parse_metadata(label, url, download_dir, cacert, clientcert)
        log("%s, %s, %s packages, iteration %s" % (memUsage.get_time_memory_stamp(), label, length, count))
        count = count + 1

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_from_feed_urls(sys.argv[1])
        sys.exit(0)
    #test_simple_repo()
    test_protected_repo()
