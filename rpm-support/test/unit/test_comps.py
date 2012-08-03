# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import mock
import os
import random
import shutil
import sys
import tempfile
import unittest
import yum
from pulp.plugins.model import Repository, Unit
from pulp_rpm.yum_plugin import comps_util, util
from pulp.server.db import connection


sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/distributors/")

import distributor_mocks
import importer_mocks
import rpm_support_base
from yum_distributor.distributor import YumDistributor
from yum_importer import comps
from yum_importer.comps import ImporterComps
from yum_importer.importer import YumImporter
from pulp_rpm.common.ids import METADATA_PKG_GROUP, METADATA_PKG_CATEGORY, TYPE_ID_PKG_GROUP, TYPE_ID_PKG_CATEGORY
from pulp_rpm.yum_plugin import comps_util



class TestComps(rpm_support_base.PulpRPMTests):

    def setUp(self):
        super(TestComps, self).setUp()
        self.data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
        self.temp_dir = tempfile.mkdtemp()
        self.pkg_dir = os.path.join(self.temp_dir, "packages")
        if not os.path.exists(self.pkg_dir):
            os.makedirs(self.pkg_dir)
        self.working_dir = os.path.join(self.temp_dir, "working")
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)

    def tearDown(self):
        super(TestComps, self).tearDown()
        shutil.rmtree(self.temp_dir)

    def create_dummy_pkg_group_unit(self, repo_id, pkg_grp_id):
        random_int = int(random.random())
        type_id = TYPE_ID_PKG_GROUP
        unit_key = {}
        unit_key["id"] = pkg_grp_id
        unit_key["repo_id"] = repo_id
        metadata = {}
        metadata["name"] = "name_%s" % (random_int)
        metadata["description"] = "description_%s" % (random_int)
        metadata["default"] = True
        metadata["user_visible"] = True
        metadata["langonly"] = "1"
        metadata["display_order"] = 1
        metadata["mandatory_package_names"] = ["test_mand_pkg_name_%s" % (random_int)]
        metadata["conditional_package_names"] = [
                    ("test_pkg_name_cond_1",["value%s"%(random.random()), "value_%s" % (random.random())])
                ]
        metadata["optional_package_names"] = ["test_opt_pkg_name_%s" % (random_int)]
        metadata["default_package_names"] = ["test_default_pkg_name_%s" % (random_int)]
        metadata["translated_description"] = {}
        metadata["translated_name"] = {}
        path = None
        return Unit(type_id, unit_key, metadata, path)
        
    def create_dummy_pkg_category_unit(self, repo_id, pkg_cat_id, grpids):
        random_int = int(random.random())
        type_id = TYPE_ID_PKG_CATEGORY
        unit_key = {}
        unit_key["id"] = pkg_cat_id
        unit_key["repo_id"] = repo_id
        metadata = {}
        metadata["name"] = "name_%s" % (random_int)
        metadata["description"] = "description_%s" % (random_int)
        metadata["display_order"] = 1
        metadata["translated_name"] = ""
        metadata["translated_description"] = ""
        metadata["packagegroupids"] = grpids
        path = None
        return Unit(type_id, unit_key, metadata, path)


    def test_skip_packagegroups(self):
        global updated_progress
        updated_progress = None

        def set_progress(progress):
            global updated_progress
            updated_progress = progress

        yi = YumImporter()
        skip = ["packagegroup"]
        repo_src_dir = os.path.join(self.data_dir, "pulp_unittest")
        feed_url = "file://%s" % (repo_src_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url,skip_content_types=skip)
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_skip_packagegroup"
        # Simulate a repo sync, copy the source contents to the repo.working_dir
        self.simulate_sync(repo, repo_src_dir)

        sync_conduit = importer_mocks.get_sync_conduit(pkg_dir=self.pkg_dir)
        sync_conduit.set_progress = mock.Mock()
        sync_conduit.set_progress = set_progress
        status, summary, details = yi._sync_repo(repo, sync_conduit, config)
        self.assertTrue(status)
        self.assertEqual(updated_progress["comps"]["state"], "SKIPPED")

    def test_sync_groups_no_metadata_present(self):
        global updated_progress
        updated_progress = None

        def set_progress(status_type, progress):
            global updated_progress
            updated_progress = progress

        ic = ImporterComps()
        feed_url = "file://%s/simple_repo_no_comps" % (self.data_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_sync_groups_no_metadata_present"
        sync_conduit = importer_mocks.get_sync_conduit(pkg_dir=self.pkg_dir)
        status, summary, details = ic.sync(repo, sync_conduit, config, set_progress)
        self.assertTrue(status)
        self.assertEqual(updated_progress["state"], "FINISHED")
        self.assertEqual(summary["num_available_groups"], 0)
        self.assertEqual(summary["num_available_categories"], 0)
        self.assertEqual(summary["num_orphaned_groups"], 0)
        self.assertEqual(summary["num_orphaned_categories"], 0)
        self.assertEqual(summary["num_new_groups"], 0)
        self.assertEqual(summary["num_new_categories"], 0)
        self.assertTrue(summary["time_total_sec"] > 0)

    def test_basic_sync_groups(self):
        global updated_progress
        updated_progress = None

        def set_progress(status_type, progress):
            global updated_progress
            updated_progress = progress

        ic = ImporterComps()
        repo_src_dir = os.path.join(self.data_dir, "pulp_unittest")
        feed_url = "file://%s" % (repo_src_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        repo = mock.Mock(spec=Repository)
        repo.id = "test_basic_sync_groups"
        repo.working_dir = self.working_dir
        # Simulate a repo sync, copy the source contents to the repo.working_dir
        self.simulate_sync(repo, repo_src_dir)

        sync_conduit = importer_mocks.get_sync_conduit(pkg_dir=self.pkg_dir)
        status, summary, details = ic.sync(repo, sync_conduit, config, set_progress)
        self.assertTrue(status)
        self.assertEqual(summary["num_available_groups"], 3)
        self.assertEqual(summary["num_available_categories"], 2)
        self.assertEqual(summary["num_new_groups"], 3)
        self.assertEqual(summary["num_new_categories"], 2)
        self.assertEqual(summary["num_orphaned_groups"], 0)
        self.assertEqual(summary["num_orphaned_categories"], 0)
        self.assertTrue(summary["time_total_sec"] > 0)

    def test_get_groups_metadata_file(self):
        repodata_dir = os.path.join(self.data_dir, "simple_repo_no_comps")
        md_file, md_type = comps.get_groups_metadata_file(repodata_dir)
        self.assertTrue(md_file == None)
        self.assertTrue(md_type == None)

        repodata_dir = os.path.join(self.data_dir, "pulp_unittest")
        md_file, md_type = comps.get_groups_metadata_file(repodata_dir)
        self.assertEquals(md_file, "repodata/comps.xml")
        self.assertEqual(md_type, "group")

        repodata_dir = os.path.join(self.data_dir, "pulp_unittest")
        md_file, md_type = comps.get_groups_metadata_file(repodata_dir, md_types=["group"])
        self.assertEquals(md_file, "repodata/comps.xml")
        self.assertEqual(md_type, "group")

        repodata_dir = os.path.join(self.data_dir, "pulp_unittest")
        md_file, md_type = comps.get_groups_metadata_file(repodata_dir, md_types=["group_gz"])
        self.assertEquals(md_file, "repodata/comps.xml.gz")
        self.assertEqual(md_type, "group_gz")

    def test_get_available_with_no_group_data_present(self):
        groups, categories = comps.get_available(None)
        self.assertEquals(groups, {})
        self.assertEquals(categories, {})

        bad_data = os.path.join(self.data_dir, "simple_repo_no_comps")
        groups, categories = comps.get_available(bad_data)
        self.assertEqual(groups, {})
        self.assertEqual(categories, {})

    def test_get_available(self):
        # Test with a valid comps.xml
        repo_dir = os.path.join(self.data_dir, "pulp_unittest")
        self.assertTrue(os.path.exists(repo_dir))
        groups, categories = comps.get_available(repo_dir, md_types=["group"])
        self.assertEqual(len(groups), 3)
        self.assertEqual(len(categories), 2)
        for g in groups.values():
            keys = g.keys()
            for key_name in METADATA_PKG_GROUP:
                self.assertTrue(key_name in keys)
        for c in categories.values():
            keys = c.keys()
            for key_name in METADATA_PKG_CATEGORY:
                self.assertTrue(key_name in keys)

        repo_dir = os.path.join(self.data_dir, "pulp_unittest")
        self.assertTrue(os.path.exists(repo_dir))
        groups, categories = comps.get_available(repo_dir, md_types=["foo", "bar"])
        self.assertEqual(len(groups), 0)
        self.assertEqual(len(categories), 0)
        for g in groups.values():
            keys = g.keys()
            for key_name in METADATA_PKG_GROUP:
                self.assertTrue(key_name in keys)
        for c in categories.values():
            keys = c.keys()
            for key_name in METADATA_PKG_CATEGORY:
                self.assertTrue(key_name in keys)

        repo_dir = os.path.join(self.data_dir, "pulp_unittest")
        self.assertTrue(os.path.exists(repo_dir))
        groups, categories = comps.get_available(repo_dir)
        self.assertEqual(len(groups), 3)
        self.assertEqual(len(categories), 2)
        for g in groups.values():
            keys = g.keys()
            for key_name in METADATA_PKG_GROUP:
                self.assertTrue(key_name in keys)
        for c in categories.values():
            keys = c.keys()
            for key_name in METADATA_PKG_CATEGORY:
                self.assertTrue(key_name in keys)

    def test_get_available_with_gzipped_comps(self):
        # Test with a valid gzipped comps.xml.gz
        repo_dir = os.path.join(self.data_dir, "pulp_unittest")
        self.assertTrue(os.path.exists(repo_dir))
        groups, categories = comps.get_available(repo_dir, md_types=["group_gz"])
        self.assertEqual(len(groups), 3)
        self.assertEqual(len(categories), 2)

        for g in groups.values():
            keys = g.keys()
            for key_name in METADATA_PKG_GROUP:
                self.assertTrue(key_name in keys)
        for c in categories.values():
            keys = c.keys()
            for key_name in METADATA_PKG_CATEGORY:
                self.assertTrue(key_name in keys)

    def test_get_orphaned(self):
        # Creating dummy group data, the 'key' is the only piece of data needed
        # for this test.
        available_groups = {"group_1":"blah", "group_2":"blah"}
        existing_groups = {"group_1":"blah", "group_2":"blah", "group_3":"blah"}
        orphaned_groups = comps.get_orphaned_groups(available_groups, existing_groups)
        self.assertEqual(len(orphaned_groups), 1)
        self.assertTrue("group_3" in orphaned_groups)
        self.assertEqual(orphaned_groups["group_3"], "blah")

    def test_sync_of_orphaned_data(self):
        # Sync repo with some initial data
        # Modify the underlying directory to make it look like source has changed
        # Re-sync
        # Verify orphaned groups/categories were removed
        ic = ImporterComps()
        repo_src_dir = os.path.join(self.data_dir, "test_orphaned_data_initial")
        feed_url = "file://%s" % (repo_src_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        repo = mock.Mock(spec=Repository)
        repo.id = "test_sync_of_orphaned_data"
        repo.working_dir = self.working_dir
        # Simulate a repo sync, copy the source contents to the repo.working_dir
        self.simulate_sync(repo, repo_src_dir)

        sync_conduit = importer_mocks.get_sync_conduit()
        status, summary, details = ic.sync(repo, sync_conduit, config)
        self.assertTrue(status)
        self.assertEqual(summary["num_available_groups"], 3)
        self.assertEqual(summary["num_available_categories"], 2)
        self.assertEqual(summary["num_new_groups"], 3)
        self.assertEqual(summary["num_new_categories"], 2)
        self.assertEqual(summary["num_orphaned_groups"], 0)
        self.assertEqual(summary["num_orphaned_categories"], 0)
        self.assertTrue(summary["time_total_sec"] > 0)
        #
        # Simulate the existing_units 
        #
        avail_groups, avail_cats = comps.get_available(repo_src_dir)
        existing_cats, existing_cat_units = comps.get_new_category_units(avail_cats, {}, sync_conduit, repo)
        existing_groups, existing_group_units = comps.get_new_group_units(avail_groups, {}, sync_conduit, repo)
        self.assertEquals(len(existing_cats), 2)
        self.assertEquals(len(existing_groups), 3)

        existing_units = []
        existing_units.extend(existing_group_units.values())
        existing_units.extend(existing_cat_units.values())
        self.assertEquals(len(existing_units), (len(existing_cats) + len(existing_groups)))
        # 
        # Now we will simulate a change to the feed and pass in our existing units
        #
        repo_src_dir = os.path.join(self.data_dir, "test_orphaned_data_final")
        feed_url = "file://%s" % (repo_src_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=existing_units)
        self.simulate_sync(repo, repo_src_dir)
        status, summary, details = ic.sync(repo, sync_conduit, config)

        self.assertTrue(status)
        self.assertEqual(summary["num_available_groups"], 2)
        self.assertEqual(summary["num_available_categories"], 1)
        self.assertEqual(summary["num_new_groups"], 0)
        self.assertEqual(summary["num_new_categories"], 0)
        self.assertEqual(summary["num_orphaned_groups"], 1)
        self.assertEqual(summary["num_orphaned_categories"], 1)
        self.assertTrue(summary["time_total_sec"] > 0)

    def test_form_comps_xml(self):
        # Form several package groups and categories
        repo_src_dir = os.path.join(self.data_dir, "pulp_unittest")
        avail_groups, avail_cats = comps.get_available(repo_src_dir)
        # Translate the dicts into units
        repo = mock.Mock(spec=Repository)
        repo.id = "test_form_comps_xml"
        repo.working_dir = self.working_dir
        sync_conduit = importer_mocks.get_sync_conduit()
        initial_cats, initial_cat_units = comps.get_new_category_units(avail_cats, {}, sync_conduit, repo)
        initial_groups, initial_group_units = comps.get_new_group_units(avail_groups, {}, sync_conduit, repo)
        # Write these to a comps.xml
        comps_xml = comps_util.form_comps_xml_from_units(initial_group_units.values(), initial_cat_units.values())
        out_path = os.path.join(self.temp_dir, "test_form_comps.xml")
        f = open(out_path, "w")
        try:
            f.write(comps_xml)
        finally:
            f.close()
        # Read in comps.xml and parse
        final_groups, final_cats = comps.get_available(repo_src_dir, group_file=out_path, group_type='group')
        final_cats, final_cat_units = comps.get_new_category_units(final_cats, {}, sync_conduit, repo)
        final_groups, final_group_units = comps.get_new_group_units(final_groups, {}, sync_conduit, repo)
        # Verify we get the same data back
        self.assertEquals(len(initial_group_units), len(final_group_units))
        self.assertEquals(len(initial_cat_units), len(final_cat_units))
        # Examine Package Group Data
        for grp_key in initial_group_units:
            initial_unit = initial_group_units[grp_key]
            final_unit = final_group_units[grp_key]
            self.assertEquals(len(initial_unit.unit_key), len(final_unit.unit_key))
            self.assertEquals(len(initial_unit.metadata), len(final_unit.metadata))
            # Verify unit keys are same
            for key in initial_unit.unit_key:
                self.assertEquals(initial_unit.unit_key[key], final_unit.unit_key[key])
            for key in initial_unit.metadata:
                self.assertEquals(initial_unit.metadata[key], final_unit.metadata[key])

    def test_publish_comps(self):
        repo = mock.Mock(spec=Repository)
        repo.id = "test_publish_comps"
        repo.working_dir = self.working_dir
        # Create 2 pkg groups
        grp_a = self.create_dummy_pkg_group_unit(repo.id, "group_a")
        grp_b = self.create_dummy_pkg_group_unit(repo.id, "group_b")
        # Create 2 pkg categories
        cat_a = self.create_dummy_pkg_category_unit(repo.id, "cat_a", ["group_a"])
        cat_b = self.create_dummy_pkg_category_unit(repo.id, "cat_b", ["group_b"])
        # Add the grps/cats to the publish_conduit
        publish_conduit = distributor_mocks.get_publish_conduit(
                existing_units=[grp_a, grp_b, cat_a, cat_b])
        config = distributor_mocks.get_basic_config(relative_url=repo.id, 
                http=True, https=True, generate_metadata=True)
        # Publish the repo, be sure 'generate_metadata' is True
        yum_distributor = YumDistributor()
        report = yum_distributor.publish_repo(repo, publish_conduit, config)
        self.assertTrue(report.success_flag)
        self.assertEqual(report.summary["num_package_groups_published"], 2)
        self.assertEqual(report.summary["num_package_categories_published"], 2)
        expected_comps_xml = os.path.join(repo.working_dir, "comps.xml")
        self.assertTrue(os.path.exists(expected_comps_xml))
        #
        # Find the path that createrepo added the comps.xml as
        #
        repomd_xml = os.path.join(repo.working_dir, "repodata", "repomd.xml")
        self.assertTrue(os.path.exists(repomd_xml))
        md_types = util.get_repomd_filetypes(repomd_xml)
        self.assertTrue('group' in md_types)
        groups_path = util.get_repomd_filetype_path(repomd_xml, "group")
        self.assertTrue(groups_path)
        groups_path = os.path.join(repo.working_dir, groups_path)
        self.assertTrue(os.path.exists(groups_path))
        #
        # Use yum to read the repodata and verify the info written matches
        # our dummy data
        #
        yc = yum.comps.Comps()
        yc.add(groups_path)
        self.assertEqual(len(yc.groups), 2)
        self.assertEqual(len(yc.categories), 2)
        for g in yc.groups:
            eg = None
            if g.groupid == "group_a":
                eg = grp_a
            elif g.groupid == "group_b":
                eg = grp_b
            else:
                # Unexpected error
                self.assertTrue(False)
            self.assertEqual(g.name, eg.metadata["name"])
            self.assertEqual(g.description, eg.metadata["description"])
            self.assertEqual(g.user_visible, eg.metadata["user_visible"])
            self.assertEqual(g.display_order, eg.metadata["display_order"])
            self.assertEqual(g.default, eg.metadata["default"])
            self.assertEqual(g.langonly, eg.metadata["langonly"])
            for pkg_name in g.mandatory_packages:
                self.assertTrue(pkg_name in eg.metadata["mandatory_package_names"])
            for pkg_name in g.optional_packages:
                self.assertTrue(pkg_name in eg.metadata["optional_package_names"])
            for pkg_name in g.default_packages:
                self.assertTrue(pkg_name in eg.metadata["default_package_names"])
            #
            # Below is related to pymongo not liking dots in a pkg_name
            # We are storing conditional_package_names as a list of tuples, (name, values)
            # convert to a dictionary to make it easier to compare against yum's data
            #
            cond_lookup = {}
            for expected_name, expected_values in eg.metadata["conditional_package_names"]:
                cond_lookup[expected_name] = expected_values
            for pkg_name in g.conditional_packages:
                # We are converting our expected value to a str below to match the behavior
                # we see from yum
                self.assertEqual(g.conditional_packages[pkg_name], str(cond_lookup[pkg_name]))
        for c in yc.categories:
            ec = None
            if c.categoryid == "cat_a":
                ec = cat_a
            elif c.categoryid == "cat_b":
                ec = cat_b
            else:
                # Unexpected error
                self.assertTrue(False)
            self.assertEqual(c.name, ec.metadata["name"])
            self.assertEqual(c.description, ec.metadata["description"])
            self.assertEqual(c.display_order, ec.metadata["display_order"])
            self.assertEqual(len(c._groups), len(ec.metadata["packagegroupids"]))
            for grpid in c._groups:
                self.assertTrue(grpid in ec.metadata["packagegroupids"])
        # Verify the pkg group/category info is correct

    def test_comps_import_with_dots_in_pkg_names(self):
        # Test we are able to save problematic package groups/categories to mongo
        db = connection.database()
        dummy_collection_name = "unit_test_dummy_data"
        dummy_collection = getattr(db, dummy_collection_name)

        # Import from a CentOS 6 comps.xml containing:
        # http://mirror.centos.org/centos/6/os/x86_64/repodata/3a27232698a261aa4022fd270797a3006aa8b8a346cbd6a31fae1466c724d098-c6-x86_64-comps.xml
        # <packagereq requires="openoffice.org-core" type="conditional">openoffice.org-langpack-en</packagereq>
        # We were seeing exceptions like below:
        #    InvalidDocument: key 'openoffice.org-langpack-en' must not contain '.'
        success = False
        try:
            repo_src_dir = os.path.join(self.data_dir, "test_comps_import_with_dots_in_pkg_names")
            avail_groups, avail_cats = comps.get_available(repo_src_dir)
            for grp in avail_groups.values():
                dummy_collection.save(grp, safe=True)
            for cat in avail_cats.values():
                dummy_collection.save(cat, safe=True)
            success = True
        finally:
            db.drop_collection(dummy_collection_name)
        self.assertTrue(success)

    def test_write_comps_with_centos6_comps_xml(self):
            repo = mock.Mock(spec=Repository)
            repo.id = "test_write_comps_with_i18n_data"
            repo.working_dir = self.working_dir
            sync_conduit = importer_mocks.get_sync_conduit()
            repo_src_dir = os.path.join(self.data_dir, "test_comps_import_with_dots_in_pkg_names")
            # Simulate a sync with CentOS 6 comps.xml data
            # The test data contains issues such as:
            #  1) conditional_package_names that contain a '.' in the key name
            #     InvalidDocument: key 'openoffice.org-langpack-en' must not contain '.'
            #  2) unicode strings which are not being encoded correctly during write
            #     UnicodeEncodeError: 'ascii' codec can't encode characters in position 334-341: ordinal not in range(128)
            avail_groups, avail_cats = comps.get_available(repo_src_dir)
            groups, group_units = comps.get_new_group_units(avail_groups, {}, sync_conduit, repo)
            cats, cat_units = comps.get_new_category_units(avail_cats, {}, sync_conduit, repo)
            yum_distributor = YumDistributor()
            comps_xml_out_path = comps_util.write_comps_xml(repo, group_units.values(), cat_units.values())
            self.assertEqual(comps_xml_out_path, os.path.join(repo.working_dir, "comps.xml"))
            yc = yum.comps.Comps()
            yc.add(comps_xml_out_path)
            self.assertTrue(len(group_units), len(yc.groups))
            self.assertTrue(len(cat_units), len(yc.categories))

