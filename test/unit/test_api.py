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
import random

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

from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.consumer_group import ConsumerGroupApi
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.api.errata import ErrataApi
from pulp.server.auth.certificate import Certificate
from pulp.server.db.model import PackageGroup
from pulp.server.db.model import PackageGroupCategory
from pulp.server.db.model import Consumer
from pulp.server.util import random_string
from pulp.server.util import get_rpm_information
from pulp.client.utils import generatePakageProfile


import testutil

logging.root.setLevel(logging.ERROR)

class TestApi(unittest.TestCase):

    def clean(self):
        self.rapi.clean()
        self.papi.clean()
        self.capi.clean()
        self.cgapi.clean()
        self.eapi.clean()
        
    def setUp(self):
        self.config = testutil.load_test_config()
        self.rapi = RepoApi()
        self.papi = PackageApi()
        self.capi = ConsumerApi()
        self.cgapi = ConsumerGroupApi()
        self.eapi  = ErrataApi()
        self.clean()
        
    def tearDown(self):
        self.clean()
        
    def test_create(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'yum:http://example.com')
        assert(repo is not None)

    def test_create_feedless(self):
        repo = self.rapi.create('some-id-no-feed', 'some name', 'i386')
        assert(repo is not None)

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
        assert(repo is not None)
        assert(repo['source']['type'] == 'yum')
        
        
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

    def test_delete_feedless(self):
        id = 'some-id-no-feed'
        repo = self.rapi.create(id,'some name', 'i386')
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
        assert(found is not None)
        assert(found['id'] == 'some-id')
        
    def test_consumer_group(self):
        print "Consumer group tests:"
        cg = self.cgapi.create('some-id','some description')

        found = self.cgapi.consumergroup('some-id')
        assert(found is not None)
        print found['description']
        assert(found['id'] == 'some-id')

        found = self.cgapi.consumergroup('some-id-that-doesnt-exist')
        assert(found is None)

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
        assert(packages is not None)
        assert(packages[p['id']] is not None)
        
    def test_repo_erratum(self):
        repo = self.rapi.create('some-id','some name', \
            'i386', 'yum:http://example.com')
        id = 'test_errata_id_1'
        title = 'test_errata_title_1'
        description = 'test_errata_description_1'
        version = '1.0'
        release = '0'
        type = 'test_errata_type'
        test_errata_1 = self.eapi.create(id, title, description, version, release, type)

        self.assertTrue(test_errata_1 is not None)
        self.rapi.add_erratum(repo['id'], test_errata_1['id'])

        errata = self.rapi.errata('some-id', types=['test_errata_type'])
        self.assertTrue(len(errata) == 1)
        
        self.rapi.delete_erratum(repo['id'], test_errata_1['id'])
        
        errata = self.rapi.errata('some-id', types=['test_errata_type'])
        self.assertTrue(len(errata) == 0)
        
    def test_repo_errata(self):
        repo = self.rapi.create('some-id','some name', \
            'i386', 'yum:http://example.com')
        id = 'test_errata_id_1'
        title = 'test_errata_title_1'
        description = 'test_errata_description_1'
        version = '1.0'
        release = '0'
        type = 'test_errata_type'
        test_errata_1 = self.eapi.create(id, title, description, version, release, type)
        self.assertTrue(test_errata_1 is not None)
        
        id = 'test_errata_id_2'
        title = 'test_errata_title_2'
        description = 'test_errata_description_2'
        version = '1.0'
        release = '0'
        type = 'test_errata_type'
        test_errata_2 = self.eapi.create(id, title, description, version, release, type)
        self.assertTrue(test_errata_2 is not None)
        self.rapi.add_errata(repo['id'], [test_errata_1['id'], test_errata_2['id']])
        
        errata = self.rapi.errata('some-id', types=['test_errata_type'])
        self.assertTrue(len(errata) == 2)

        self.rapi.delete_errata(repo['id'], [test_errata_1['id'], test_errata_2['id']])
        
        errata = self.rapi.errata('some-id', types=['test_errata_type'])
        self.assertTrue(len(errata) == 0)
        
    def test_consumer_errata(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        repo = self.rapi.create('some-id','some name', \
            'x86_64', 'yum:http://example.com')
        id = 'test_errata_id_1'
        title = 'test_errata_title_1'
        description = 'test_errata_description_1'
        version = '1.0'
        release = '0'
        type = 'test_errata_type'
        test_errata_1 = self.eapi.create(id, title, description, version, release, type)
        assert(test_errata_1 is not None)
        
        epkg = get_rpm_information(my_dir + "/data/pulp-test-package-0.3.1-1.fc11.x86_64.rpm")
        test_pkg_name = epkg["name"]
        test_epoch = epkg["epoch"]
        test_version = epkg["version"]
        test_release = epkg["release"]
        test_arch = epkg["arch"]
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
        self.rapi.update(repo)
        test_errata_1["pkglist"] = [{"packages" : [{'src': 'http://download.fedoraproject.org/pub/fedora/linux/updates/11/x86_64/pulp-test-package-0.3.1-1.fc11.x86_64.rpm', 
                                                    'name': 'pulp-test-package', 
                                                    'filename': 'pulp-test-package-0.3.1-1.fc11.x86_64.rpm', 
                                                    'epoch': '0', 'version': '0.3.1', 'release': '1.fc11', 
                                                    'arch': 'x86_64'}]}]

        self.eapi.update(test_errata_1)
        repo["errata"] = {"security" : [test_errata_1['id']]}

        cid = 'test-consumer'
        c = self.capi.create(cid, 'some consumer desc')
        self.assertTrue(c is not None)

        info1 = get_rpm_information(my_dir + \
                        "/data/pulp-test-package-0.2.1-1.fc11.x86_64.rpm")
        info2 = get_rpm_information(my_dir + \
                        "/data/pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm")
        
        packages = generatePakageProfile([info1, info2])
        c['package_profile'] = packages
        self.assertTrue(c['package_profile'] is not None)
        self.capi.update(c)

        self.rapi.update(repo)
        c["repoids"] = [repo['id']]
        self.capi.update(c)

        errlist = self.capi.listerrata(c['id'])
        assert(len(errlist) == 1)
        
        pkguplist = self.capi.list_package_updates(c['id'])
        assert(len(pkguplist) == 1)
        
    def test_repo_package_by_name(self):
        repo = self.rapi.create('some-id','some name', \
            'i386', 'yum:http://example.com')
        p = self.create_package('test_pkg_by_name')
        self.rapi.add_package(repo["id"], p['id'])
        
        pkg = self.rapi.get_package(repo['id'], p['name'])
        assert(pkg is not None)
    
    def test_repo_package_groups(self):
        repo = self.rapi.create('some-id','some name', \
            'i386', 'yum:http://example.com')
        pkggroup = self.rapi.create_packagegroup(repo["id"],
                'test-group-id', 'test-group-name',
                'test-group-description')
        package = self.create_package('test_repo_packages')
        self.rapi.add_package(repo["id"], package["id"])
        self.rapi.add_package_to_group(repo["id"], pkggroup["id"],
                package["name"], gtype="default")
        # Verify package is present in group
        found = self.rapi.repository('some-id')
        self.assertTrue(found['packagegroups'] is not None)
        self.assertTrue(pkggroup['id'] in found['packagegroups'])
        self.assertTrue(package["name"] in \
                found['packagegroups'][pkggroup['id']]['default_package_names'])
        # Remove package from package group
        self.rapi.delete_package_from_group(repo["id"], pkggroup["id"],
                package["name"], gtype="default")
        found = self.rapi.repository('some-id')
        self.assertTrue(found['packagegroups'] is not None)
        self.assertTrue(pkggroup['id'] in found['packagegroups'])
        self.assertTrue(package["name"] not in \
                found['packagegroups'][pkggroup['id']]['default_package_names'])
        # Remove packagegroup from repo
        self.rapi.delete_packagegroup(repo["id"], pkggroup["id"])
        found = self.rapi.repository('some-id')
        self.assertTrue(len(found['packagegroups']) == 0)


    
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
        assert(found['packagegroups'] is not None)
        assert(pkggroup['id'] in found['packagegroups'])
        assert(found['packagegroupcategories'] is not None)
        assert(ctg['id'] in found['packagegroupcategories'])
    
    def test_consumer_create(self):
        c = self.capi.create('test-consumer', 'some consumer desc')
        self.assertTrue(c is not None)
        found = self.capi.consumer('test-consumer')
        self.assertTrue(found is not None)
        
        # test that we get back the consumer from the list method
        consumers = self.capi.consumers()
        self.assertTrue(len(consumers) == 1)
        self.assertTrue(c['id'] == consumers[0]['id'])
        
    def test_consumer_certificate(self):
        c = self.capi.create('test-consumer', 'some consumer desc')
        (pk, pem) = self.capi.certificate(c['id'])
        self.assertTrue(pem is not None)
        cert = Certificate()
        cert.update(str(pem))
        subject = cert.subject()
        consumer_cert_uid = subject.get('CN', None)
        self.assertEqual(c['id'], consumer_cert_uid)
        
        
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

    def __test_consumer_installpackages(self):
        cid = 'bindconsumerid'
        packagenames = ['A','B','C']
        self.capi.create(cid, 'test install package.')
        result = self.capi.installpackages(cid, packagenames)
        assert(result == packagenames)

    def test_bulk_create(self):
        consumers = []
        my_dir = os.path.abspath(os.path.dirname(__file__))
        info1 = get_rpm_information(my_dir + "/data/pulp-test-package-0.2.1-1.fc11.x86_64.rpm")
        info2 = get_rpm_information(my_dir + "/data/pulp-test-package-0.3.1-1.fc11.x86_64.rpm")
        info3 = get_rpm_information(my_dir + "/data/pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm")
        
        packages = generatePakageProfile([info1, info2, info3])

        for i in range(1005):
            c = Consumer(random_string(), random_string())
            c['package_profile'] = packages
            consumers.append(c)
            
        self.capi.bulkcreate(consumers)
        all = self.capi.consumers()
        n = len(all)
        assert(n == 1005)
            
    def test_consumerwithpackage(self):
        c = self.capi.create('test-consumer', 'some consumer desc')
        repo = self.rapi.create('some-id', 'some name',
                'i386', 'yum:http://example.com')
        my_dir = os.path.abspath(os.path.dirname(__file__))
        
        info1 = get_rpm_information(my_dir + "/data/pulp-test-package-0.2.1-1.fc11.x86_64.rpm")
        info2 = get_rpm_information(my_dir + "/data/pulp-test-package-0.3.1-1.fc11.x86_64.rpm")
        info3 = get_rpm_information(my_dir + "/data/pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm")
        
        packages = generatePakageProfile([info1, info2, info3])
        
        for i in range(10):
            randName = random_string()
            package = self.create_package(randName)
            packages.append(package)
            
        c['package_profile'] = packages
        self.capi.update(c)
        self.assertTrue(c['package_profile'] is not None)
        ## Look back up from DB
        c = self.capi.consumer(c['id'])
        found = False
        for p in c['package_profile']:
            if (p['name'] == 'pulp-test-package'):
                found = True
        self.assertTrue(found)
        found = self.capi.consumers_with_package_names(['some-invalid-id'])
        assert(len(found) == 0)

        found = self.capi.consumers_with_package_names(['pulp-test-package'])
        assert(len(found) > 0)
        
        packages = self.capi.packages(c['id'])
        self.assertTrue(packages is not None)
        self.assertTrue(len(packages) > 0)
        
    def test_json(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'yum:http://example.com')
        jsonrepo = json.dumps(repo, default=pymongo.json_util.default)
        assert(jsonrepo is not None)
        parsed = json.loads(jsonrepo)
        assert(parsed is not None)
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
        # This will get fixed when we move the async nature of sync down into 
        # the API layer
        import time
        time.sleep(5)
        
        # Look up each repo from API
        found_a = self.rapi.repository(repo_a['id'])
        found_b = self.rapi.repository(repo_b['id'])

        # Verify each repo has the test package synced
        found_a_pid = None
        for p in found_a["packages"].values():
            if (p['name'].index(test_pkg_name) >= 0):
                found_a_pid = p['id']
        assert(found_a_pid is not None)
        
        found_b_pid = None
        for p in found_b["packages"].values():
            if (p['name'].index(test_pkg_name) >= 0):
                found_b_pid = p['id']
        assert(found_b_pid is not None)
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
        assert(found_a_pid is not None)
        
        found_b_pid = None
        for p in found_b["packages"].values():
            if (p['name'].index(test_pkg_name) >= 0):
                found_b_pid = p['id']
        assert(found_b_pid is not None)
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
        assert(packages is not None)
        assert(len(packages) > 0)
    
    def test_sync_feedless(self):
        repo = self.rapi.create('some-id-no-feed','some name', 'i386')
        # verify repo without feed is not syncable
        failed = False
        try:
            self.rapi.sync(repo['id'])
        except Exception:
            # raises a PulpException
            # 'This repo is not setup for sync. Please add packages using upload.'
            failed = True
        assert(failed)

    def test_local_sync(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir = my_dir + "/data/"
        repo = self.rapi.create('some-id','some name', 'i386', 
                                'local:file://%s' % datadir)
        print "Repo: %s" % repo
                                
        self.rapi.sync(repo['id'])
        found = self.rapi.repository(repo['id'])
        packages = found['packages']
        assert(packages is not None)
        assert(len(packages) > 0)
        print packages
        p = packages.values()[0]
        assert(p is not None)
        # versions = p['versions']
        
    # Meant to make sure we can create a repo with 5000+ packages without BSON
    # size errors
    def test_sync_large_repo(self):
        repo = self.rapi.create('large-sync','some name', 'i386')
        numpacks = 5000
        for x in range(numpacks):
            self.rapi._add_package(repo, self.create_random_package())
            if (x % 100 == 0):
                print "Created [%s] packages" % x
        print "Updating repo"
        self.rapi.update(repo)
        self.assertTrue(numpacks, self.rapi.packages(repo['id']))

    def create_package(self, name): 
        test_pkg_name = name
        test_epoch = "1"
        test_version = "1.2.3"
        test_release = "1.el5"
        test_arch = "x86_64"
        test_description = "zzz test description text zzz"
        test_checksum_type = "sha256"
        test_checksum = "9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e"
        test_filename = "test-filename-zzz-1.2.3-1.el5.x86_64.rpm"
        p = self.papi.create(name=test_pkg_name, epoch=test_epoch, version=test_version, 
                release=test_release, arch=test_arch, description=test_description, 
                checksum_type="sha256", checksum=test_checksum, filename=test_filename)
        lookedUp = self.papi.package(p['id'])
        return lookedUp
      
    
          
    def create_random_package(self):
        test_pkg_name = random_string()
        test_epoch = random.randint(0,2)
        test_version = "%s.%s.%s" % (random.randint(0,100), 
                                random.randint(0,100), random.randint(0,100))
        test_release = "%s.el5" % random.randint(0, 10)
        test_arch = "x86_64"
        test_description = ""
        test_requires = []
        test_provides = []
        for x in range(10):
            test_description = test_description + " " + random_string()
            test_requires.append(random_string())
            test_provides.append(random_string())
            
        test_checksum_type = "sha256"
        test_checksum = "9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e"
        test_filename = "test-filename-zzz-%s-%s.x86_64.rpm" % (test_version, test_release)
        p = self.papi.create(name=test_pkg_name, epoch=test_epoch, version=test_version, 
                release=test_release, arch=test_arch, description=test_description, 
                checksum_type="sha256", checksum=test_checksum, filename=test_filename)
        p['requires'] = test_requires
        p['provides'] = test_requires
        self.papi.update(p)
        return p
        
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
        self.assertTrue(len(repo["packages"][p['id']]) is not None)
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
        self.assertTrue(pkgs[packageid] is not None)
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
        self.papi.delete(found[0]["_id"])
        # Verify it's deleted
        found = self.papi.packages(name=test_pkg_name, epoch=test_epoch, 
                version=test_version, release=test_release, arch=test_arch, 
                filename=test_filename, checksum_type=test_checksum_type,
                checksum=test_checksum)
        self.assertTrue(len(found) == 0)
        # Check nothing returned in search with no params
        all = self.papi.packages()
        self.assertTrue(len(all) == 0)
        
        
        
if __name__ == '__main__':
    unittest.main()
