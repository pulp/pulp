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
import unittest
import logging

import yum

import pulp.util
import pulp.model
from pulp.api.repo import RepoApi
from pulp.api.repo_sync import BaseSynchronizer

class TestComps(unittest.TestCase):

    def setUp(self):
        config_file = os.path.join(srcdir, "../etc/pulp/pulp.ini")
        self.config = pulp.util.load_config(config_file)
        self.rapi = RepoApi(self.config)
        self.rapi.clean()
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

    def broken_intend_this_to_run_full_read_write_out_to_xml(self):
        """
        Test full cycle of Groups/Categories, import a comps.xml, parse it
        modify the entries, then write them out to XML
        """
        #TODO: Writing to XML is broken 
        # Parse existing comps.xml
        compsPath = "./data/rhel-i386-server-5/comps.xml"
        comps = yum.comps.Comps()
        comps.add(compsPath)
        self.assertTrue(len(comps.get_groups()) != 0)
        self.assertTrue(len(comps.get_categories()) != 0)
        # Create Groups/Categories from parsed data
        repo = self.rapi.create('test_comps_id','test_comps_name', 
                'i386', 'yum:http://example.com/')
        found = self.rapi.packagegroups(repo['id'])
        self.assertTrue(len(found) == 0)
        found = self.rapi.packagegroupcategories(repo['id'])
        self.assertTrue(len(found) == 0)

        grp_list = []
        groupids = []
        for g in comps.get_groups():
            grp = pulp.model.PackageGroup(g.groupid, g.name, 
                    g.description, g.user_visible, g.display_order, g.default, 
                    g.langonly)
            grp['mandatory_package_names'].extend(g.mandatory_packages.keys())
            grp['optional_package_names'].extend(g.optional_packages.keys())
            grp['default_package_names'].extend(g.default_packages.keys())
            grp['conditional_package_names'] = g.conditional_packages
            grp['translated_name'] = g.translated_name
            grp['translated_description'] = g.translated_description
            grp_list.append(grp)
            groupids.append(grp['id'])
        self.rapi.update_packagegroups(repo['id'], grp_list)
        ctg_list = []
        categoryids = []
        for c in comps.get_categories():
            ctg = pulp.model.PackageGroupCategory(c.categoryid, 
                    c.name, c.description, c.display_order)
            groupids = [grp for grp in c.groups]
            ctg['packagegroupids'].extend(groupids)
            ctg['translated_name'] = c.translated_name
            ctg['translated_description'] = c.translated_description
            ctg_list.append(ctg)
            categoryids.append(ctg['id'])
        self.rapi.update_packagegroupcategories(repo['id'], ctg_list)
        # Lookup data from API calls
        found = self.rapi.packagegroups(repo['id'])
        self.assertTrue(len(found) > 0)
        found = self.rapi.packagegroupcategories(repo['id'])
        self.assertTrue(len(found) > 0)
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
        # Test Removal
        self.rapi.remove_packagegroup(repo['id'], "web-server")
        found = self.rapi.packagegroup(repo['id'], "web-server")
        self.assertTrue(found == None)
        self.rapi.remove_packagegroupcategory(repo['id'], "development")
        found = self.rapi.packagegroupcategory(repo['id'], "development")
        self.assertTrue(found == None)

        newComps = yum.comps.Comps()
        # Look up categories from a repo
        ctgs = self.rapi.packagegroupcategories(repo["id"])
        grps = self.rapi.packagegroups(repo["id"])

        for cid in ctgs:
            category = self.rapi.translate_packagegroupcategory(ctgs[cid])
            newComps.add_category(category)
        for gid in grps:
            pkggrp = self.rapi.translate_packagegroup(grps[gid])
            newComps.add_group(pkggrp)
        # Write back to xml
        xml = newComps.xml()
        print "Generated XML = %s" % (xml)
        self.assertTrue(True)




