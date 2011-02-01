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
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    fmt = '%(funcName)s() @ %(filename)s:%(lineno)d - %(message)s'
    formatter = logging.Formatter(fmt)
    ch.setFormatter(formatter)
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
            end = time.time()
            repo_json = json.dumps(repo, default=pymongo.json_util.default)
            log.critical("All fields.  Packages: %s Length: %s _get_existing_repo(%s) took %s seconds" % \
                    (len(repo["packages"]), len(repo_json), repo_id, (end - start)))
        
        for repo_id in self.get_available_repoids():
            start = time.time()
            fields = ["id", "package_count", "relative_path"]
            repo = self.rapi._get_existing_repo(repo_id, fields=fields)
            end = time.time()
            repo_json = json.dumps(repo, default=pymongo.json_util.default)
            log.critical("Limited fields: Shortened fetch<no packages>: Length: %s _get_existing_repo(%s) took %s seconds" % \
                    (len(repo_json), repo_id, (end - start)))

    def time_package_lookups_simple(self):
        start = time.time()
        for repo_id in self.get_available_repoids():
            repo = self.rapi._get_existing_repo(repo_id)
            packages = {}
            for pkg_id in repo["packages"]:
                pkg = self.papi.package(pkg_id)
                packages[pkg_id] = pkg
            end = time.time()
            repo_json = json.dumps(repo, default=pymongo.json_util.default)
            packages_json = json.dumps(packages, default=pymongo.json_util.default)
            log.critical("Full retrieval of Repo %s and %s packages took %s seconds." % (repo_id, len(repo["packages"]), (end - start)))

    def time_package_lookups_batched(self):
        start = time.time()
        for repo_id in self.get_available_repoids():
            start = time.time()
            repo = self.rapi._get_existing_repo(repo_id)
            packages = self.rapi.get_packages_by_id(repo_id, repo["packages"])
            end = time.time()
            repo_json = json.dumps(repo, default=pymongo.json_util.default)
            packages_json = json.dumps(packages, default=pymongo.json_util.default)
            log.critical("Full retrieval <batched> of Repo<%s> %s and %s packages<%s> took %s seconds." % (len(repo_json), \
                    repo_id, len(repo["packages"]), len(packages_json), (end - start)))

if __name__ == "__main__":
    setup()
    tr = TimeRepos()
    tr.time_get_available_repoids()
    tr.time_get_existing_repo()
    #tr.time_package_lookups_simple()
    tr.time_package_lookups_batched()

