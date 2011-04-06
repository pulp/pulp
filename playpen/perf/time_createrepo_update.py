#!/usr/bin/env python

# Python
import logging
import sys
import os
import time
import unittest
import random
from optparse import OptionParser

try:
    import json
except ImportError:
    import simplejson as json

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../../test/common/'
sys.path.insert(0, commondir)

import pymongo.json_util

import pulp
from pulp.server import auditing
from pulp.server import config
from pulp.server.util import constants
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.api.errata import ErrataApi
from pulp.server.db import connection
from pulp.server.db.model import RepoSource
from pulp.server.logs import start_logging, stop_logging
from pulp.server.util import random_string
from pulp.server.util import get_rpm_information
import testutil
#Override the change to LOCAL_STORAGE done in testutil
constants.LOCAL_STORAGE="/var/lib/pulp"

log = logging.getLogger(__name__)

def setup():
    stop_logging()
    override_file = os.path.abspath(os.path.dirname(__file__)) + '/pulp_perf_override.conf'
    try:
        config.add_config_file(override_file)
    except RuntimeError:
        pass
    start_logging()
    connection.initialize()
    auditing.initialize()
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    fmt = '%(funcName)s() @ %(filename)s:%(lineno)d - %(message)s'
    formatter = logging.Formatter(fmt)
    ch.setFormatter(formatter)
    log.addHandler(ch)
    return config.config

class TimeCreateRepo:
    def __init__(self):
        self.rapi = RepoApi()
        self.papi = PackageApi()
        self.eapi = ErrataApi()

    def get_repomd_filetypes(self, dir_path):
        f = os.path.join(dir_path, "repodata", "repomd.xml")
        return pulp.server.util.get_repomd_filetypes(f)

    def verify_repomd_filetypes(self, dir_path, prior_types):
        current_types = self.get_repomd_filetypes(dir_path)
        missing = []
        for t in prior_types:
            if t not in current_types:
                missing.append(t)
        return missing

    def time_package_metadata_update(self, repoid):
        repo = self.rapi.repository(repoid)
        if not repo:
            print "Couldn't find repo: %s" % (repoid)
            return
        source_path = os.path.join(pulp.server.util.top_repos_location(),
                repo["relative_path"])
        print "Updating metadata at: %s" % (source_path)
        start = time.time()
        pulp.server.util.create_repo(source_path)
        end = time.time()
        print "Update of metadata finished in %s seconds." % (end-start)
        current_types = self.get_repomd_filetypes(source_path)
        missing = self.verify_repomd_filetypes(source_path, current_types)
        if missing:
            print "We are missing these <%s> metadata types from %s" % (missing, source_path)

if __name__ == "__main__":
    setup()
    parser = OptionParser()
    parser.add_option("-r", "--repoid", dest="repoid", default=None,
                  help="repository id")
    (options, args) = parser.parse_args()
    if not options.repoid:
        parser.print_help()
        print "Please re-run with a repoid"
        sys.exit(1)
    tcr = TimeCreateRepo()
    tcr.time_package_metadata_update(options.repoid)


