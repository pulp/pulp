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

srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src"
sys.path.append(srcdir)
import pulp.comps_util
import pulp.util
import pulp.model
from pulp.api.repo import RepoApi
from pulp.api.repo_sync import BaseSynchronizer

log = logging.getLogger('pulp.test.testcomps')

class TestComps(unittest.TestCase):

    def setUp(self):
        config_file = os.path.join(srcdir, "../etc/pulp/pulp.ini")
        self.config = pulp.util.load_config(config_file)
        self.rapi = RepoApi(self.config)
        self.dataPath = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")

    def tearDown(self):
        self.rapi.clean()

    def test_import_groups_data(self):
        repo = self.rapi.create('test_import_groups_data_id',
                'test_import_groups_data_id', 'i386', 
                'yum:http://example.com/')
        # Parse existing comps.xml
        compspath = os.path.join(self.dataPath, "rhel-i386-server-5/comps.xml")
        compsfile = open(compspath)
        base = BaseSynchronizer(self.config)
        base.import_groups_data(compsfile, repo)
        # 'repo' object should now contain groups/categories
        # we need to save it to the db so we can query from it
        self.rapi.update(repo)
        # Testing for expected values
        found = self.rapi.packagegroup(repo['id'], "web-server")
        self.assertTrue(found != None)
        self.assertTrue("httpd" in found['mandatory_package_names'])
        self.assertTrue("mod_auth_kerb" in found['optional_package_names'])
        self.assertTrue("mod_auth_mysql" in found['optional_package_names'])
        self.assertTrue("crypto-utils" in found['default_package_names'])
        self.assertTrue("distcache" in found['default_package_names'])
        # PackageGroupCategory, look up expected values,
        found = self.rapi.packagegroupcategory(repo['id'], "BAD_VALUE_NOT_IN_CATEGORY")
        self.assertTrue(found == None)
        found = self.rapi.packagegroupcategory(repo['id'], "development")
        self.assertTrue(found != None)

    def test_basic_comps(self):
        repo = self.rapi.create('test_comps_id','test_comps_name', 
            'i386', 'yum:http://example.com/')
        grp = pulp.model.PackageGroup("groupid1", "groupname1", 
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
        self.assertTrue(found != None)
        self.assertTrue(found['name'] == 'groupname1')
        self.assertTrue("mandatory_package_name1" in found['mandatory_package_names'])

        ctg = pulp.model.PackageGroupCategory("categoryid1", 
                    "categoryname", "description", "display_order")
        ctg['packagegroupids'] = ["groupid1"]
        ctg['translated_name'] = {"a":"name"}
        ctg['translated_description'] = {"b":"description"}
        self.rapi.update_packagegroupcategory(repo["id"], ctg)
        found = self.rapi.packagegroupcategory(repo["id"], ctg["id"]) 
        self.assertTrue(found != None)
        self.assertTrue(found["name"] == "categoryname")
        self.assertTrue("groupid1" in found["packagegroupids"])


    def test_remove_group_category(self):
        repo = self.rapi.create('test_remove_group_category',
                'test_remove_group_category', 'i386',
                'yum:http://example.com/')
        # Parse existing comps.xml
        compspath = os.path.join(self.dataPath, "rhel-i386-server-5/comps.xml")
        compsfile = open(compspath)
        base = BaseSynchronizer(self.config)
        base.import_groups_data(compsfile, repo)
        # 'repo' object should now contain groups/categories
        # we need to save it to the db so we can query from it
        self.rapi.update(repo)
        # Testing for expected values
        found = self.rapi.packagegroup(repo['id'], "web-server")
        self.assertTrue(found != None)
        found = self.rapi.packagegroupcategory(repo['id'], "development")
        self.assertTrue(found != None)
        # Test Removal
        self.rapi.remove_packagegroup(repo['id'], "web-server")
        found = self.rapi.packagegroup(repo['id'], "web-server")
        self.assertTrue(found == None)
        self.rapi.remove_packagegroupcategory(repo['id'], "development")
        found = self.rapi.packagegroupcategory(repo['id'], "development")
        self.assertTrue(found == None)


    def test_model_group_to_yum_group(self):
        """
        Test translation of model.PackageGroup to yum.comps.Group
        """
        grp = pulp.model.PackageGroup("groupid1", "groupname1", 
            "description", "user_visible", "display_order", "default"
            "langonly")
        grp['mandatory_package_names'] = ["mandatory_package_name1"]
        grp['optional_package_names'] = ["optional_package_name1"]
        grp['default_package_names'] = ["default_package_name1"]
        grp['conditional_package_names'] = {"pkg1":"value pkg1"}
        grp['translated_name'] = {"a":"value"}
        grp['translated_description'] = {"b":"value"}
        yumGrp = pulp.comps_util.model_group_to_yum_group(grp)
        self.assertTrue(yumGrp.groupid == "groupid1")
        self.assertTrue("mandatory_package_name1" in yumGrp.mandatory_packages)
        xml = yumGrp.xml()
        log.debug("Group XML = %s" % (xml))
        self.assertTrue(len(xml) > 0)

    def test_model_category_to_yum_category(self):
        """
        Test translation of model.PackageGroupCategory to yum.comps.Category
        """
        ctg = pulp.model.PackageGroupCategory("categoryid1", 
                    "categoryname", "description", "display_order")
        ctg['packagegroupids'] = ["groupid1"]
        ctg['translated_name'] = {"a":"name"}
        ctg['translated_description'] = {"b":"description"}
        yumCat = pulp.comps_util.model_category_to_yum_category(ctg)
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
        compsPath = os.path.join(self.dataPath, "rhel-i386-server-5/comps.xml")
        comps = yum.comps.Comps()
        comps.add(compsPath)
        self.assertTrue(len(comps.get_groups()) != 0)
        self.assertTrue(len(comps.get_categories()) != 0)

        # Create empty repo, we will populate it with our groups/categories
        repo = self.rapi.create('test_comps_id','test_comps_name', 
                'i386', 'yum:http://example.com/')
        found = self.rapi.packagegroups(repo['id'])
        self.assertTrue(len(found) == 0)
        found = self.rapi.packagegroupcategories(repo['id'])
        self.assertTrue(len(found) == 0)

        # Create Groups/Categories from parsed data
        grp_list = []
        for g in comps.get_groups():
            grp = pulp.comps_util.yum_group_to_model_group(g)
            self.assertTrue(grp != None)
            grp_list.append(grp)
        self.rapi.update_packagegroups(repo['id'], grp_list)
        ctg_list = []
        for c in comps.get_categories():
            ctg = pulp.comps_util.yum_category_to_model_category(c)
            self.assertTrue(ctg != None)
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
        self.assertTrue(found == None)
        found = self.rapi.packagegroup(repo['id'], "web-server")
        self.assertTrue(found != None)
        self.assertTrue("httpd" in found['mandatory_package_names'])
        self.assertTrue("mod_auth_kerb" in found['optional_package_names'])
        self.assertTrue("mod_auth_mysql" in found['optional_package_names'])
        self.assertTrue("crypto-utils" in found['default_package_names'])
        self.assertTrue("distcache" in found['default_package_names'])

        # PackageGroupCategory, look up expected values,
        found = self.rapi.packagegroupcategory(repo['id'], "BAD_VALUE_NOT_IN_CATEGORY")
        self.assertTrue(found == None)
        found = self.rapi.packagegroupcategory(repo['id'], "development")
        self.assertTrue(found != None)


        # Look up groups/categories from repo api
        ctgs = self.rapi.packagegroupcategories(repo["id"])
        grps = self.rapi.packagegroups(repo["id"])

        xml = pulp.comps_util.form_comps_xml(ctgs, grps)
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
        self.assertTrue(foundGroup != None)
        self.assertTrue("httpd" in foundGroup.mandatory_packages)
        self.assertTrue("mod_auth_kerb" in foundGroup.optional_packages)
        self.assertTrue("mod_auth_mysql" in foundGroup.optional_packages)
        self.assertTrue("crypto-utils" in foundGroup.default_packages)
        self.assertTrue("distcache" in foundGroup.default_packages)
        # Clean up file if tests have passed, 
        # leave file for debugging if tests failed
        os.unlink(f_name)

