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
import os
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src"
sys.path.append(srcdir)
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
        #self.papi.clean()
        self.capi.clean()
        self.pvapi.clean()
        self.pgapi.clean()
        self.pgcapi.clean()
        
    def setUp(self):
        config = loadTestConfig()

        self.rapi = RepoApi(config)
        self.rapi.localStoragePath = "/tmp"
        #self.papi = PackageApi(config)
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
        package = Package(repo.id, 'test_repo_packages')
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
        package = Package(repo["id"], 'test_repo_packages')
        pkggroup.default_package_names.append(package["packageid"])
        repo.packagegroups[pkggroup["groupid"]] = pkggroup
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
        package = Package(repo.id, 'test_repo_packages')
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
            consumers.append(Consumer(randomString(), randomString()))
        self.capi.bulkcreate(consumers)
        assert(len(self.capi.consumers()) == 1005)
            
    def test_consumerwithpackage(self):
        c = self.capi.create('test-consumer', 'some consumer desc')
        repo = self.rapi.create('some-id', 'some name',
                'i386', 'yum:http://example.com')
        test_pkg_name = "test_consumerwithpackage"
        #TODO: The consumer model/api needs to be updated, it's not setup to handle
        #       tracking a packageversion
        for i in range(10):
            c.packageids.append(test_pkg_name)
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
        found_a = self.rapi.repository(repo_a.id)
        found_b = self.rapi.repository(repo_b.id)
        # Verify each repo has the test package synced
        assert (found_a["packages"].has_key(test_pkg_name))
        assert (found_b["packages"].has_key(test_pkg_name))
        # Grab the associated package version (there should only be 1)
        # Ensure that the package versions have different checksums, but all other
        # keys are identical
        assert (len(found_a["packages"][test_pkg_name]) == 1)
        assert (len(found_b["packages"][test_pkg_name]) == 1)
        pkgVerA = found_a["packages"][test_pkg_name][0]
        pkgVerB = found_b["packages"][test_pkg_name][0]
        for key in ['epoch', 'version', 'release', 'arch', 'filename', 'name']:
            assert (pkgVerA[key] == pkgVerB[key])
        #Ensure checksums are not equal
        print "pkgVerA = %s" % (pkgVerA)
        print "pkgVerB = %s" % (pkgVerB)
        assert (pkgVerA['checksum'] != pkgVerB['checksum'])

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
        self.rapi.sync(repo_a.id)
        self.rapi.sync(repo_b.id)
        # Look up each repo from API
        found_a = self.rapi.repository(repo_a.id)
        found_b = self.rapi.repository(repo_b.id)
        # Verify each repo has the test package synced
        assert (found_a["packages"].has_key(test_pkg_name))
        assert (found_b["packages"].has_key(test_pkg_name))
        # Grab the associated package version (there should only be 1)
        # Ensure that the package versions have different md5sums, but all other
        # keys are identical

        assert (len(found_a["packages"][test_pkg_name]) == 1)
        assert (len(found_b["packages"][test_pkg_name]) == 1)
        pkgVerA = found_a["packages"][test_pkg_name][0]
        pkgVerB = found_b["packages"][test_pkg_name][0]
        # Ensure that the 2 PackageVersions instances actually point 
        # to the same single instance
        assert(repo_a['_id'] != repo_b['_id'])
        assert(pkgVerA['_id'] == pkgVerB['_id'])
    
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
        print('+++++++++ ' + self.rapi.localStoragePath)
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
        assert(p != None)
        # versions = p['versions']
        
    def test_package_versions(self):
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
        pv = self.pvapi.create(name=test_pkg_name, epoch=test_epoch, version=test_version, 
                release=test_release, arch=test_arch, description=test_description, 
                checksum_type="sha256", checksum=test_checksum, filename=test_filename)
        # Add this package version to the repo
        self.rapi.add_package_version(repo["id"], pv)
        # Lookup repo and confirm new package version was added
        repo = self.rapi.repository(repo["id"])
        self.assertTrue(repo["packages"].has_key(test_pkg_name))
        self.assertTrue(len(repo["packages"][test_pkg_name]) == 1)
        saved_pkg = repo["packages"][test_pkg_name][0]
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
        self.assertTrue(pkgs.has_key(test_pkg_name))
        self.assertTrue(len(pkgs[test_pkg_name]) == 1)
        self.assertTrue(pkgs[test_pkg_name][0]['filename'] == test_filename)
        pkgs = self.rapi.packageversions(repo['id'], test_pkg_name)
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(pkgs[0]['filename'] == test_filename)

        # Remove package version from repo
        self.rapi.remove_package_version(repo['id'], pv)
        repo = self.rapi.repository(repo['id'])
        self.assertTrue(not repo["packages"].has_key(test_pkg_name))
        # Verify package version from repo
        found = self.pvapi.packageversion(name=test_pkg_name, epoch=test_epoch, 
                version=test_version, release=test_release, arch=test_arch, 
                filename=test_filename, checksum_type=test_checksum_type,
                checksum=test_checksum)
        self.assertTrue(found.count() == 1)
        # Remove from PackageVersion collection
        self.pvapi.delete(found[0])
        # Verify it's deleted
        found = self.pvapi.packageversion(name=test_pkg_name, epoch=test_epoch, 
                version=test_version, release=test_release, arch=test_arch, 
                filename=test_filename, checksum_type=test_checksum_type,
                checksum=test_checksum)
        self.assertTrue(found.count() == 0)

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
