#!/usr/bin/env python

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import yum

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../utils")
from memory_usage import MemoryUsage

TIME_FMT_STR = "%b%d_%Y__%l:%M%p"
LOG = open("%s.simple_yum_test.output" % (time.strftime(TIME_FMT_STR)), "w")


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

def setupYum(label, url, cacert=None, clientcert=None):
    repo = yum.yumRepo.YumRepository(label)
    repo.basecachedir = tempfile.mkdtemp()
    repo.cache = 0
    repo.metadata_expire = 0
    repo.baseurl = [url]
    repo.sslcacert = cacert
    repo.sslclientcert = clientcert
    repo.sslverify = 1
    return repo

def parse_metadata(label, url, download_dir, cacert=None, clientcert=None):
    yum_repo = setupYum(label, url, cacert, clientcert)
    try:
        for ftype in yum_repo.repoXML.fileTypes():
            ftypefile = yum_repo.retrieveMD(ftype)
        return 0
    finally:
        yum_repo.close()
        shutil.rmtree(yum_repo.basecachedir)


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

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_from_feed_urls(sys.argv[1])
        sys.exit(0)
    test_simple_repo()
