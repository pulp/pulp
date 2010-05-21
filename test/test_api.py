#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Mike McCune
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
import sys
sys.path.append("../src")
import json
import time
import unittest
import logging
import os

import pymongo.json_util 

from pulp.api import RepoApi
from pulp.api import PackageApi
from pulp.api import ConsumerApi
from pulp.api import PackageVersionApi
from pulp.model import Package
from pulp.model import Consumer
from pulp.util import random_string

class TestApi(unittest.TestCase):
    def setUp(self):
        self.rapi = RepoApi()
        self.papi = PackageApi()
        self.capi = ConsumerApi()
        self.pvapi = PackageVersionApi()
        self.rapi.clean()
        self.papi.clean()
        self.capi.clean()
        self.pvapi.clean()
        
    def test_create(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'yum:http://example.com')
        assert(repo != None)

    def test_duplicate(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'yum:http://example.com')
        repo = self.rapi.create('some-id','some name', 
            'i386', 'yum:http://example.com')
        
        repos = self.rapi.repositories()
        assert(len(repos) == 1)
        
        
    def test_feed_types(self):
        failed = False
        try:
            repo = self.rapi.create('some-id','some name', 
                'i386', 'invalidtype:http://example.com/')
        except:
            failed = True
        assert(failed)

        try:
            repo = self.rapi.create('some-id','some name', 
                'i386', 'blippybloopyfoo')
        except:
            failed = True
        assert(failed)
        
        
        repo = self.rapi.create('some-id','some name', 
            'i386', 'yum:http://example.com')
        assert(repo != None)
        assert(repo.repo_source.type == 'yum')
        
        
    def test_clean(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'yum:http://example.com')
        self.rapi.clean()
        repos = self.rapi.repositories()
        assert(len(repos) == 0)
        
    def test_delete(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'yum:http://example.com')
        repos = self.rapi.delete('some-id')
        assert(repos == None or len(repos) == 0)
        
    def test_repositories(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'yum:http://example.com')
        
        # list all the repos
        repos = self.rapi.repositories()
        found = False
        assert(len(repos) > 0)
        for r in repos:
            ## TODO: See if we can get dot notation here on id field
            if (r['id'] == 'some-id'):
                found = True

        assert(found)
    
    def test_repository(self):
        repo = self.rapi.create('some-id','some name', \
            'i386', 'yum:http://example.com')
        
        found = self.rapi.repository('some-id')
        assert(found != None)
        assert(found['id'] == 'some-id')
        # assert(found.id == 'some-id')
        
    def test_repo_packages(self):
        repo = self.rapi.create('some-id','some name', \
            'i386', 'yum:http://example.com')
        package = Package('test_repo_packages','test package')
        repo.packages[package.id] = package
        self.rapi.update(repo)
        
        found = self.rapi.repository('some-id')
        packages = found['packages']
        assert(packages != None)
        assert(packages['test_repo_packages'] != None)
    
    def test_consumer_create(self):
        c = self.capi.create('test-consumer', 'some consumer desc')
        assert(c != None)
        found = self.capi.consumer('test-consumer')
        assert(found != None)
        
    def test_bulk_create(self):
        consumers = []
        for i in range(1005):
            consumers.append(Consumer(random_string(), random_string()))
        self.capi.bulkcreate(consumers)
        assert(len(self.capi.consumers()) == 1005)
            
    def test_consumerwithpackage(self):
        c = self.capi.create('test-consumer', 'some consumer desc')
        package = Package('test_consumerwithpackage','test package search')
        c.packageids.append(package.id)
        for i in range(10):
            package = Package(random_string(), random_string())
            c.packageids.append(package.id)
        self.capi.update(c)
        
        found = self.capi.consumerswithpackage('some-invalid-id')
        assert(len(found) == 0)

        found = self.capi.consumerswithpackage('test_consumerwithpackage')
        assert(len(found) > 0)
        
    def test_json(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'yum:http://example.com')
        jsonrepo = json.dumps(repo, default=pymongo.json_util.default)
        assert(jsonrepo != None)
        
        
        
    def test_sync(self):
        repo = self.rapi.create('some-id','some name', 'i386', 
                                'yum:http://mmccune.fedorapeople.org/pulp/')
        failed = False
        try:
            self.rapi.sync('invalid-id-not-found')
        except Exception:
            failed = True
        assert(failed)
        
        self.rapi.sync(repo.id)
        
        # Check that local storage has dir and rpms
        dirList = os.listdir(self.rapi.LOCAL_STORAGE + '/' + repo.id)
        assert(len(dirList) > 0)
        found = self.rapi.repository(repo.id)
        packages = found['packages']
        assert(packages != None)
        assert(len(packages) > 0)
        
    def test_local_sync(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir = my_dir + "/data/"
        repo = self.rapi.create('some-id','some name', 'i386', 
                                'local:file://%s' % datadir)
                                
        self.rapi.sync(repo.id)
        found = self.rapi.repository(repo.id)
        packages = found['packages']
        assert(packages != None)
        assert(len(packages) > 0)
        print packages
        p = packages.values()[0]
        assert(p['versions'] != None)
        # versions = p['versions']
        
    def test_package_versions(self):
        p = self.papi.create('some-package-id', 'some package desc')
        pv = self.pvapi.create(p.id, 0, '1.2.3', '1', 'i386')
        p.versions.append(pv)
        self.papi.update(p)
        
        found = self.papi.package(p.id)
        versions = found['versions']
        assert(versions != None)
        assert(versions[0]['packageid'] == p.id)
        print found
        
    def test_packages(self):
        p = self.papi.create('some-package-id', 'some package desc')
        packages = self.papi.packages()
        print "packages: %s" % packages
        assert(len(packages) > 0)
        
if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.INFO)
    unittest.main()
