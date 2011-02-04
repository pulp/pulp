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
from pulp.server.api.keystore import KeyStore
from pulp.server.api.errata import ErrataApi
from pulp.server.auth.certificate import Certificate
from pulp.server.db.model import PackageGroup
from pulp.server.db.model import PackageGroupCategory
from pulp.server.db.model import Consumer
from pulp.server.db.model import RepoSource
from pulp.server.util import random_string
from pulp.server.util import get_rpm_information
from pulp.client.utils import generatePakageProfile
from pulp.server.util import top_repos_location
from pulp.server.auth import cert_generator
from pulp.server.auth.cert_generator import SerialNumber
from pulp.server import constants
import testutil

logging.root.setLevel(logging.ERROR)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

SerialNumber.PATH = '/tmp/sn.dat'
constants.LOCAL_STORAGE="/tmp/pulp/"

class TestApi(unittest.TestCase):

    def clean(self):
        self.rapi.clean()
        self.papi.clean()
        self.capi.clean()
        self.cgapi.clean()
        self.eapi.clean()
        testutil.common_cleanup()
        sn = SerialNumber()
        sn.reset()

    def setUp(self):
        self.config = testutil.load_test_config()
        self.data_path = \
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
        self.rapi = RepoApi()
        self.papi = PackageApi()
        self.capi = ConsumerApi()
        self.cgapi = ConsumerGroupApi()
        self.eapi = ErrataApi()
        self.clean()

    def tearDown(self):
        self.clean()

    def test_create(self):
        repo = self.rapi.create('some-id', 'some name',
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
            repo = self.rapi.create('some-id', 'some name',
                'i386', 'invalidtype:http://example.com/')
        except:
            failed = True
        assert(failed)

        try:
            repo = self.rapi.create('some-id', 'some name',
                'i386', 'blippybloopyfoo')
        except:
            failed = True
        assert(failed)


        repo = self.rapi.create('some-id', 'some name',
            'i386', 'yum:http://example.com')
        assert(repo is not None)
        assert(repo['source']['type'] == 'yum')

    def test_repo_update(self):
        repo = self.rapi.create('some-id', 'some name',
            'i386', 'yum:http://example.com')
        assert(repo is not None)
        assert(repo['source']['type'] == 'yum')
        repo['feed'] = 'yum:http://example2.com'
        self.rapi.update(repo)
        repo = self.rapi.repository(repo['id'])
        print "Repo source: %s" % repo['source']
        assert(repo['source']['url'] == 'http://example2.com')
        
    def test_clean(self):
        repo = self.rapi.create('some-id', 'some name',
            'i386', 'yum:http://example.com')
        self.rapi.clean()
        repos = self.rapi.repositories()
        assert(len(repos) == 0)

    def test_delete(self):
        id = 'some-id'
        repo = self.rapi.create(id, 'some name', 'i386', 'yum:http://example.com')
        repo = self.rapi.repository(id)
        assert(repo is not None)
        self.rapi.delete(id=id)
        repo = self.rapi.repository(id)
        assert(repo is None)

    def test_delete_feedless(self):
        id = 'some-id-no-feed'
        repo = self.rapi.create(id, 'some name', 'i386')
        repo = self.rapi.repository(id)
        assert(repo is not None)
        self.rapi.delete(id=id)
        repo = self.rapi.repository(id)
        assert(repo is None)

    def test_repositories(self):
        repo = self.rapi.create('some-id', 'some name',
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
        repo = self.rapi.create('some-id', 'some name', \
            'i386', 'yum:http://example.com')

        found = self.rapi.repository('some-id')
        assert(found is not None)
        assert(found['id'] == 'some-id')

    def test_repository_with_groupid(self):
        repo = self.rapi.create('some-id', 'some name', \
            'i386', 'yum:http://example.com/mypath', groupid=["testgroup"])
        found = self.rapi.repository('some-id')
        assert(found is not None)
        assert(found['id'] == 'some-id')
        assert(found['groupid'] == ["testgroup"])

    def test_repository_with_relativepath(self):
        repo = self.rapi.create('some-id-mypath', 'some name', \
            'i386', 'yum:http://example.com/mypath', relative_path="/mypath/")
        found = self.rapi.repository('some-id-mypath')
        assert(found is not None)
        assert(found['id'] == 'some-id-mypath')
        assert(found['relative_path'] == "mypath")

        # default path
        repo = self.rapi.create('some-id-default-path', 'some name', \
            'i386', 'yum:http://example.com/mypath')
        found = self.rapi.repository('some-id-default-path')
        assert(found is not None)
        assert(found['id'] == 'some-id-default-path')
        assert(found['relative_path'] == "mypath")

    def test_consumer_group(self):
        print "Consumer group tests:"
        cg = self.cgapi.create('some-id', 'some description')

        found = self.cgapi.consumergroup('some-id')
        assert(found is not None)
        print found['description']
        assert(found['id'] == 'some-id')

        found = self.cgapi.consumergroup('some-id-that-doesnt-exist')
        assert(found is None)

    def test_repo_packages(self):
        repo = self.rapi.create('some-id', 'some name', \
            'i386', 'yum:http://example.com')
        p = testutil.create_package(self.papi, 'test_repo_packages')
        self.rapi.add_package(repo["id"], [p['id']])
        for i in range(10):
            package = testutil.create_package(self.papi, random_string())
            self.rapi.add_package(repo["id"], [package['id']])

        found = self.rapi.repository('some-id')
        packages = found['packages']
        assert(packages is not None)
        assert(p['id'] in packages)

    def test_repo_package_count(self):
        repo = self.rapi.create('some-id', 'some name', \
            'i386', 'yum:http://example.com')
        num_packages = 50
        package = None
        for i in range(num_packages):
            package = testutil.create_package(self.papi, random_string())
            self.rapi.add_package(repo["id"], [package['id']])

        count = self.rapi.package_count('some-id')
        self.assertTrue(num_packages == count)
        self.rapi.remove_package('some-id', package)
        count = self.rapi.package_count('some-id')
        self.assertTrue(count == (num_packages - 1))
        

    def test_repo_erratum(self):
        repo = self.rapi.create('some-id', 'some name', \
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

    def test_repo_gpgkeys(self):
        id = 'fedora'
        relativepath = 'f11/i386'
        feed = 'yum:http://abc.com/%s' % relativepath
        repo = self.rapi.create(id, 'Fedora', 'noarch', feed=feed)
        keyA = ('keyA', 'MY KEY (A) CONTENT')
        keyB = ('keyB', 'MY KEY (B) CONTENT')
        keylist = [keyA, keyB]
        ks = KeyStore(relativepath)
        ks.clean()
        # multiple (2) keys
        self.rapi.addkeys(id, keylist)
        found = self.rapi.listkeys(id)
        for i in range(0, len(keylist)):
            path = os.path.join(relativepath, keylist[i][0])
            self.assertTrue(path in found)
        # single key
        ks.clean()
        self.rapi.addkeys(id, keylist[1:])
        found = self.rapi.listkeys(id)
        path = os.path.join(relativepath, keylist[1][0])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0], path)

    def test_repo_update(self):
        id = 'fedora'
        relativepath = 'f11/i386'
        feed = 'yum:http://abc.com/%s' % relativepath
        repo = self.rapi.create(id, 'Fedora', 'noarch', feed=feed)
        d = dict(id=id, feed='yum:http://xyz.com')
        repo = self.rapi.update(d)
        d = dict(id=id, use_symlinks=True)
        repo = self.rapi.update(d)
        d = dict(id=id, relative_path='/bla/bla')
        repo = self.rapi.update(d)
        root = top_repos_location()
        # add some phony content and try again
        path = os.path.join(root, repo['relative_path'])
        if not os.path.exists(path):
            os.makedirs(path)
        f = open(os.path.join(path, 'package'), 'w')
        f.close()
        try:
            d = dict(id=id, feed='yum:http://xyz.com/my/new/path')
            repo = self.rapi.update(d)
            self.assertTrue(False, 'should fail')
        except:
            pass
        try:
            d = dict(id=id, use_symlinks=False)
            repo = self.rapi.update(d)
            self.assertTrue(False, 'should fail')
        except:
            pass
        try:
            d = dict(id=id, relative_path='/bla/bla')
            repo = self.rapi.update(d)
            self.assertTrue(False, 'should fail')
        except:
            pass

    def test_repo_errata(self):
        repo = self.rapi.create('some-id', 'some name', \
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
        repo = self.rapi.create('some-id', 'some name', \
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
        self.rapi.add_package(repo["id"], [p['id']])
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

        pkguplist = self.capi.list_package_updates(c['id'])['packages']
        assert(len(pkguplist) == 1)

    def test_repo_package_groups(self):
        repo = self.rapi.create('some-id', 'some name', \
            'i386', 'yum:http://example.com')
        pkggroup = self.rapi.create_packagegroup(repo["id"],
                'test-group-id', 'test-group-name',
                'test-group-description')
        package = testutil.create_package(self.papi, 'test_repo_packages')
        self.rapi.add_package(repo["id"], [package["id"]])
        self.rapi.add_packages_to_group(repo["id"], pkggroup["id"],
                [package["name"]], gtype="default")
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
        repo = self.rapi.create('some-id_pkg_group_categories', 'some name', \
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

    def test_consumer_delete(self):
        # Setup
        id = 'delete-me'
        self.capi.create(id, '')
        self.assertTrue(self.capi.consumer(id) is not None)

        # Test
        self.capi.delete(id)

        # Verify
        self.assertTrue(self.capi.consumer(id) is None)
        
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
        packagenames = ['A', 'B', 'C']
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
            package = testutil.create_package(self.papi, randName)
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
        repo = self.rapi.create('some-id', 'some name',
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
        repo_a = self.rapi.create(repo_name_a, 'some name', 'x86_64',
                                  'local:file://%s' % datadir_a)
        repo_b = self.rapi.create(repo_name_b, 'some name', 'x86_64',
                                'local:file://%s' % datadir_b)
        self.rapi._sync(repo_a["id"])
        self.rapi._sync(repo_b["id"])

        # This will get fixed when we move the async nature of sync down into
        # the API layer

        time.sleep(5)

        # Look up each repo from API
        found_a = self.rapi.repository(repo_a['id'])
        found_b = self.rapi.repository(repo_b['id'])

        # Verify each repo has the test package synced
        found_a_pid = None
        for pkg_id in found_a["packages"]:
            p = self.papi.package(pkg_id)
            if (p['name'].index(test_pkg_name) >= 0):
                found_a_pid = p['id']
        assert(found_a_pid is not None)

        found_b_pid = None
        for pkg_id in found_b["packages"]:
            p = self.papi.package(pkg_id)
            if (p['name'].index(test_pkg_name) >= 0):
                found_b_pid = p['id']
        assert(found_b_pid is not None)


        packagea = self.papi.package(found_a_pid)
        packageb = self.papi.package(found_b_pid)

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
        repo_a = self.rapi.create(repo_name_a, 'some name', 'x86_64',
                                'local:file://%s' % datadir_a)
        repo_b = self.rapi.create(repo_name_b, 'some name', 'x86_64',
                                'local:file://%s' % datadir_b)
        self.rapi._sync(repo_a['id'])
        self.rapi._sync(repo_b['id'])
        # Look up each repo from API
        found_a = self.rapi.repository(repo_a['id'])
        found_b = self.rapi.repository(repo_b['id'])
        # Verify each repo has the test package synced
        # Verify each repo has the test package synced
        found_a_pid = None
        for pkg_id in found_a["packages"]:
            p = self.papi.package(pkg_id)
            if (p['name'].index(test_pkg_name) >= 0):
                found_a_pid = p['id']
        assert(found_a_pid is not None)

        found_b_pid = None
        for pkg_id in found_b["packages"]:
            p = self.papi.package(pkg_id)
            if (p['name'].index(test_pkg_name) >= 0):
                found_b_pid = p['id']
        assert(found_b_pid is not None)
        packagea = self.papi.package(found_a_pid)
        packageb = self.papi.package(found_b_pid)

        # Ensure that the 2 Package instances actually point 
        # to the same single instance
        assert(repo_a['_id'] != repo_b['_id'])
        assert(packagea['_id'] == packageb['_id'])

    def test_sync(self):
        p = os.path.join(self.data_path, "repo_resync_a")
        repo = self.rapi.create('some-id', 'some name', 'i386',
                'local:%s' % (p))
        failed = False
        try:
            self.rapi._sync('invalid-id-not-found')
        except Exception:
            failed = True
        assert(failed)

        self.rapi._sync(repo['id'])

        # Check that local storage has dir and rpms
        d = os.path.join(top_repos_location(), repo['relative_path'])
        self.assertTrue(os.path.isdir(d))
        dirList = os.listdir(d)
        assert(len(dirList) > 0)
        found = self.rapi.repository(repo['id'])
        packages = found['packages']
        assert(packages is not None)
        assert(len(packages) > 0)

    def resync_removes_deleted_package(self):
        # Since a repo with 3 packages, simulate the repo source deleted 1 package
        # Re-sync ensure we delete the removed package
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        r = self.rapi.create('test_resync_removes_deleted_package',
                'test_name', 'x86_64', 'local:file://%s' % (repo_path))
        self.assertTrue(r != None)
        self.rapi._sync(r["id"])
        # Refresh object now it's been sync'd
        r = self.rapi.repository(r['id'])
        self.assertTrue(len(r["packages"]) == 3)
        expected_packages = ["pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm",
                "pulp-test-package-0.2.1-1.fc11.x86_64.rpm",
                "pulp-test-package-0.3.1-1.fc11.x86_64.rpm"]
        for ep in expected_packages:
            found = False
            for pkg_id in r["packages"]:
                p = self.papi.package(pkg_id)
                if p["filename"] == ep:
                    found = True
            self.assertTrue(found)
        # Simulate a change that a package was deleted
        repo_path = os.path.join(self.data_path, "repo_resync_b")
        r = self.rapi.repository(r["id"])
        r["source"] = RepoSource("local:file://%s" % (repo_path))
        self.rapi.update(r)
        self.rapi._sync(r["id"])
        #Refresh Repo Object and Verify Changes
        r = self.rapi.repository(r["id"])
        self.assertTrue(len(r["packages"]) == 2)
        removed_package = "pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm"
        expected_packages = ["pulp-test-package-0.2.1-1.fc11.x86_64.rpm",
                "pulp-test-package-0.3.1-1.fc11.x86_64.rpm"]
        for ep in expected_packages:
            found = False
            for pkg_id in r["packages"]:
                p = self.papi.package(pkg_id)
                if p["filename"] == ep:
                    found = True
            self.assertTrue(found)
        for pkg_id in r["packages"]:
            p = self.papi.package(pkg_id)
            self.assertTrue(p["filename"] != removed_package)

    def disabled_resync_removes_deleted_package_with_two_pkgs_same_nevra(self):
        # Assume we have 2 packages in pulp with same NEVRA
        # 1 of those packages is in a repo
        # the repo is re-synced and that package is not present
        # We need to ensure the package previously associated to the repo
        # is removed and verify the other pkg with same NEVRA info but never
        # part of this repo still exists in pulp
        self.assertTrue(False)

    def test_sync_feedless(self):
        repo = self.rapi.create('some-id-no-feed', 'some name', 'i386')
        # verify repo without feed is not syncable
        failed = False
        try:
            self.rapi._sync(repo['id'])
        except Exception:
            # raises a PulpException
            # 'This repo is not setup for sync. Please add packages using upload.'
            failed = True
        assert(failed)

    def test_local_sync(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir = my_dir + "/data/"
        repo = self.rapi.create('some-id', 'some name', 'i386',
                                'local:file://%s' % datadir)

        self.rapi._sync(repo['id'])
        found = self.rapi.repository(repo['id'])
        packages = found['packages']
        assert(packages is not None)
        assert(len(packages) > 0)
        p = packages[0]
        assert(p is not None)
        # versions = p['versions']


    def test_local_sync_with_exception(self):
        # We need report to be accesible for writing by the callback
        global report
        report = None
        def callback(r):
            global report
            report = r
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir = my_dir + "/data/repo_with_bad_read_perms/"
        repo = self.rapi.create('some-id', 'some name', 'i386',
                                'local:file://%s' % datadir)
        self.rapi._sync(repo['id'], progress_callback=callback)
        found = self.rapi.repository(repo['id'])
        packages = found['packages']
        self.assertTrue(packages is not None)
        self.assertTrue(len(packages) == 2)
        self.assertTrue(report["items_total"] - report["num_success"] == 2)
        self.assertTrue(report["num_error"] == 2)
        self.assertTrue(report["error_details"] is not None)
        self.assertTrue(len(report["error_details"]) == 2)
        #error_details is a list of tuples
        #Packages are processed first, so [0] will be the package error and [1] with be the tree error
        #tuple[0] is the item info dictionary
        #tuple[1] is the error info dictionary
        self.assertTrue("pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm" in report["error_details"][0][0]["fileName"])
        self.assertTrue("Permission denied" in report["error_details"][0][1]["exc_value"])
        self.assertTrue("file3.img" in report["error_details"][1][0]["fileName"])
        self.assertTrue("Permission denied" in report["error_details"][1][1]["exc_value"])

    def test_find_repos_by_package(self):
        # Goal is to search by errata id and discover the repos
        # which contain the errata.
        #
        # Sync 2 repos with same content local feed
        datadir = os.path.join(self.data_path, "sameNEVRA_differentChecksums/A/repo")
        r = self.rapi.create("test_find_repos_by_package", "test_name", "x86_64",
                "local:file://%s" % datadir)
        self.rapi._sync(r['id'])
        datadir = os.path.join(self.data_path, "sameNEVRA_differentChecksums/B/repo")
        r2 = self.rapi.create("test_find_repos_by_package_2", "test_name_2", "x86_64",
                "local:file://%s" % datadir)
        self.rapi._sync(r2['id'])
        # Refresh object now it's been sync'd
        r = self.rapi.repository(r['id'])
        r2 = self.rapi.repository(r2['id'])

        # Test for known pkgid
        self.assertTrue(len(r["packages"]) == 1)
        self.assertTrue(len(r2["packages"]) == 1)
        pkgid1 = r["packages"][0]
        pkgid2 = r2["packages"][0]

        found = self.rapi.find_repos_by_package(pkgid1)
        self.assertTrue(len(found) == 1)
        self.assertTrue(r["id"] in found)
        found = self.rapi.find_repos_by_package(pkgid2)
        self.assertTrue(len(found) == 1)
        self.assertTrue(r2["id"] in found)
    
    def test_repo_package_by_name(self):
        repo = self.rapi.create('some-id', 'some name', \
            'i386', 'yum:http://example.com')
        p = testutil.create_package(self.papi, 'test_pkg_by_name', version="1")
        self.rapi.add_package(repo["id"], [p['id']])
        
        p2 = testutil.create_package(self.papi, 'test_pkg_by_name', version="2")
        self.rapi.add_package(repo["id"], [p2['id']])

        pkgs = self.rapi.get_packages_by_name(repo['id'], p['name'])
        self.assertTrue(len(pkgs) == 2)
        self.assertTrue(p["id"] in pkgs)
        self.assertTrue(p2["id"] in pkgs)
        
        pkgs = self.rapi.get_packages_by_name(repo['id'], "bad_name")
        self.assertTrue(len(pkgs) == 0)


    def test_get_packages_by_id(self):
        repo = self.rapi.create('some-id', 'some name', \
            'i386', 'yum:http://example.com')
        repo2 = self.rapi.create('some-id-2', 'some name 2', \
            'i386', 'yum:http://example.com-2')
        p1 = testutil.create_package(self.papi, 'test_pkg_by_name')
        self.rapi.add_package(repo["id"], [p1['id']])

        p2 = testutil.create_package(self.papi, 'test_pkg2_by_name')
        self.rapi.add_package(repo2["id"], [p2['id']])

        pkgs = self.rapi.get_packages_by_id(repo['id'], [p1['id']])
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(p1["id"] in pkgs)

        pkgs = self.rapi.get_packages_by_id(repo2['id'], [p2['id']])
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(p2["id"] in pkgs)

        pkgs = self.rapi.get_packages_by_id(repo2['id'], [p1['id']])
        self.assertTrue(len(pkgs) == 0)

    def test_get_packages_by_filename(self):
        repo = self.rapi.create('some-id', 'some name', \
            'i386', 'yum:http://example.com')
        repo2 = self.rapi.create('some-id-2', 'some name 2', \
            'i386', 'yum:http://example.com-2')
        p1 = testutil.create_package(self.papi, 'test_pkg_by_name', filename="test01.rpm")
        self.rapi.add_package(repo["id"], [p1['id']])

        p2 = testutil.create_package(self.papi, 'test_pkg2_by_name', filename="test02.rpm")
        self.rapi.add_package(repo2["id"], [p2['id']])
        
        pkgs = self.rapi.get_packages_by_filename(repo['id'], [p1['filename']])
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(p1["id"] in pkgs)

        pkgs = self.rapi.get_packages_by_filename(repo2['id'], [p2['filename']])
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(p2["id"] in pkgs)
        
        pkgs = self.rapi.get_packages_by_filename(repo2['id'], [p1['filename']])
        self.assertTrue(len(pkgs) == 0)

        pkgs = self.rapi.get_packages_by_id(repo2['id'], [])
        self.assertTrue(len(pkgs) == 0)
        
        pkgs = self.rapi.get_packages_by_id(repo2['id'], ["bad_name"])
        self.assertTrue(len(pkgs) == 0)
        
    def test_packages(self):
        repo = self.rapi.create('some-id', 'some name', \
            'i386', 'yum:http://example.com')
        p1 = testutil.create_package(self.papi, 'test_pkg_by_name', filename="test01.rpm")
        self.rapi.add_package(repo["id"], [p1['id']])

        p2 = testutil.create_package(self.papi, 'test_pkg2_by_name', filename="test02.rpm")
        self.rapi.add_package(repo["id"], [p2['id']])
       
        #Create a similar package but dont add to repo
        p3 = testutil.create_package(self.papi, 'test_pkg_by_name', filename="test03.rpm")
        
        pkgs = self.rapi.packages(repo['id'])
        self.assertTrue(len(pkgs) == 2)
        self.assertTrue(p1["id"] in pkgs)
        self.assertTrue(p2["id"] in pkgs)
        
        pkgs = self.rapi.packages(repo['id'], name=p1['name'])
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(p1["id"] in pkgs)
        
        pkgs = self.rapi.packages(repo['id'], filename=p2['filename'])
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(p2["id"] in pkgs)
        
        pkgs = self.rapi.packages(repo['id'], version=p1['version'])
        self.assertTrue(len(pkgs) == 2)
        self.assertTrue(p1["id"] in pkgs)
        self.assertTrue(p2["id"] in pkgs)
        
        pkgs = self.rapi.packages(repo['id'], name="bad_name")
        self.assertTrue(len(pkgs) == 0)

if __name__ == '__main__':
    unittest.main()
