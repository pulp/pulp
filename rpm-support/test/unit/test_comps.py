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

import importer_mocks
import rpm_support_base
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

    def test_get_available_over(self):
        # Test with a valid comps.xml
        repo_dir = os.path.join(self.data_dir, "pulp_unittest")
        self.assertTrue(os.path.exists(repo_dir))
        groups, categories = comps.get_available(repo_dir, md_types=["group"])
        self.assertEqual(len(groups), 3)
        self.assertEqual(len(categories), 2)

        repo_dir = os.path.join(self.data_dir, "pulp_unittest")
        self.assertTrue(os.path.exists(repo_dir))
        groups, categories = comps.get_available(repo_dir, md_types=["foo", "bar"])
        self.assertEqual(len(groups), 0)
        self.assertEqual(len(categories), 0)

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
        pass

    def test_resync_removes_group(self):
        pass

    def test_resync_removes_category(self):
        pass

    def test_resync_adds_group(self):
        pass

    def test_resync_adds_category(self):
        pass

    def test_resync_no_change(self):
        pass

    def test_cancel_sync(self):
        pass

