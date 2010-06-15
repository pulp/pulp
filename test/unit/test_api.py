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

# Python
import logging
import sys
import os
import time
import unittest

try:
    import json
except ImportError:
    import simplejson as json

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import pymongo.json_util 

from pulp.api.consumer import ConsumerApi
from pulp.api.package import PackageApi
from pulp.api.package_group import PackageGroupApi
from pulp.api.package_group_category import PackageGroupCategoryApi
from pulp.api.repo import RepoApi

from pulp.model import Package
from pulp.model import PackageGroup
from pulp.model import PackageGroupCategory
from pulp.model import Consumer
from pulp.util import random_string

from ConfigParser import ConfigParser

import testutil


class TestApi(unittest.TestCase):

    def clean(self):
        self.rapi.clean()
        self.papi.clean()
        self.capi.clean()
        self.pgapi.clean()
        self.pgcapi.clean()
        
    def setUp(self):
        self.config = testutil.load_test_config()
        self.rapi = RepoApi(self.config)
        self.papi = PackageApi(self.config)
        self.capi = ConsumerApi(self.config)
        self.pgapi = PackageGroupApi(self.config)
        self.pgcapi = PackageGroupCategoryApi(self.config)
        self.clean()
        
    def tearDown(self):
        self.clean()
        
    def test_create(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'yum:http://example.com')
        assert(repo != None)

    def test_duplicate(self):
        id = 'some-id'
        name = 'some name'
        arch = 'i386'
        feed = 'yum:http://example.com'
        repo = self.rapi.create(id, name, arch, feed)
        try:
            repo = self.rapi.create(id, name, arch, feed)
            raise Exception, 'Duplicate allowed'
        except:
            pass
        
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
        assert(repo['repo_source']['type'] == 'yum')
        
        
    def test_clean(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'yum:http://example.com')
        self.rapi.clean()
        repos = self.rapi.repositories()
        assert(len(repos) == 0)
        
    def test_delete(self):
        id = 'some-id'
        repo = self.rapi.create(id,'some name', 'i386', 'yum:http://example.com')
        repo = self.rapi.repository(id)
        assert(repo is not None)
        self.rapi.delete(id=id)
        repo = self.rapi.repository(id)
        assert(repo is None)
        
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
        p = self.create_package('test_repo_packages')
        self.rapi.add_package(repo["id"], p['id'])
        for i in range(10):
            package = self.create_package(random_string())
            self.rapi.add_package(repo["id"], package['id'])
        
        found = self.rapi.repository('some-id')
        packages = found['packages']
        assert(packages != None)
        assert(packages[p['id']] != None)
    
    def test_repo_package_groups(self):
        repo = self.rapi.create('some-id','some name', \
            'i386', 'yum:http://example.com')
        pkggroup = PackageGroup('test-group-id', 'test-group-name', 
                'test-group-description')
        package = self.create_package('test_repo_packages')
        pkggroup.default_package_names.append(package["id"])
        repo['packagegroups'][pkggroup["id"]] = pkggroup
        repo['packages'][package["id"]] = package
        
        self.rapi.update(repo)
        
        found = self.rapi.repository('some-id')
        assert(found['packagegroups'] != None)
        assert(pkggroup['id'] in found['packagegroups'])
    
    def test_repo_package_group_categories(self):
        repo = self.rapi.create('some-id_pkg_group_categories','some name', \
            'i386', 'yum:http://example.com')
        pkggroup = PackageGroup('test-group-id', 'test-group-name', 
                'test-group-description')
        pkggroup.default_package_names.append("test-package-name")
        ctg = PackageGroupCategory('test-group-cat-id', 'test-group-cat-name',
                'test-group-cat-description')
        ctg.packagegroupids = pkggroup.id
        repo['packagegroupcategories'][ctg.id] = ctg
        repo['packagegroups'][pkggroup.id] = pkggroup
        self.rapi.update(repo)
        
        found = self.rapi.repository('some-id_pkg_group_categories')
        assert(found['packagegroups'] != None)
        assert(pkggroup['id'] in found['packagegroups'])
        assert(found['packagegroupcategories'] != None)
        assert(ctg['id'] in found['packagegroupcategories'])
    
    def test_consumer_create(self):
        c = self.capi.create('test-consumer', 'some consumer desc')
        assert(c != None)
        found = self.capi.consumer('test-consumer')
        assert(found != None)
        
    def test_consumer_bind(self):
        cid = 'bindconsumerid'
        rid = 'bindrepoid'
        key = 'repoids'
        self.capi.create(cid, 'test bind/unbind.')
        self.rapi.create(rid, 'testbind', 'noarch', 'yum:http://foo')
        self.capi.bind(cid, rid)
        consumer = self.capi.consumer(cid)
        assert(rid in consumer[key])
        self.capi.unbind(cid, rid)
        consumer = self.capi.consumer(cid)
        assert(rid not in consumer[key])

    def test_bulk_create(self):
        consumers = []
        for i in range(1005):
            consumers.append(Consumer(random_string(), random_string()))
        self.capi.bulkcreate(consumers)
        all = self.capi.consumers()
        n = len(all)
        print '%d consumers found' % n
        assert(n == 1005)
            
    def test_consumerwithpackage(self):
        c = self.capi.create('test-consumer', 'some consumer desc')
        repo = self.rapi.create('some-id', 'some name',
                'i386', 'yum:http://example.com')
        test_pkg_name = "test_consumerwithpackage"
        #TODO: The consumer model/api needs to be updated, it's not setup to handle
        #       tracking a package
        package = self.create_package(test_pkg_name)
        c['packageids'].append(package["id"])
        for i in range(10):
            package = self.create_package(random_string())
            c['packageids'].append(package["id"])
        self.capi.update(c)
        
        found = self.capi.consumers_with_package_name('some-invalid-id')
        
        assert(len(found) == 0)

        found = self.capi.consumers_with_package_name('test_consumerwithpackage')
        assert(len(found) > 0)
        
    def test_json(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'yum:http://example.com')
        jsonrepo = json.dumps(repo, default=pymongo.json_util.default)
        assert(jsonrepo != None)
        parsed = json.loads(jsonrepo)
        assert(parsed != None)
        print parsed
    
    def test_sync_two_repos_same_nevra_different_checksum(self):
        """
        Sync 2 repos that have a package with same NEVRA 
        but different checksum
        """
        test_pkg_name = "pulp-test-package-same-nevra"
        my_dir = os.path.abspath(os.path.dirname(__file__))
        repo_name_a = "test_same_nevra_diff_checksum_repo_A"
        repo_name_b = "test_same_nevra_diff_checksum_repo_B"
        datadir_a = my_dir + "/data/sameNEVRA_differentChecksums/A/repo/"
        datadir_b = my_dir + "/data/sameNEVRA_differentChecksums/B/repo/"

        # Create & Sync Repos
        repo_a = self.rapi.create(repo_name_a,'some name', 'x86_64', 
                                  'local:file://%s' % datadir_a)
        repo_b = self.rapi.create(repo_name_b,'some name', 'x86_64', 
                                'local:file://%s' % datadir_b)
        self.rapi.sync(repo_a["id"])
        self.rapi.sync(repo_b["id"])
        # Look up each repo from API
        found_a = self.rapi.repository(repo_a['id'])
        found_b = self.rapi.repository(repo_b['id'])

        # Verify each repo has the test package synced
        found_a_pid = None
        for p in found_a["packages"].values():
            if (p['name'].index(test_pkg_name) >= 0):
                found_a_pid = p['id']
        assert(found_a_pid != None)
        
        found_b_pid = None
        for p in found_b["packages"].values():
            if (p['name'].index(test_pkg_name) >= 0):
                found_b_pid = p['id']
        assert(found_b_pid != None)
        packagea = found_a["packages"][found_a_pid]
        packageb = found_b["packages"][found_b_pid]
        
        # Grab the associated package version (there should only be 1)
        # Ensure that the package versions have different checksums, but all other
        # keys are identical
        for key in ['epoch', 'version', 'release', 'arch', 'filename', 'name']:
            assert (packagea[key] == packageb[key])
        self.assertTrue(packagea['checksum'] != packageb['checksum'])
        #TODO:
        # Add test to compare checksum when it's implemented in Package
        # verify the checksums are different

    def test_sync_two_repos_share_common_package(self):
        """
        Sync 2 repos that share a common package, same NEVRA
        same checksum
        """
        test_pkg_name = "pulp-test-package"
        my_dir = os.path.abspath(os.path.dirname(__file__))
        repo_name_a = "test_two_repos_share_common_pkg_repo_A"
        repo_name_b = "test_two_repos_share_common_pkg_repo_B"
        datadir_a = my_dir + "/data/sameNEVRA_sameChecksums/A/repo/"
        datadir_b = my_dir + "/data/sameNEVRA_sameChecksums/B/repo/"
        # Create & Sync Repos
        repo_a = self.rapi.create(repo_name_a,'some name', 'x86_64', 
                                'local:file://%s' % datadir_a)
        repo_b = self.rapi.create(repo_name_b,'some name', 'x86_64', 
                                'local:file://%s' % datadir_b)
        self.rapi.sync(repo_a['id'])
        self.rapi.sync(repo_b['id'])
        # Look up each repo from API
        found_a = self.rapi.repository(repo_a['id'])
        found_b = self.rapi.repository(repo_b['id'])
        # Verify each repo has the test package synced
        # Verify each repo has the test package synced
        found_a_pid = None
        for p in found_a["packages"].values():
            if (p['name'].index(test_pkg_name) >= 0):
                found_a_pid = p['id']
        assert(found_a_pid != None)
        
        found_b_pid = None
        for p in found_b["packages"].values():
            if (p['name'].index(test_pkg_name) >= 0):
                found_b_pid = p['id']
        assert(found_b_pid != None)
        packagea = found_a["packages"][found_a_pid]
        packageb = found_b["packages"][found_b_pid]

        # Ensure that the 2 Package instances actually point 
        # to the same single instance
        assert(repo_a['_id'] != repo_b['_id'])
        assert(packagea['_id'] == packageb['_id'])
    
    def test_sync(self):
        repo = self.rapi.create('some-id','some name', 'i386', 
                                'yum:http://mmccune.fedorapeople.org/pulp/')
        failed = False
        try:
            self.rapi.sync('invalid-id-not-found')
        except Exception:
            failed = True
        assert(failed)
        
        self.rapi.sync(repo['id'])
        
        # Check that local storage has dir and rpms
        dirList = os.listdir(self.config.get('paths', 'local_storage') + '/' + repo['id'])
        assert(len(dirList) > 0)
        found = self.rapi.repository(repo['id'])
        packages = found['packages']
        assert(packages != None)
        assert(len(packages) > 0)
        
    def test_local_sync(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir = my_dir + "/data/"
        repo = self.rapi.create('some-id','some name', 'i386', 
                                'local:file://%s' % datadir)
                                
        self.rapi.sync(repo['id'])
        found = self.rapi.repository(repo['id'])
        packages = found['packages']
        assert(packages != None)
        assert(len(packages) > 0)
        print packages
        p = packages.values()[0]
        assert(p != None)
        # versions = p['versions']
        
    def create_package(self, name): 
        test_pkg_name = name
        test_epoch = "1"
        test_version = "1.2.3"
        test_release = "1.el5"
        test_arch = "x86_64"
        test_description = "test description text"
        test_checksum_type = "sha256"
        test_checksum = "9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e"
        test_filename = "test-filename-1.2.3-1.el5.x86_64.rpm"
        p = self.papi.create(name=test_pkg_name, epoch=test_epoch, version=test_version, 
                release=test_release, arch=test_arch, description=test_description, 
                checksum_type="sha256", checksum=test_checksum, filename=test_filename)
        lookedUp = self.papi.package(p['id'])
        return lookedUp
        
    def test_packages(self):
        repo = self.rapi.create('some-id','some name',
            'i386', 'yum:http://example.com')
        repo = self.rapi.repository(repo["id"])
        test_pkg_name = "test_package_versions_name"
        test_epoch = "1"
        test_version = "1.2.3"
        test_release = "1.el5"
        test_arch = "x86_64"
        test_description = "test description text"
        test_checksum_type = "sha256"
        test_checksum = "9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e"
        test_filename = "test-filename-1.2.3-1.el5.x86_64.rpm"
        p = self.papi.create(name=test_pkg_name, epoch=test_epoch, version=test_version, 
                release=test_release, arch=test_arch, description=test_description, 
                checksum_type="sha256", checksum=test_checksum, filename=test_filename)
        print "Package! %s" % p
        # Add this package version to the repo
        self.rapi.add_package(repo["id"], p['id'])
        # Lookup repo and confirm new package version was added
        repo = self.rapi.repository(repo["id"])
        self.assertTrue(repo["packages"].has_key(p['id']))
        packageid = p['id']
        self.assertTrue(len(repo["packages"][p['id']]) != None)
        saved_pkg = repo["packages"][packageid]
        self.assertTrue(saved_pkg['name'] == test_pkg_name)
        self.assertTrue(saved_pkg['epoch'] == test_epoch)
        self.assertTrue(saved_pkg['version'] == test_version)
        self.assertTrue(saved_pkg['release'] == test_release)
        self.assertTrue(saved_pkg['arch'] == test_arch)
        self.assertTrue(saved_pkg['description'] == test_description)
        self.assertTrue(saved_pkg['checksum'].has_key(test_checksum_type))
        self.assertTrue(saved_pkg['checksum'][test_checksum_type] == test_checksum)
        self.assertTrue(saved_pkg['filename'] == test_filename)
        # Verify we can find this package version through repo api calls
        pkgs = self.rapi.packages(repo['id'])
        self.assertTrue(pkgs.has_key(packageid))
        self.assertTrue(pkgs[packageid] != None)
        self.assertTrue(pkgs[packageid]['filename'] == test_filename)
        pkgs = self.rapi.packages(repo['id'], test_pkg_name)
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(pkgs[0]['filename'] == test_filename)

        # Remove package version from repo
        self.rapi.remove_package(repo['id'], p)
        repo = self.rapi.repository(repo['id'])
        self.assertTrue(not repo["packages"].has_key(test_pkg_name))
        # Verify package version from repo
        found = self.papi.packages(name=test_pkg_name, epoch=test_epoch, 
                version=test_version, release=test_release, arch=test_arch, 
                filename=test_filename, checksum_type=test_checksum_type,
                checksum=test_checksum)
        self.assertTrue(len(found) == 1)
        # Check returned in search with no params
        all = self.papi.packages()
        self.assertTrue(len(all) > 0)

        # Remove from Package collection
        self.papi.delete(found[0])
        # Verify it's deleted
        found = self.papi.packages(name=test_pkg_name, epoch=test_epoch, 
                version=test_version, release=test_release, arch=test_arch, 
                filename=test_filename, checksum_type=test_checksum_type,
                checksum=test_checksum)
        self.assertTrue(len(found) == 0)
        # Check nothing returned in search with no params
        all = self.papi.packages()
        self.assertTrue(len(all) == 0)
        

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
