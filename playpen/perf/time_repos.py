#!/usr/bin/env python

# Python
import logging
import sys
import os
import time
import unittest
import random

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

from pulp.server import auditing
from pulp.server import config
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.api.errata import ErrataApi
from pulp.server.db import connection
from pulp.server.db.model import RepoSource
from pulp.server.logs import start_logging, stop_logging
from pulp.server.util import random_string
from pulp.server.util import get_rpm_information
import testutil

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
    # setup logging for this file
    log.setLevel(logging.DEBUG)
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter
    fmt = '%(asctime)s [%(levelname)s][%(threadName)s] %(funcName)s() @ %(filename)s:%(lineno)d - %(message)s'
    formatter = logging.Formatter(fmt)
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    log.addHandler(ch)
    return config.config

class TimeRepos:
    def __init__(self):
        self.rapi = RepoApi()
        self.papi = PackageApi()
        self.eapi = ErrataApi()

    def get_available_repoids(self):
        return [r["id"] for r in self.rapi.repositories(fields=["id"])]

    def time_get_available_repoids(self):
        start = time.time()
        repoids = self.get_available_repoids()
        end = time.time()
        log.critical("%s ids query for repositories took %s seconds"  % ((len(repoids), (end - start))))

        start = time.time()
        repoids = self.rapi.objectdb.find({}, {"id":1})
        end = time.time()
        log.critical("%s ids query for repositories custom took %s seconds"  % (repoids.count(), (end - start)))
    
    def time_get_existing_repo(self):
        for repo_id in self.get_available_repoids():
            start = time.time()
            repo = self.rapi._get_existing_repo(repo_id)
            repo_json = json.dumps(repo, default=pymongo.json_util.default)
            end = time.time()
            log.critical("Packages: %s Length: %s _get_existing_repo(%s) took %s seconds" % \
                    (len(repo["packages"]), len(repo_json), repo_id, (end - start)))
        
        for repo_id in self.get_available_repoids():
            start = time.time()
            fields = ["id", "package_count", "relative_path"]
            repo = self.rapi._get_existing_repo(repo_id, fields=fields)
            repo_json = json.dumps(repo, default=pymongo.json_util.default)
            end = time.time()
            log.critical("Shortened fetch<no packages>: Length: %s _get_existing_repo(%s) took %s seconds" % \
                    (len(repo_json), repo_id, (end - start)))


if __name__ == "__main__":
    #start_logging()
    setup()
    tr = TimeRepos()
    tr.time_get_available_repoids()
    tr.time_get_existing_repo()


