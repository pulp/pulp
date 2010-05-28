#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
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
sys.path.append("../../src")
import time
import unittest
import logging
import os

try:
    import json
except ImportError:
    import simplejson as json

import pymongo.json_util 

from pulp.api.consumer import ConsumerApi
from pulp.api.package import PackageApi
from pulp.api.package_group import PackageGroupApi
from pulp.api.package_group_category import PackageGroupCategoryApi
from pulp.api.package_version import PackageVersionApi
from pulp.api.repo import RepoApi

from pulp.model import Package
from pulp.model import PackageGroup
from pulp.model import PackageGroupCategory
from pulp.model import Consumer
from pulp.util import randomString

from util import loadTestConfig

class TestApi(unittest.TestCase):
    def clean(self):
        self.rapi.clean()
        self.papi.clean()
        self.capi.clean()
        self.pvapi.clean()
        self.pgapi.clean()
        self.pgcapi.clean()
        
    def setUp(self):
        config = loadTestConfig()

        self.rapi = RepoApi(config)
        self.rapi.localStoragePath = "/tmp"
        self.papi = PackageApi(config)
        self.capi = ConsumerApi(config)
        self.pvapi = PackageVersionApi(config)
        self.pgapi = PackageGroupApi(config)
        self.pgcapi = PackageGroupCategoryApi(config)
        self.clean()
        
    def tearDown(self):
        self.clean()
        
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
        package = Package(repo.id, 'test_repo_packages','test package')
        repo.packages[package["packageid"]] = package
        self.rapi.update(repo)
        
        found = self.rapi.repository('some-id')
        packages = found['packages']
        assert(packages != None)
        assert(packages['test_repo_packages'] != None)
    
    def test_repo_package_groups(self):
        repo = self.rapi.create('some-id','some name', \
            'i386', 'yum:http://example.com')
        pkggroup = PackageGroup('test-group-id', 'test-group-name', 
                'test-group-description')
        package = Package(repo.id, 'test_repo_packages','test package')
        pkggroup.default_package_names.append(package.id)
        repo.packagegroups[pkggroup.groupid] = pkggroup
        repo.packages[package["packageid"]] = package
        self.rapi.update(repo)
        
        found = self.rapi.repository('some-id')
        packages = found['packages']
        assert(packages != None)
        assert(packages['test_repo_packages'] != None)
        assert(found['packagegroups'] != None)
        print "test_repo_package_groups found['packagegroups'] = %s" % (found['packagegroups'])
        assert(pkggroup.groupid in found['packagegroups'])
    
    def test_repo_package_group_categories(self):
        repo = self.rapi.create('some-id','some name', \
            'i386', 'yum:http://example.com')
        package = Package(repo.id, 'test_repo_packages','test package')
        pkggroup = PackageGroup('test-group-id', 'test-group-name', 
                'test-group-description')
        pkggroup.default_package_names.append(package["packageid"])
        ctg = PackageGroupCategory('test-group-cat-id', 'test-group-cat-name',
                'test-group-cat-description')
        ctg.packagegroupids = pkggroup.id
        repo.packagegroupcategories[ctg.categoryid] = ctg
        repo.packagegroups[pkggroup.groupid] = pkggroup
        repo.packages[package["packageid"]] = package
        self.rapi.update(repo)
        
        found = self.rapi.repository('some-id')
        packages = found['packages']
        assert(packages != None)
        assert(packages['test_repo_packages'] != None)
        assert(found['packagegroups'] != None)
        print "test_repo_package_groups found['packagegroups'] = %s" % (found['packagegroups'])
        assert(pkggroup.groupid in found['packagegroups'])
        assert(found['packagegroupcategories'] != None)
        assert(ctg.categoryid in found['packagegroupcategories'])
    
    def test_consumer_create(self):
        c = self.capi.create('test-consumer', 'some consumer desc')
        assert(c != None)
        found = self.capi.consumer('test-consumer')
        assert(found != None)
        
    def test_bulk_create(self):
        consumers = []
        for i in range(1005):
            consumers.append(Consumer(randomString(), randomString()))
        self.capi.bulkcreate(consumers)
        assert(len(self.capi.consumers()) == 1005)
            
    def test_consumerwithpackage(self):
        c = self.capi.create('test-consumer', 'some consumer desc')
        repo = self.rapi.create('some-id', 'some name',
                'i386', 'yum:http://example.com')
        for i in range(10):
            package = self.rapi.create_package(repo["id"], 'test_consumerwithpackage',
                'test package search')
            repo = self.rapi.repository(repo["id"])
            c.packageids.append(package["packageid"])
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
        parsed = json.loads(jsonrepo)
        assert(parsed != None)
        print parsed
        
        
        
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
        dirList = os.listdir(self.rapi.localStoragePath + '/' + repo.id)
        assert(len(dirList) > 0)
        found = self.rapi.repository(repo.id)
        print "found = ", found
        packages = found['packages']
        print "packages = ", packages
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
        repo = self.rapi.create('some-id','some name',
            'i386', 'yum:http://example.com')
        p = self.rapi.create_package(repo.id, 'some-package-id',
                'some package desc')
        repo = self.rapi.repository(repo["id"])
        pv = self.pvapi.create(p["packageid"], 0, '1.2.3', '1', 'i386')
        #Explicit reference to the repo packages dict is needed
        # The SON Manipulator prob made a copy of the dict, which makes references
        # to p["versions"].append(pv) no longer work
        repo["packages"][p["packageid"]]["versions"].append(pv)
        self.rapi.update(repo)
        found = self.rapi.package(repo["id"], p["packageid"])
        versions = found['versions']
        assert(versions != None)
        assert(versions[0]['packageid'] == p["packageid"])
        
    def test_packages(self):
        repo = self.rapi.create('some-id','some name',
            'i386', 'yum:http://example.com')
        p = self.rapi.create_package(repo.id, 'some-package-id',
                'some package desc')
        repo = self.rapi.repository(repo["id"])
        packages = self.rapi.packages(repo["id"])
        assert(len(packages) > 0)
    
    def test_package_groups(self):
        pkggroup = self.pgapi.create('test-pkg-group-id', 'test-pkg-group-name', 
                'test-pkg-group-description')
        test_package_id = "test_package_id"
        pkggroup.default_package_names.append(test_package_id)
        self.pgapi.update(pkggroup)

        found = self.pgapi.packagegroup(pkggroup.id)
        print found
        assert(found['default_package_names'] != None)
        assert(test_package_id in found['default_package_names'])
    
    def test_package_group_categories(self):
        ctg = self.pgcapi.create('test_pkg_group_ctg_id', 'test_pkg_group_ctg_name',
                'test_pkg_group_description')
        test_pkg_group_id = 'test_package_group_id'
        ctg.packagegroupids.append(test_pkg_group_id)
        self.pgcapi.update(ctg)

        found = self.pgcapi.packagegroupcategory(ctg.id)
        print found
        assert(found['packagegroupids'] != None)
        assert(test_pkg_group_id in found['packagegroupids'])
        
if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.INFO)
    unittest.main()
