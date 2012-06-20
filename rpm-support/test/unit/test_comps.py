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
import shutil
import sys
import tempfile
import unittest
import yum
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/distributors/")

import importer_mocks
import rpm_support_base
from pulp_rpm.yum_plugin import comps_util
from yum_importer import comps
from yum_importer.comps import ImporterComps, PKG_GROUP_METADATA, PKG_CATEGORY_METADATA
from yum_importer.importer import YumImporter
from pulp.plugins.model import Repository, Unit

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

    def simulate_sync(self, repo, src):
        # Simulate a repo sync, copy the source contents to the repo.working_dir
        dst = os.path.join(repo.working_dir, repo.id)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    def tearDown(self):
        super(TestComps, self).tearDown()
        shutil.rmtree(self.temp_dir)

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
            for key_name in PKG_GROUP_METADATA:
                self.assertTrue(key_name in keys)
        for c in categories.values():
            keys = c.keys()
            for key_name in PKG_CATEGORY_METADATA:
                self.assertTrue(key_name in keys)

        repo_dir = os.path.join(self.data_dir, "pulp_unittest")
        self.assertTrue(os.path.exists(repo_dir))
        groups, categories = comps.get_available(repo_dir, md_types=["foo", "bar"])
        self.assertEqual(len(groups), 0)
        self.assertEqual(len(categories), 0)
        for g in groups.values():
            keys = g.keys()
            for key_name in PKG_GROUP_METADATA:
                self.assertTrue(key_name in keys)
        for c in categories.values():
            keys = c.keys()
            for key_name in PKG_CATEGORY_METADATA:
                self.assertTrue(key_name in keys)

        repo_dir = os.path.join(self.data_dir, "pulp_unittest")
        self.assertTrue(os.path.exists(repo_dir))
        groups, categories = comps.get_available(repo_dir)
        self.assertEqual(len(groups), 3)
        self.assertEqual(len(categories), 2)
        for g in groups.values():
            keys = g.keys()
            for key_name in PKG_GROUP_METADATA:
                self.assertTrue(key_name in keys)
        for c in categories.values():
            keys = c.keys()
            for key_name in PKG_CATEGORY_METADATA:
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
            for key_name in PKG_GROUP_METADATA:
                self.assertTrue(key_name in keys)
        for c in categories.values():
            keys = c.keys()
            for key_name in PKG_CATEGORY_METADATA:
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
        comps_xml = comps_util.form_comps_xml_from_units(initial_group_units, initial_cat_units)
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
