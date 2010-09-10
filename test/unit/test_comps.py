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
import unittest
import logging
import tempfile
import yum
import shutil
import xml.dom
import time

srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src"
sys.path.append(srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import pulp.server.comps_util
import pulp.server.util
import pulp.server.db.model
from pulp.server.api.repo import RepoApi
from pulp.server.api.repo_sync import BaseSynchronizer
from pulp.server.pexceptions import PulpException

import testutil

log = logging.getLogger('pulp.test.testcomps')

class TestComps(unittest.TestCase):

    def setUp(self):
        self.config = testutil.load_test_config()
        self.rapi = RepoApi()
        self.data_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")

    def tearDown(self):
        self.rapi.clean()
        testutil.common_cleanup()

    def test_sync_groups_data(self):
        repo = self.rapi.create('test_sync_groups_data_id',
                'test_sync_groups_data_id', 'i386',
                'yum:http://example.com/')
        # Parse existing comps.xml
        compspath = os.path.join(self.data_path, "rhel-i386-server-5/comps.xml")
        compsfile = open(compspath)
        base = BaseSynchronizer()
        base.sync_groups_data(compsfile, repo)
        # 'repo' object should now contain groups/categories
        # we need to save it to the db so we can query from it
        self.rapi.update(repo)
        # Testing for expected values
        found = self.rapi.packagegroup(repo['id'], "web-server")
        self.assertTrue(found is not None)
        self.assertTrue("httpd" in found['mandatory_package_names'])
        self.assertTrue("mod_auth_kerb" in found['optional_package_names'])
        self.assertTrue("mod_auth_mysql" in found['optional_package_names'])
        self.assertTrue("crypto-utils" in found['default_package_names'])
        self.assertTrue("distcache" in found['default_package_names'])
        # PackageGroupCategory, look up expected values,
        found = self.rapi.packagegroupcategory(repo['id'], "BAD_VALUE_NOT_IN_CATEGORY")
        self.assertTrue(found is None)
        found = self.rapi.packagegroupcategory(repo['id'], "development")
        self.assertTrue(found is not None)

    def test_create_groups_metadata(self):
        repo_path = os.path.join(self.data_path, "no_groups_repo")
        repo = self.rapi.create("test_create_groups_metadata_id",
                'test_import_groups_data_id', 'i386',
                'local:file://%s' % (repo_path))
        self.rapi.sync(repo["id"])
        found = self.rapi.packagegroups(repo['id'])
        self.assertTrue(len(found) == 0)
        self.assertTrue(repo["group_xml_path"] == "")
        self.assertTrue(repo["group_gz_xml_path"] == "")
        pkg_group = self.rapi.create_packagegroup(repo["id"], "test_group",
                "test_group_name", "test description")
        self.rapi.add_packages_to_group(repo["id"], pkg_group["id"], ["test_package_name"])
        # Update repo object so we can test that group_xml_path was set
        repo = self.rapi.repository(repo["id"])
        self.assertTrue(repo["group_xml_path"] != "")
        comps = yum.comps.Comps()
        comps.add(repo["group_xml_path"])
        groups = comps.get_groups()
        self.assertTrue(len(groups) == 1)
        self.assertTrue(groups[0].groupid == pkg_group["id"])
        self.assertTrue(groups[0].name == pkg_group["name"])
        self.assertTrue("test_package_name" in groups[0].default_packages)
        self.assertTrue("test_package_name" not in groups[0].mandatory_packages)

    def test_basic_comps(self):
        repo = self.rapi.create('test_comps_id', 'test_comps_name',
            'i386', 'yum:http://example.com/')
        grp = pulp.server.db.model.PackageGroup("groupid1", "groupname1",
            "description", "user_visible", "display_order", "default"
            "langonly")
        grp['mandatory_package_names'] = ["mandatory_package_name1"]
        grp['optional_package_names'] = ["optional_package_name1"]
        grp['default_package_names'] = ["default_package_name1"]
        grp['conditional_package_names'] = {"pkg1":"value pkg1"}
        grp['translated_name'] = {"a":"value"}
        grp['translated_description'] = {"b":"value"}
        self.rapi.update_packagegroup(repo['id'], grp)
        found = self.rapi.packagegroup(repo['id'], grp['id'])
        self.assertTrue(found is not None)
        self.assertTrue(found['name'] == 'groupname1')
        self.assertTrue("mandatory_package_name1" in found['mandatory_package_names'])

        ctg = pulp.server.db.model.PackageGroupCategory("categoryid1",
                    "categoryname", "description", "display_order")
        ctg['packagegroupids'] = ["groupid1"]
        ctg['translated_name'] = {"a":"name"}
        ctg['translated_description'] = {"b":"description"}
        self.rapi.update_packagegroupcategory(repo["id"], ctg)
        found = self.rapi.packagegroupcategory(repo["id"], ctg["id"])
        self.assertTrue(found is not None)
        self.assertTrue(found["name"] == "categoryname")
        self.assertTrue("groupid1" in found["packagegroupids"])


    def test_delete_group_category(self):
        repo = self.rapi.create('test_delete_group_category',
                'test_delete_group_category', 'i386',
                'yum:http://example.com/')
        cat = self.rapi.create_packagegroupcategory(repo["id"],
                "test_cat", "test_cat_name", "test description")
        grp = self.rapi.create_packagegroup(repo["id"],
                "test_group", "test_group_name", "test description")
        found = self.rapi.packagegroupcategory(repo['id'], cat["id"])
        self.assertTrue(found is not None)
        found = self.rapi.packagegroup(repo['id'], grp["id"])
        self.assertTrue(found is not None)
        self.rapi.delete_packagegroup(repo['id'], grp["id"])
        found = self.rapi.packagegroup(repo['id'], grp["id"])
        self.assertTrue(found is None)
        self.rapi.delete_packagegroupcategory(repo['id'], cat["id"])
        found = self.rapi.packagegroupcategory(repo['id'], cat["id"])
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
        grp['conditional_package_names'] = {"pkg1":"value pkg1"}
        grp['translated_name'] = {"a":"value"}
        grp['translated_description'] = {"b":"value"}
        yumGrp = pulp.server.comps_util.model_group_to_yum_group(grp)
        self.assertTrue(yumGrp.groupid == "groupid1")
        self.assertTrue("mandatory_package_name1" in yumGrp.mandatory_packages)
        xml = yumGrp.xml()
        log.debug("Group XML = %s" % (xml))
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
        log.debug("Category XML = %s" % (xml))
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
        repo = self.rapi.create('test_comps_id', 'test_comps_name',
                'i386', 'yum:http://example.com/')
        found = self.rapi.packagegroups(repo['id'])
        self.assertTrue(len(found) == 0)
        found = self.rapi.packagegroupcategories(repo['id'])
        self.assertTrue(len(found) == 0)

        # Create Groups/Categories from parsed data
        grp_list = []
        for g in comps.get_groups():
            grp = pulp.server.comps_util.yum_group_to_model_group(g)
            self.assertTrue(grp is not None)
            grp_list.append(grp)
        self.rapi.update_packagegroups(repo['id'], grp_list)
        ctg_list = []
        for c in comps.get_categories():
            ctg = pulp.server.comps_util.yum_category_to_model_category(c)
            self.assertTrue(ctg is not None)
            ctg_list.append(ctg)
        self.rapi.update_packagegroupcategories(repo['id'], ctg_list)

        # Lookup data from API calls
        found = self.rapi.packagegroups(repo['id'])
        self.assertTrue(len(found) == len(comps.get_groups()))
        found = self.rapi.packagegroupcategories(repo['id'])
        self.assertTrue(len(found) == len(comps.get_categories()))

        # PackageGroup, look up expected values, 
        # good values come from known data in rhel-5 comps.xml
        found = self.rapi.packagegroup(repo['id'], "BAD_VALUE_NOT_IN_GROUP")
        self.assertTrue(found is None)
        found = self.rapi.packagegroup(repo['id'], "web-server")
        self.assertTrue(found is not None)
        self.assertTrue("httpd" in found['mandatory_package_names'])
        self.assertTrue("mod_auth_kerb" in found['optional_package_names'])
        self.assertTrue("mod_auth_mysql" in found['optional_package_names'])
        self.assertTrue("crypto-utils" in found['default_package_names'])
        self.assertTrue("distcache" in found['default_package_names'])

        # PackageGroupCategory, look up expected values,
        found = self.rapi.packagegroupcategory(repo['id'], "BAD_VALUE_NOT_IN_CATEGORY")
        self.assertTrue(found is None)
        found = self.rapi.packagegroupcategory(repo['id'], "development")
        self.assertTrue(found is not None)


        # Look up groups/categories from repo api
        ctgs = self.rapi.packagegroupcategories(repo["id"])
        grps = self.rapi.packagegroups(repo["id"])

        xml = pulp.server.comps_util.form_comps_xml(ctgs, grps)
        #log.debug("Generated XML = %s" % (xml.encode('utf-8')))
        self.assertTrue(len(xml) > 0)
        self.assertTrue(xml.find("<comps>"))
        self.assertTrue(xml.find("</comps>"))
        self.assertTrue(xml.find("<group>"))
        self.assertTrue(xml.find("<category>"))
        # Verify the XML we produced can be parsed to get back valid
        # yum Groups/Categories
        f = tempfile.NamedTemporaryFile(delete=False)
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
        log.debug("new comps has %s groups we expected %s groups" % \
                (actualGroups, expectedGroups))
        log.debug("new comps has %s categoriess we expected %s categoriess" \
                % (actualCats, expectedCats))
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
        f_comps = tempfile.NamedTemporaryFile(delete=False)
        f_repomd = tempfile.NamedTemporaryFile(delete=False)
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

    def immutable_groups(self):
        #TODO  until we fix group import, this tests needs to be commented out

        repo_path = os.path.join(self.data_path, "repo_with_groups")
        # Create repo with 1 group
        repo = self.rapi.create('test_immutable_groups_id',
                'test_import_groups_data_id', 'i386',
                'local:file://%s' % (repo_path))
        self.rapi.sync(repo["id"])
        # Ensure groups/categories were found and they are all immutable
        found = self.rapi.packagegroups(repo['id'])
        self.assertTrue(len(found) > 0)
        for key in found:
            self.assertTrue(found[key]["immutable"] == True)
        found = self.rapi.packagegroupcategories(repo['id'])
        self.assertTrue(len(found) > 0)
        for key in found:
            self.assertTrue(found[key]["immutable"] == True)
        found = self.rapi.packagegroup(repo['id'], "admin-tools")
        self.assertTrue(found is not None)
        self.assertTrue("system-config-boot" in found['default_package_names'])
        # Verify we cannot delete a package from an immutable group
        caught = False
        try:
            self.rapi.delete_package_from_group(repo["id"], found["id"],
                "system-config-boot", gtype="default")
        except PulpException, e:
            caught = True
        self.assertTrue(caught)
        # Verify we cannot add a package
        caught = False
        try:
            self.rapi.add_packages_to_group(repo["id"], "admin-tools",
                ["newPackage"], gtype="default")
        except PulpException, e:
            caught = True
        self.assertTrue(caught)
        # Verify we cannot update package group with same name
        caught = False
        try:
            found = self.rapi.packagegroup(repo["id"], "admin-tools")
            self.assertTrue(found is not None)
            found["default_package_names"].append("newPackage1")
            self.rapi.update_packagegroup(repo["id"], found)
        except PulpException, e:
            caught = True
        self.assertTrue(caught)
        # Verify if we create a new package group, we can add/delete packages
        pkg_group = self.rapi.create_packagegroup(repo["id"], "test_group",
                "test_group_name", "test description")
        self.rapi.add_packages_to_group(repo["id"], pkg_group["id"],
                ["test_package_name"], gtype="default")
        found = self.rapi.packagegroup(repo['id'], pkg_group["id"])
        self.assertTrue(found is not None)
        self.assertTrue("test_package_name" in found["default_package_names"])
        self.rapi.delete_package_from_group(repo["id"], pkg_group["id"],
                "test_package_name", gtype="default")
        found = self.rapi.packagegroup(repo['id'], pkg_group["id"])
        self.assertTrue(found is not None)
        self.assertTrue("test_package_name" not in found["default_package_names"])
        # Verify we can remove package group
        self.rapi.delete_packagegroup(repo["id"], pkg_group["id"])
        found = self.rapi.packagegroup(repo['id'], pkg_group["id"])
        self.assertTrue(found is None)


    def comps_resync_with_group_changes(self):
        #TODO: until we fix group import this needs to be commented out    

        repo_path = os.path.join(self.data_path, "repo_resync_a")
        repo = self.rapi.create('test_comps_resync_with_group_changes',
                'test_comps_resync_with_group_changes_name', 'i386',
                'local:file://%s' % (repo_path))
        self.rapi.sync(repo["id"])
        found = self.rapi.packagegroups(repo['id'])
        # Verify expected groups/categories
        self.assertTrue(len(found) == 3)
        self.assertTrue(self.rapi.packagegroup(repo["id"], "admin-tools") is not None)
        self.assertTrue(self.rapi.packagegroup(repo["id"], "dns-server") is not None)
        self.assertTrue(self.rapi.packagegroup(repo["id"], "haskell") is not None)
        found = self.rapi.packagegroup(repo["id"], "dns-server")
        self.assertTrue(found is not None)
        self.assertTrue("bind" in found["optional_package_names"])
        self.assertTrue("dnssec-conf" not in found["mandatory_package_names"])
        found = self.rapi.packagegroupcategories(repo['id'])
        self.assertTrue(len(found) == 2)
        self.assertTrue(self.rapi.packagegroupcategory(repo["id"], "desktops") is not None)
        self.assertTrue(self.rapi.packagegroupcategory(repo["id"], "apps") is not None)
        # Simulate a change to comps.xml from repo source 
        # Changes:  removed the haskell group 
        #           added a package to the dns-server group
        #           added a new category, 'development'
        repo_path = os.path.join(self.data_path, "repo_resync_b")
        repo = self.rapi.repository(repo["id"])
        repo["source"] = pulp.server.db.model.RepoSource("local:file://%s" % (repo_path))
        self.rapi.update(repo)
        self.rapi.sync(repo["id"])
        found = self.rapi.packagegroups(repo['id'])
        self.assertTrue(len(found) == 2)
        self.assertTrue(self.rapi.packagegroup(repo["id"], "admin-tools") is not None)
        self.assertTrue(self.rapi.packagegroup(repo["id"], "dns-server") is not None)
        found = self.rapi.packagegroup(repo["id"], "dns-server")
        self.assertTrue("bind" in found["optional_package_names"])
        self.assertTrue("dnssec-conf" in found["mandatory_package_names"])
        found = self.rapi.packagegroupcategories(repo['id'])
        self.assertTrue(len(found) == 3)
        self.assertTrue(self.rapi.packagegroupcategory(
            repo["id"], "desktops") is not None)
        self.assertTrue(self.rapi.packagegroupcategory(
            repo["id"], "apps") is not None)
        self.assertTrue(self.rapi.packagegroupcategory(
            repo["id"], "development") is not None)

