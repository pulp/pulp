#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

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

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import pymongo.json_util
from pulp.server.exceptions import PulpException
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.util import random_string
from pulp.server.util import get_rpm_information
from pulp.server.util import RegularExpressionError

logging.root.setLevel(logging.ERROR)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

class TestApi(testutil.PulpAsyncTest):

    def test_package_search(self):
        # Create multiple packages
        pkgs = []
        pkgs.append(testutil.create_package(self.package_api, name="xwindows"))
        pkgs.append(testutil.create_package(self.package_api, name="gvim"))
        pkgs.append(testutil.create_package(self.package_api, name="apache"))
        pkgs.append(testutil.create_package(self.package_api, name="vim-enhanced"))
        pkgs.append(testutil.create_package(self.package_api, name="vim-minimal"))
        pkgs.append(testutil.create_package(self.package_api, name="amanda"))
        pkgs.append(testutil.create_package(self.package_api, name="emacs"))
        # Verify we can search for them with basic terms
        for pkg in pkgs:
            self.assertTrue(self.package_api.package(pkg["id"]) != None)
        # Verify regex search works
        result = self.package_api.packages(name="vim")
        self.assertTrue(not result)
        result = self.package_api.packages(name="vim", regex=True)
        self.assertTrue(result)

        result = self.package_api.packages(name="\w+ed", regex=False)
        self.assertTrue(len(result) == 0)
        result = self.package_api.packages(name="\w+ed", regex=True)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0]["name"] == "vim-enhanced")

    def test_package_regexes(self):
        # Create multiple packages
        pkgs = []
        pkgs.append(testutil.create_package(self.package_api, name="xwindows", version="1.2.3", arch="x86_64"))
        pkgs.append(testutil.create_package(self.package_api, name="emacs", version="1.2.3", epoch='2', arch="x86_64"))
        pkgs.append(testutil.create_package(self.package_api, name="emacs", version="2.3.4", release="1.fc13", arch="i386"))
        pkgs.append(testutil.create_package(self.package_api, name="emacs", version="3.4.5", release="1.fc13", arch="x86_64"))

        # Verify we can search for them with basic terms
        for pkg in pkgs:
            self.assertTrue(self.package_api.package(pkg["id"]) != None)

        # name
        result = self.package_api.packages(name="^emac", regex=True)
        self.assertTrue(len(result) == 3)

        # filename
        result = self.package_api.packages(filename="random", regex=True)
        self.assertTrue(len(result) == 0)

        # version
        result = self.package_api.packages(version="3.4", regex=True)
        self.assertTrue(len(result) == 2)

        # epoch
        result = self.package_api.packages(epoch="^2", regex=True)
        self.assertTrue(len(result) == 1)

        # release
        result = self.package_api.packages(release="fc13", regex=True)
        self.assertTrue(len(result) == 2)

        # arch
        result = self.package_api.packages(arch="^x86", regex=True)
        self.assertTrue(len(result) == 3)

        # checksum
        result = self.package_api.packages(checksum_type="sha256", checksum="^9d05cc3dbdc94", regex=True)
        self.assertTrue(len(result) == 4)

    def test_package_invalid_regex(self):

        pkgs = []
        pkgs.append(testutil.create_package(self.package_api, name="xwindows", version="1.2.3", arch="x86_64"))
        self.assertRaises(RegularExpressionError, 
            self.package_api.packages, version="*.2.3", regex=True)


    def test_package_dependency(self):
        repo = self.repo_api.create('some-id', 'some name',
                                'i386', 'http://example.com')
        repo = self.repo_api.repository(repo["id"])
        test_pkg_name = "test_package_versions_name"
        test_epoch = "1"
        test_version = "1.2.3"
        test_release = "1.el5"
        test_arch = "x86_64"
        test_description = "test description text"
        test_checksum_type = "sha256"
        test_checksum = "9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e"
        test_filename = "test-filename-1.2.3-1.el5.x86_64.rpm"
        p = self.package_api.create(name=test_pkg_name, epoch=test_epoch, version=test_version,
                release=test_release, arch=test_arch, description=test_description,
                checksum_type="sha256", checksum=test_checksum, filename=test_filename)
        result = self.package_api.package_dependency(["test_package_versions_name"], ["some-id"])
        self.assertTrue(result['printable_dependency_result'] == '')
        result = self.package_api.package_dependency(["test_package_versions_name"], ["some-id"], recursive=1)
        self.assertTrue(result['printable_dependency_result'] == '')


    def test_package_filenames_descriptions(self):
        testutil.create_package(self.package_api, name="xwindows", version="1.2.3", arch="x86_64")
        testutil.create_package(self.package_api, name="emacs", version="1.2.3", epoch='2', arch="x86_64")
        testutil.create_package(self.package_api, name="emacs", version="2.3.4", release="1.fc13", arch="i386")
        testutil.create_package(self.package_api, name="emacs", version="3.4.5", release="1.fc13", arch="x86_64")

        result = self.package_api.package_filenames({"name":"emacs", "release":"1.fc13"})
        self.assertTrue(len(result) == 2)

        result = self.package_api.package_descriptions({"name":"emacs", "release":"1.fc13"})
        self.assertTrue(len(result) == 2)

    def test_package_cheksums(self):
        testutil.create_package(self.package_api, name="xwindows", version="1.2.3", arch="x86_64")
        testutil.create_package(self.package_api, name="emacs", version="1.2.3", epoch='2', arch="x86_64")
        testutil.create_package(self.package_api, name="emacs", version="2.3.4", release="1.fc13", arch="i386", filename="my-filename-1.2.3-1.el5.x86_64.rpm")
        testutil.create_package(self.package_api, name="emacs", version="3.4.5", release="1.fc13", arch="x86_64", filename="my-filename-1.2.3-1.el5.x86_64.rpm")

        result = self.package_api.get_package_checksums(filenames=['my-filename-1.2.3-1.el5.x86_64.rpm'])
        self.assertTrue(len(result) == 1)
        self.assertTrue(len(result["my-filename-1.2.3-1.el5.x86_64.rpm"]) == 2)

        result = self.package_api.package_checksum(filename='my-filename-1.2.3-1.el5.x86_64.rpm')
        self.assertTrue(len(result) == 2)

    def test_packages(self):
        repo = self.repo_api.create('some-id', 'some name',
            'i386', 'http://example.com')
        repo = self.repo_api.repository(repo["id"])
        test_pkg_name = "test_package_versions_name"
        test_epoch = "1"
        test_version = "1.2.3"
        test_release = "1.el5"
        test_arch = "x86_64"
        test_description = "test description text"
        test_checksum_type = "sha256"
        test_checksum = "9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e"
        test_filename = "test-filename-1.2.3-1.el5.x86_64.rpm"
        p = self.package_api.create(name=test_pkg_name, epoch=test_epoch, version=test_version,
                release=test_release, arch=test_arch, description=test_description,
                checksum_type="sha256", checksum=test_checksum, filename=test_filename)
        print "Package! %s" % p
        # Add this package version to the repo
        self.repo_api.add_package(repo["id"],[p['id']])
        # Lookup repo and confirm new package version was added
        repo = self.repo_api.repository(repo["id"])
        self.assertTrue(p['id'] in repo["packages"])
        packageid = p['id']
        saved_pkg = self.package_api.package(p['id'])
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
        pkgs = self.repo_api.packages(repo['id'], name=test_pkg_name)
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(pkgs[packageid]["id"] == packageid)
        self.assertTrue(pkgs[packageid]['filename'] == test_filename)

        # Remove package from repo
        self.repo_api.remove_package(repo['id'], saved_pkg)
        repo = self.repo_api.repository(repo['id'])
        self.assertTrue(p['id'] not in repo["packages"])

    def test_nonexistent_package_update(self):
        try:
            self.package_api.update("nonexisting_id", {})
            assertTrue(False)
        except PulpException:
            pass

    def test_wrong_delta_keyvalue(self):
        test_pkg_name = "test_package_versions_name"
        test_epoch = "1"
        test_version = "1.2.3"
        test_release = "1.el5"
        test_arch = "x86_64"
        test_description = "test description text"
        test_checksum_type = "sha256"
        test_checksum = "9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e"
        test_filename = "test-filename-1.2.3-1.el5.x86_64.rpm"
        test_group = "Application"
        test_license = "GPL"
        test_buildhost = "test.example.com"
        test_size = 22456
        p = self.package_api.create(name=test_pkg_name, epoch=test_epoch, version=test_version,
                release=test_release, arch=test_arch, description=test_description,
                checksum_type="sha256", checksum=test_checksum, filename=test_filename)
        try:
            self.package_api.update(p['id'], {"random-key":"random-value"})
            self.assertTrue(False)
        except:
            pass

    def test_package_fields(self):
        repo = self.repo_api.create('some-id', 'some name',
            'i386', 'http://example.com')
        repo = self.repo_api.repository(repo["id"])
        test_pkg_name = "test_package_versions_name"
        test_epoch = "1"
        test_version = "1.2.3"
        test_release = "1.el5"
        test_arch = "x86_64"
        test_description = "test description text"
        test_checksum_type = "sha256"
        test_checksum = "9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e"
        test_filename = "test-filename-1.2.3-1.el5.x86_64.rpm"
        test_group = "Application"
        test_license = "GPL"
        test_buildhost = "test.example.com"
        test_size = 22456
        p = self.package_api.create(name=test_pkg_name, epoch=test_epoch, version=test_version,
                release=test_release, arch=test_arch, description=test_description,
                checksum_type="sha256", checksum=test_checksum, filename=test_filename)
        p.size = test_size
        p.group = test_group
        p.buildhost = test_buildhost
        p.license = test_license
        self.assertTrue(p)
        self.assertTrue(p['name'] == test_pkg_name)
        self.assertTrue(p['epoch'] == test_epoch)
        self.assertTrue(p['version'] == test_version)
        self.assertTrue(p['release'] == test_release)
        self.assertTrue(p['arch'] == test_arch)
        self.assertTrue(p['description'] == test_description)
        self.assertTrue(p['checksum'].has_key(test_checksum_type))
        self.assertTrue(p['checksum'][test_checksum_type] == test_checksum)
        self.assertTrue(p['filename'] == test_filename)
        self.assertTrue(p['size'] == test_size)
        self.assertTrue(p['group'] == test_group)
        self.assertTrue(p['license'] == test_license)
        self.assertTrue(p['buildhost'] == test_buildhost)
        
    def test_package_delete_repo(self):
        repo = self.repo_api.create('some-id', 'some name',
            'i386', 'http://example.com')
        repo = self.repo_api.repository(repo["id"])
        test_pkg_name = "test_package_versions_name"
        test_epoch = "1"
        test_version = "1.2.3"
        test_release = "1.el5"
        test_arch = "x86_64"
        test_description = "test description text"
        test_checksum_type = "sha256"
        test_checksum = "9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e"
        test_filename = "test-filename-1.2.3-1.el5.x86_64.rpm"
        p = self.package_api.create(name=test_pkg_name, epoch=test_epoch, version=test_version,
                release=test_release, arch=test_arch, description=test_description,
                checksum_type="sha256", checksum=test_checksum, filename=test_filename)
        print "Package! %s" % p
        # Add this package version to the repo
        self.repo_api.add_package(repo["id"],[p['id']])
        # Lookup repo and confirm new package version was added
        repo = self.repo_api.repository(repo["id"])
        self.assertTrue(p['id'] in repo["packages"])
        packageid = p['id']
        saved_pkg = self.package_api.package(p['id'])
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
        pkgs = self.repo_api.packages(repo['id'], name=test_pkg_name)
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(pkgs[packageid]["id"] == packageid)
        self.assertTrue(pkgs[packageid]['filename'] == test_filename)

        self.repo_api.delete(repo['id'])
        found = self.package_api.package(p['id'])
        self.assertTrue(found is None)

    def test_find_repos_by_package(self):
        repo_a = self.repo_api.create('some-id_a', 'some name',
            'i386', 'http://example.com')
        repo_b = self.repo_api.create('some-id_b', 'some name',
            'i386', 'http://example.com')
        repo_a = self.repo_api.repository(repo_a["id"])
        repo_b = self.repo_api.repository(repo_b["id"])
        pkg1 = testutil.create_random_package(self.package_api)
        pkg2 = testutil.create_random_package(self.package_api)
        pkg3 = testutil.create_random_package(self.package_api)
        self.repo_api.add_package(repo_a["id"], [pkg1["id"]])
        self.repo_api.add_package(repo_a["id"], [pkg2["id"]])
        self.repo_api.add_package(repo_b["id"], [pkg1["id"]])

        found = self.repo_api.repository(repo_a["id"])
        self.assertTrue(pkg1["id"] in found["packages"])
        self.assertTrue(pkg2["id"] in found["packages"])
        self.assertTrue(pkg3["id"] not in found["packages"])

        found = self.repo_api.repository(repo_b["id"])
        self.assertTrue(pkg1["id"] in found["packages"])

        found = self.repo_api.find_repos_by_package(pkg1["id"])
        self.assertTrue(len(found) == 2)
        self.assertTrue(repo_a["id"] in found)
        self.assertTrue(repo_b["id"] in found)

    def test_find_orphaned_packages(self):
        repo_a = self.repo_api.create('some-id_a', 'some name',
            'i386', 'http://example.com')
        repo_b = self.repo_api.create('some-id_b', 'some name',
            'i386', 'http://example.com')
        repo_a = self.repo_api.repository(repo_a["id"])
        repo_b = self.repo_api.repository(repo_b["id"])
        #Create 5 test packages, associte 3 to repos
        #2 of them should be orphaned packages
        pkg1 = testutil.create_random_package(self.package_api)
        pkg2 = testutil.create_random_package(self.package_api)
        pkg3 = testutil.create_random_package(self.package_api)
        pkg4 = testutil.create_random_package(self.package_api)
        pkg5 = testutil.create_random_package(self.package_api)
        self.repo_api.add_package(repo_a["id"], [pkg1["id"]])
        self.repo_api.add_package(repo_a["id"], [pkg2["id"]])
        self.repo_api.add_package(repo_b["id"], [pkg1["id"]])
        self.repo_api.add_package(repo_b["id"], [pkg3["id"]])

        orphans = self.package_api.orphaned_packages()
        self.assertTrue(len(orphans) == 2)
        orphan_ids = [x["id"] for x in orphans]
        self.assertTrue(pkg4["id"] in orphan_ids)
        self.assertTrue(pkg5["id"] in orphan_ids)

    def test_or_query(self):
        repo_a = self.repo_api.create('some-id_a', 'some name',
            'i386', 'http://example.com')
        repo_b = self.repo_api.create('some-id_b', 'some name',
            'i386', 'http://example.com')
        pkg1 = testutil.create_random_package(self.package_api)
        pkg2 = testutil.create_random_package(self.package_api)
        pkg3 = testutil.create_random_package(self.package_api)

        queries = [{"filename":pkg1["filename"], "checksum.sha256":pkg1["checksum"]["sha256"]},
        {"filename":pkg2["filename"], "checksum.sha256":pkg2["checksum"]["sha256"]},
        {"filename":pkg3["filename"], "checksum.sha256":pkg3["checksum"]["sha256"]}]
        found = self.package_api.or_query(queries)
        self.assertEqual(len(found), 3)
        self.assertTrue(found[0]["id"] in [pkg1["id"], pkg2["id"], pkg3["id"]])
        self.assertTrue(found[1]["id"] in [pkg1["id"], pkg2["id"], pkg3["id"]])
        self.assertTrue(found[2]["id"] in [pkg1["id"], pkg2["id"], pkg3["id"]])

if __name__ == '__main__':
    unittest.main()
