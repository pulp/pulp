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
#

import sys
import os
import logging
import yum
import shutil
import xml.dom.minidom
import time
import random
from tempfile import gettempdir

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import pulp.server.comps_util
import pulp.server.util
from pulp.server.api import repo_sync
from pulp.server.db import model
from pulp.server.api.synchronizers import BaseSynchronizer
from pulp.server.exceptions import PulpException

logging.root.setLevel(logging.ERROR)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

log = logging.getLogger('pulp.test.testcomps')

def tmpfile():
    # used instead of tempfile.NamedTemporaryFile(delete=True)
    # for python 2.4 compat.  (delete=True) not supported in 2.4.
    n = random.randint(0 ,0xFFFF)
    fn = hex(n)[2:].upper()
    path = os.path.join(gettempdir(), fn)
    return open(path, 'w')


class TestComps(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        logging.root.setLevel(logging.ERROR)

    def test_sync_groups_data(self):
        repo = self.repo_api.create('test_sync_groups_data_id',
                'test_sync_groups_data_id', 'i386',
                'http://example.com/')
        # Parse existing comps.xml
        compspath = os.path.join(self.data_path, "rhel-i386-server-5/comps.xml")
        compsfile = open(compspath)
        base = BaseSynchronizer()
        base.sync_groups_data(compsfile, repo)
        # 'repo' object should now contain groups/categories
        # we need to save it to the db so we can query from it
        model.Repo.get_collection().save(repo, safe=True)
        # Testing for expected values
        found = self.repo_api.packagegroup(repo['id'], "web-server")
        self.assertTrue(found is not None)
        self.assertTrue("httpd" in found['mandatory_package_names'])
        self.assertTrue("mod_auth_kerb" in found['optional_package_names'])
        self.assertTrue("mod_auth_mysql" in found['optional_package_names'])
        self.assertTrue("crypto-utils" in found['default_package_names'])
        self.assertTrue("distcache" in found['default_package_names'])
        # PackageGroupCategory, look up expected values,
        found = self.repo_api.packagegroupcategory(repo['id'], "BAD_VALUE_NOT_IN_CATEGORY")
        self.assertTrue(found is None)
        found = self.repo_api.packagegroupcategory(repo['id'], "development")
        self.assertTrue(found is not None)

    def test_create_groups_metadata(self):
        repo_path = os.path.join(self.data_path, "no_groups_repo")
        repo = self.repo_api.create("test_create_groups_metadata_id",
                'test_import_groups_data_id', 'i386',
                'file://%s' % (repo_path))
        repo_sync._sync(repo["id"])
        found = self.repo_api.packagegroups(repo['id'])
        self.assertTrue(len(found) == 0)
        self.assertTrue(repo["group_xml_path"] == "")
        self.assertTrue(repo["group_gz_xml_path"] == "")
        pkg_group = self.repo_api.create_packagegroup(repo["id"], "test_group",
                "test_group_name", "test description")

        self.repo_api.add_packages_to_group(repo["id"], pkg_group["id"], ["pulp-test-package"])
        # Update repo object so we can test that group_xml_path was set
        repo = self.repo_api.repository(repo["id"])
        self.assertTrue(repo["group_xml_path"] != "")
        comps = yum.comps.Comps()
        comps.add(repo["group_xml_path"])
        groups = comps.get_groups()
        self.assertTrue(len(groups) == 1)
        self.assertTrue(groups[0].groupid == pkg_group["id"])
        self.assertTrue(groups[0].name == pkg_group["name"])
        self.assertTrue("pulp-test-package" in groups[0].default_packages)
        self.assertTrue("pulp-test-package" not in groups[0].mandatory_packages)

    def test_basic_comps(self):
        repo = self.repo_api.create('test_comps_id', 'test_comps_name',
            'i386', 'http://example.com/')
        grp = pulp.server.db.model.PackageGroup("groupid1", "groupname1",
            "description", "user_visible", "display_order", "default"
            "langonly")
        grp['mandatory_package_names'] = ["mandatory_package_name1"]
        grp['optional_package_names'] = ["optional_package_name1"]
        grp['default_package_names'] = ["default_package_name1"]
        grp['conditional_package_names'] = {"requires_pkg":["package_name1", "package_name2"]}
        grp['translated_name'] = {"a":"value"}
        grp['translated_description'] = {"b":"value"}
        self.repo_api.update_packagegroup(repo['id'], grp)
        found = self.repo_api.packagegroup(repo['id'], grp['id'])
        self.assertTrue(found is not None)
        self.assertTrue(found['name'] == 'groupname1')
        self.assertTrue("mandatory_package_name1" in found['mandatory_package_names'])
        self.assertTrue("optional_package_name1" in found['optional_package_names'])
        self.assertTrue("default_package_name1" in found['default_package_names'])
        self.assertTrue("package_name1" in found["conditional_package_names"]["requires_pkg"])
        self.assertTrue("package_name2" in found["conditional_package_names"]["requires_pkg"])

        ctg = pulp.server.db.model.PackageGroupCategory("categoryid1",
                    "categoryname", "description", "display_order")
        ctg['packagegroupids'] = ["groupid1"]
        ctg['translated_name'] = {"a":"name"}
        ctg['translated_description'] = {"b":"description"}
        self.repo_api.update_packagegroupcategory(repo["id"], ctg)
        found = self.repo_api.packagegroupcategory(repo["id"], ctg["id"])
        self.assertTrue(found is not None)
        self.assertTrue(found["name"] == "categoryname")
        self.assertTrue("groupid1" in found["packagegroupids"])


    def test_delete_group_category(self):
        repo = self.repo_api.create('test_delete_group_category',
                'test_delete_group_category', 'i386',
                'http://example.com/')
        cat = self.repo_api.create_packagegroupcategory(repo["id"],
                "test_cat", "test_cat_name", "test description")
        grp = self.repo_api.create_packagegroup(repo["id"],
                "test_group", "test_group_name", "test description")
        found = self.repo_api.packagegroupcategory(repo['id'], cat["id"])
        self.assertTrue(found is not None)
        found = self.repo_api.packagegroup(repo['id'], grp["id"])
        self.assertTrue(found is not None)
        self.repo_api.delete_packagegroup(repo['id'], grp["id"])
        found = self.repo_api.packagegroup(repo['id'], grp["id"])
        self.assertTrue(found is None)
        self.repo_api.delete_packagegroupcategory(repo['id'], cat["id"])
        found = self.repo_api.packagegroupcategory(repo['id'], cat["id"])
        self.assertTrue(found is None)

    def test_model_group_to_yum_group(self):
        """
        Test translation of model.PackageGroup to yum.comps.Group
        """
        grp = pulp.server.db.model.PackageGroup("groupid1", "groupname1",
            "description", "user_visible", "display_order", "default"
            "langonly")
        grp['mandatory_package_names'] = ["mandatory_package_name1"]
        grp['optional_package_names'] = ["optional_package_name1"]
        grp['default_package_names'] = ["default_package_name1"]
        grp['conditional_package_names'] = {"package_name1":"requires_pkg", \
                "package_name2":"requires_pkg"}
        grp['translated_name'] = {"a":"value"}
        grp['translated_description'] = {"b":"value"}
        yumGrp = pulp.server.comps_util.model_group_to_yum_group(grp)
        self.assertTrue(yumGrp.groupid == "groupid1")
        self.assertTrue("mandatory_package_name1" in yumGrp.mandatory_packages)
        self.assertTrue("package_name1" in yumGrp.conditional_packages)
        self.assertEquals("requires_pkg", yumGrp.conditional_packages["package_name1"])
        self.assertTrue("package_name2" in yumGrp.conditional_packages)
        self.assertEquals("requires_pkg", yumGrp.conditional_packages["package_name2"])


        xml = yumGrp.xml()
        #log.debug("Group XML = %s" % (xml))
        self.assertTrue(len(xml) > 0)

    def test_model_category_to_yum_category(self):
        """
        Test translation of model.PackageGroupCategory to yum.comps.Category
        """
        ctg = pulp.server.db.model.PackageGroupCategory("categoryid1",
                    "categoryname", "description", "display_order")
        ctg['packagegroupids'] = ["groupid1"]
        ctg['translated_name'] = {"a":"name"}
        ctg['translated_description'] = {"b":"description"}
        yumCat = pulp.server.comps_util.model_category_to_yum_category(ctg)
        self.assertTrue(yumCat.categoryid == "categoryid1")
        self.assertTrue("groupid1" in yumCat._groups)
        xml = yumCat.xml()
        #log.debug("Category XML = %s" % (xml))
        self.assertTrue(len(xml) > 0)

    def test_full_read_parse_write_to_xml(self):
        """
        Test full cycle of Groups/Categories, import a comps.xml, parse it
        modify the entries, then write them out to XML
        """
        # Parse existing comps.xml
        compsPath = os.path.join(self.data_path, "rhel-i386-server-5/comps.xml")
        comps = yum.comps.Comps()
        comps.add(compsPath)
        self.assertTrue(len(comps.get_groups()) != 0)
        self.assertTrue(len(comps.get_categories()) != 0)

        # Create empty repo, we will populate it with our groups/categories
        repo = self.repo_api.create('test_comps_id', 'test_comps_name',
                'i386', 'http://example.com/')
        found = self.repo_api.packagegroups(repo['id'])
        self.assertTrue(len(found) == 0)
        found = self.repo_api.packagegroupcategories(repo['id'])
        self.assertTrue(len(found) == 0)

        # Create Groups/Categories from parsed data
        grp_list = []
        for g in comps.get_groups():
            grp = pulp.server.comps_util.yum_group_to_model_group(g)
            self.assertTrue(grp is not None)
            grp_list.append(grp)
        self.repo_api.update_packagegroups(repo['id'], grp_list)
        ctg_list = []
        for c in comps.get_categories():
            ctg = pulp.server.comps_util.yum_category_to_model_category(c)
            self.assertTrue(ctg is not None)
            ctg_list.append(ctg)
        self.repo_api.update_packagegroupcategories(repo['id'], ctg_list)

        # Lookup data from API calls
        found = self.repo_api.packagegroups(repo['id'])
        self.assertTrue(len(found) == len(comps.get_groups()))
        found = self.repo_api.packagegroupcategories(repo['id'])
        self.assertTrue(len(found) == len(comps.get_categories()))

        # PackageGroup, look up expected values,
        # good values come from known data in rhel-5 comps.xml
        found = self.repo_api.packagegroup(repo['id'], "BAD_VALUE_NOT_IN_GROUP")
        self.assertTrue(found is None)
        found = self.repo_api.packagegroup(repo['id'], "web-server")
        self.assertTrue(found is not None)
        self.assertTrue("httpd" in found['mandatory_package_names'])
        self.assertTrue("mod_auth_kerb" in found['optional_package_names'])
        self.assertTrue("mod_auth_mysql" in found['optional_package_names'])
        self.assertTrue("crypto-utils" in found['default_package_names'])
        self.assertTrue("distcache" in found['default_package_names'])
        found = self.repo_api.packagegroup(repo['id'], "afrikaans-support")
        self.assertTrue(found is not None)
        self.assertTrue("aspell-af" in found['conditional_package_names'])
        self.assertEquals("aspell", found['conditional_package_names']['aspell-af'])

        # PackageGroupCategory, look up expected values,
        found = self.repo_api.packagegroupcategory(repo['id'], "BAD_VALUE_NOT_IN_CATEGORY")
        self.assertTrue(found is None)
        found = self.repo_api.packagegroupcategory(repo['id'], "development")
        self.assertTrue(found is not None)


        # Look up groups/categories from repo api
        ctgs = self.repo_api.packagegroupcategories(repo["id"])
        grps = self.repo_api.packagegroups(repo["id"])

        xml = pulp.server.comps_util.form_comps_xml(ctgs, grps)
        #log.debug("Generated XML = %s" % (xml.encode('utf-8')))
        self.assertTrue(len(xml) > 0)
        self.assertTrue(xml.find("<comps>"))
        self.assertTrue(xml.find("</comps>"))
        self.assertTrue(xml.find("<group>"))
        self.assertTrue(xml.find("<category>"))
        # Verify the XML we produced can be parsed to get back valid
        # yum Groups/Categories
        f = tmpfile()
        f_name = f.name
        log.debug("Writing comps xml to %s" % (f_name))
        f.write(xml.encode('utf-8'))
        f.close()
        parsedComps = yum.comps.Comps()
        parsedComps.add(f_name)
        self.assertTrue(len(parsedComps.get_groups()) != 0)
        self.assertTrue(len(parsedComps.get_categories()) != 0)

        foundGroup = None
        actualGroups = len(parsedComps.get_groups())
        expectedGroups = len(comps.get_groups())
        actualCats = len(parsedComps.get_categories())
        expectedCats = len(parsedComps.get_categories())
        #log.debug("new comps has %s groups we expected %s groups" % \
        #        (actualGroups, expectedGroups))
        #log.debug("new comps has %s categoriess we expected %s categoriess" \
        #        % (actualCats, expectedCats))
        self.assertTrue(actualGroups == expectedGroups)
        self.assertTrue(actualCats == expectedCats)
        groups = parsedComps.get_groups()
        for g in groups:
            if g.groupid == "web-server":
                foundGroup = g
                break
        self.assertTrue(foundGroup is not None)
        self.assertTrue("httpd" in foundGroup.mandatory_packages)
        self.assertTrue("mod_auth_kerb" in foundGroup.optional_packages)
        self.assertTrue("mod_auth_mysql" in foundGroup.optional_packages)
        self.assertTrue("crypto-utils" in foundGroup.default_packages)
        self.assertTrue("distcache" in foundGroup.default_packages)
        # Clean up file if tests have passed,
        # leave file for debugging if tests failed
        os.unlink(f_name)

    def test_update_repomd_xml_file(self):
        """
        Update repomd.xml with a newer comps.xml
        """
        comps_path = os.path.join(self.data_path, "rhel-i386-server-5/comps.xml")
        repomd_path = os.path.join(self.data_path, "rhel-i386-server-5/repomd.xml")
        # In case the test fails, we want the temp files left over for debugging
        f_comps = tmpfile()
        f_repomd = tmpfile()
        f_repomd.close()
        tmp_comps_path = f_comps.name
        tmp_repomd_path = f_repomd.name
        log.debug("test_update_repomdxml_file temp comps.xml = %s, temp repomd.xml = %s" % \
                (tmp_comps_path, tmp_repomd_path))
        # Copy original repomd to temp file so we can modify it
        shutil.copy(repomd_path, tmp_repomd_path)
        # Modify temp comps.xml so we know the sha256 is different
        dom = xml.dom.minidom.parse(comps_path)
        dom.getElementsByTagName("id")[0].childNodes[0].data = "MODIFIED %s" % (time.time())
        f_comps.write(dom.toxml().encode("UTF-8"))
        f_comps.close()
        # Update repomd.xml with our newer comps.xml
        pulp.server.comps_util.update_repomd_xml_file(tmp_repomd_path, tmp_comps_path)
        dom = xml.dom.minidom.parse(tmp_repomd_path)
        # Checksum test
        group_elems = filter(lambda x: x.getAttribute("type") == "group", dom.getElementsByTagName("data"))
        self.assertTrue(len(group_elems) == 1)
        checksum_elems = group_elems[0].getElementsByTagName("checksum")
        self.assertTrue(len(checksum_elems) == 1)
        actualChecksum = checksum_elems[0].childNodes[0].data
        expectedChecksum = pulp.server.util.get_file_checksum(hashtype="sha256", filename=tmp_comps_path)
        self.assertTrue(actualChecksum == expectedChecksum)
        # Timestamp test
        timestamp_elems = group_elems[0].getElementsByTagName("timestamp")
        actualTimestamp = timestamp_elems[0].childNodes[0].data
        expectedTimestamp = pulp.server.util.get_file_timestamp(tmp_repomd_path)
        self.assertTrue(actualTimestamp, expectedTimestamp)
        os.unlink(tmp_repomd_path)
        os.unlink(tmp_comps_path)

    def test_immutable_groups(self):

        repo_path = os.path.join(self.data_path, "repo_with_groups")
        # Create repo with 1 group
        repo = self.repo_api.create('test_immutable_groups_id',
                'test_import_groups_data_id', 'i386',
                'file://%s' % (repo_path))
        repo_sync._sync(repo["id"])
        # Ensure groups/categories were found and they are all immutable
        found = self.repo_api.packagegroups(repo['id'])
        self.assertTrue(len(found) > 0)
        for key in found:
            self.assertTrue(found[key]["immutable"] == True)
        found = self.repo_api.packagegroupcategories(repo['id'])
        self.assertTrue(len(found) > 0)
        for key in found:
            self.assertTrue(found[key]["immutable"] == True)
        found = self.repo_api.packagegroup(repo['id'], "admin-tools")
        self.assertTrue(found is not None)
        self.assertTrue("system-config-boot" in found['default_package_names'])
        # Verify we cannot delete a package from an immutable group
        caught = False
        try:
            self.repo_api.delete_package_from_group(repo["id"], found["id"],
                "pulp-test-package", gtype="default")
        except PulpException, e:
            caught = True
        self.assertTrue(caught)
        # Verify we cannot add a package
        caught = False
        try:
            self.repo_api.add_packages_to_group(repo["id"], "admin-tools",
                ["pulp-test-package"], gtype="default")
        except PulpException, e:
            caught = True
        self.assertTrue(caught)
        # Verify we cannot update package group with same name
        caught = False
        try:
            found = self.repo_api.packagegroup(repo["id"], "admin-tools")
            self.assertTrue(found is not None)
            found["default_package_names"].append("newPackage1")
            self.repo_api.update_packagegroup(repo["id"], found)
        except PulpException, e:
            caught = True
        self.assertTrue(caught)

        # Verify if we create a new package group, we can add/delete packages
        pkg_group = self.repo_api.create_packagegroup(repo["id"], "test_group",
                "test_group_name", "test description")
        self.repo_api.add_packages_to_group(repo["id"], pkg_group["id"],
                ["pulp-test-package"], gtype="default")
        found = self.repo_api.packagegroup(repo['id'], pkg_group["id"])
        self.assertTrue(found is not None)
        self.assertTrue("pulp-test-package" in found["default_package_names"])
        self.repo_api.delete_package_from_group(repo["id"], pkg_group["id"],
                "pulp-test-package", gtype="default")
        found = self.repo_api.packagegroup(repo['id'], pkg_group["id"])
        self.assertTrue(found is not None)
        self.assertTrue("pulp-test-package" not in found["default_package_names"])
        # Verify we can remove package group
        self.repo_api.delete_packagegroup(repo["id"], pkg_group["id"])
        found = self.repo_api.packagegroup(repo['id'], pkg_group["id"])
        self.assertTrue(found is None)


    def test_comps_resync_with_group_changes(self):

        repo_path = os.path.join(self.data_path, "repo_resync_a")
        repo = self.repo_api.create('test_comps_resync_with_group_changes',
                'test_comps_resync_with_group_changes_name', 'i386',
                'file://%s' % (repo_path))
        repo_sync._sync(repo["id"])
        found = self.repo_api.packagegroups(repo['id'])
        # Verify expected groups/categories
        self.assertTrue(len(found) == 3)
        self.assertTrue(self.repo_api.packagegroup(repo["id"], "admin-tools") is not None)
        self.assertTrue(self.repo_api.packagegroup(repo["id"], "dns-server") is not None)
        self.assertTrue(self.repo_api.packagegroup(repo["id"], "haskell") is not None)
        found = self.repo_api.packagegroup(repo["id"], "dns-server")
        self.assertTrue(found is not None)
        self.assertTrue("bind" in found["optional_package_names"])
        self.assertTrue("dnssec-conf" not in found["mandatory_package_names"])
        found = self.repo_api.packagegroupcategories(repo['id'])
        self.assertTrue(len(found) == 2)
        self.assertTrue(self.repo_api.packagegroupcategory(repo["id"], "desktops") is not None)
        self.assertTrue(self.repo_api.packagegroupcategory(repo["id"], "apps") is not None)
        # Simulate a change to comps.xml from repo source
        # Changes:  removed the haskell group
        #           added a package to the dns-server group
        #           added a new category, 'development'
        repo_path = os.path.join(self.data_path, "repo_resync_b")
        repo = self.repo_api.repository(repo["id"])
        repo["source"] = pulp.server.db.model.RepoSource("file://%s" % (repo_path))
        model.Repo.get_collection().save(repo, safe=True)
        repo_sync._sync(repo["id"])
        found = self.repo_api.packagegroups(repo['id'])
        self.assertTrue(len(found) == 2)
        self.assertTrue(self.repo_api.packagegroup(repo["id"], "admin-tools") is not None)
        self.assertTrue(self.repo_api.packagegroup(repo["id"], "dns-server") is not None)
        found = self.repo_api.packagegroup(repo["id"], "dns-server")
        self.assertTrue("bind" in found["optional_package_names"])
        self.assertTrue("dnssec-conf" in found["mandatory_package_names"])
        found = self.repo_api.packagegroupcategories(repo['id'])
        self.assertTrue(len(found) == 3)
        self.assertTrue(self.repo_api.packagegroupcategory(
            repo["id"], "desktops") is not None)
        self.assertTrue(self.repo_api.packagegroupcategory(
            repo["id"], "apps") is not None)
        self.assertTrue(self.repo_api.packagegroupcategory(
            repo["id"], "development") is not None)

