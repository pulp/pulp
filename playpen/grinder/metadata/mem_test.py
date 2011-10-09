#!/usr/bin/env python

import os
import shlex
import subprocess
import sys
import time

from grinder.RepoFetch import RepoFetch

TIME_FMT_STR = "%b%d_%Y__%l:%M%p"

LOG = open("%s.metadata_parse.output" % (time.strftime(TIME_FMT_STR)), "w")


def log(msg):
    print msg
    LOG.write("%s\n" % (msg))
    LOG.flush()

def get_memory_usage():
    pid = os.getpid()
    cmd = "pmap -d %s" % (pid)
    cmd = shlex.split(cmd)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    mem_usage =  out.splitlines()[-1]
    return mem_usage

def parse_metadata(label, url, download_dir, cacert=None, clientcert=None):
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
        del pkglist # just in case, explicit del of pkglist and yumFetch
        del yumFetch

def test_simple_repo(url=None, label=None, download_dir=None):
    if not url:
        url = "http://repos.fedorapeople.org/repos/pulp/pulp/fedora-15/x86_64/"
    if not label:
        label = "pulp_f15_x86_64"
    if not download_dir:
        download_dir = "./data/%s" % (label)
    log("Fetching metadata for: %s" % (url))
    count = 0
    while True:
        length = parse_metadata(label, url, download_dir)
        log("%s %s fetch metadata for %s packages.  Memory usage: %s" % (count, time.strftime(TIME_FMT_STR), length, get_memory_usage()))
        LOG.flush()
        count = count + 1

def test_protected_repo(url=None, label=None, download_dir=None, clientcert=None, cacert=None):
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
        length = parse_metadata(label, url, download_dir, cacert, clientcert)
        log("%s %s fetch metadata for %s packages.  Memory usage: %s" % (count, time.strftime(TIME_FMT_STR), length, get_memory_usage()))
        count = count + 1

if __name__ == "__main__":
    test_simple_repo()
    #test_protected_repo()
