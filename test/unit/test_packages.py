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

from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.util import random_string
from pulp.server.util import get_rpm_information
import testutil

logging.root.setLevel(logging.ERROR)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

class TestApi(unittest.TestCase):

    def clean(self):
        self.rapi.clean()
        self.papi.clean()
        testutil.common_cleanup()

    def setUp(self):
        self.config = testutil.load_test_config()
        self.data_path = \
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
        self.rapi = RepoApi()
        self.papi = PackageApi()
        self.clean()

    def tearDown(self):
        self.clean()

    def test_package_search(self):
        # Create multiple packages
        pkgs = []
        pkgs.append(testutil.create_package(self.papi, name="xwindows"))
        pkgs.append(testutil.create_package(self.papi, name="gvim"))
        pkgs.append(testutil.create_package(self.papi, name="apache"))
        pkgs.append(testutil.create_package(self.papi, name="vim-enhanced"))
        pkgs.append(testutil.create_package(self.papi, name="vim-minimal"))
        pkgs.append(testutil.create_package(self.papi, name="amanda"))
        pkgs.append(testutil.create_package(self.papi, name="emacs"))
        # Verify we can search for them with basic terms
        for pkg in pkgs:
            self.assertTrue(self.papi.package(pkg["id"]) != None)
        # Verify regex search works
        result = self.papi.packages(name="vim")
        self.assertTrue(not result)
        result = self.papi.packages(name="vim", regex=True)
        self.assertTrue(result)

        result = self.papi.packages(name="\w+ed", regex=False)
        self.assertTrue(len(result) == 0)
        result = self.papi.packages(name="\w+ed", regex=True)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0]["name"] == "vim-enhanced")

    def test_packages(self):
        repo = self.rapi.create('some-id', 'some name',
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
        self.rapi.add_package(repo["id"],[p['id']])
        # Lookup repo and confirm new package version was added
        repo = self.rapi.repository(repo["id"])
        self.assertTrue(p['id'] in repo["packages"])
        packageid = p['id']
        saved_pkg = self.papi.package(p['id'])
        self.assertTrue(saved_pkg)
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
        pkgs = self.rapi.packages(repo['id'], name=test_pkg_name)
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(pkgs[packageid]["id"] == packageid)
        self.assertTrue(pkgs[packageid]['filename'] == test_filename)

        # Remove package from repo
        self.rapi.remove_package(repo['id'], p)
        repo = self.rapi.repository(repo['id'])
        self.assertTrue(p['id'] not in repo["packages"])
        # Verify package has been removed from repo and since
        # no other repos were referencing it, the package has been removed
        # from the package collection as well
        found = self.papi.packages(name=test_pkg_name, epoch=test_epoch,
                version=test_version, release=test_release, arch=test_arch,
                filename=test_filename, checksum_type=test_checksum_type,
                checksum=test_checksum)
        self.assertTrue(len(found) == 0)

    def test_find_repos_by_package(self):
        repo_a = self.rapi.create('some-id_a', 'some name',
            'i386', 'yum:http://example.com')
        repo_b = self.rapi.create('some-id_b', 'some name',
            'i386', 'yum:http://example.com')
        repo_a = self.rapi.repository(repo_a["id"])
        repo_b = self.rapi.repository(repo_b["id"])
        pkg1 = testutil.create_random_package(self.papi)
        pkg2 = testutil.create_random_package(self.papi)
        pkg3 = testutil.create_random_package(self.papi)
        self.rapi.add_package(repo_a["id"], [pkg1["id"]])
        self.rapi.add_package(repo_a["id"], [pkg2["id"]])
        self.rapi.add_package(repo_b["id"], [pkg1["id"]])

        found = self.rapi.repository(repo_a["id"])
        self.assertTrue(pkg1["id"] in found["packages"])
        self.assertTrue(pkg2["id"] in found["packages"])
        self.assertTrue(pkg3["id"] not in found["packages"])

        found = self.rapi.repository(repo_b["id"])
        self.assertTrue(pkg1["id"] in found["packages"])

        found = self.rapi.find_repos_by_package(pkg1["id"])
        self.assertTrue(len(found) == 2)
        self.assertTrue(repo_a["id"] in found)
        self.assertTrue(repo_b["id"] in found)

    def test_find_orphaned_packages(self):
        repo_a = self.rapi.create('some-id_a', 'some name',
            'i386', 'yum:http://example.com')
        repo_b = self.rapi.create('some-id_b', 'some name',
            'i386', 'yum:http://example.com')
        repo_a = self.rapi.repository(repo_a["id"])
        repo_b = self.rapi.repository(repo_b["id"])
        #Create 5 test packages, associte 3 to repos
        #2 of them should be orphaned packages
        pkg1 = testutil.create_random_package(self.papi)
        pkg2 = testutil.create_random_package(self.papi)
        pkg3 = testutil.create_random_package(self.papi)
        pkg4 = testutil.create_random_package(self.papi)
        pkg5 = testutil.create_random_package(self.papi)
        self.rapi.add_package(repo_a["id"], [pkg1["id"]])
        self.rapi.add_package(repo_a["id"], [pkg2["id"]])
        self.rapi.add_package(repo_b["id"], [pkg1["id"]])
        self.rapi.add_package(repo_b["id"], [pkg3["id"]])

        orphans = self.papi.orphaned_packages()
        self.assertTrue(len(orphans) == 2)
        orphan_ids = [x["id"] for x in orphans]
        self.assertTrue(pkg4["id"] in orphan_ids)
        self.assertTrue(pkg5["id"] in orphan_ids)


if __name__ == '__main__':
    unittest.main()
