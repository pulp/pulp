#!/usr/bin/python
#
# Copyright (c) 2012 Red Hat, Inc.
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

import os
import unittest
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../importers/yum_importer/")
import mock

from importer import YumImporter
from importer import YUM_IMPORTER_TYPE_ID, RPM_TYPE_ID, RPM_UNIT_KEY

from pulp.server.content.conduits.repo_sync import RepoSyncConduit
from pulp.server.content.plugins.config import PluginCallConfiguration
from pulp.server.content.plugins.model import Repository, Unit

class TestYumImporter(unittest.TestCase):

    def setUp(self):
        super(TestYumImporter, self).setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = os.path.join(self.temp_dir, "working")
        self.pkg_dir = os.path.join(self.temp_dir, "packages")

    def tearDown(self):
        super(TestYumImporter, self).tearDown()
        shutil.rmtree(self.temp_dir)

    def test_metadata(self):
        metadata = YumImporter.metadata()
        self.assertEquals(metadata["id"], YUM_IMPORTER_TYPE_ID)
        self.assertTrue(RPM_TYPE_ID in metadata["types"])

    def get_sync_conduit(self, existing_units=None):
        def side_effect(type_id, key, metadata, rel_path):
            rel_path = os.path.join(self.pkg_dir, rel_path)
            unit = Unit(type_id, key, metadata, rel_path)
            return unit
        sync_conduit = mock.Mock(spec=RepoSyncConduit)
        sync_conduit.get_units = mock.Mock()
        if not existing_units:
            sync_conduit.get_units.return_value = []
        else:
            sync_conduit.get_units.return_value = existing_units

        sync_conduit.init_unit.side_effect = side_effect
        return sync_conduit

    def get_basic_config(self, feed_url, num_threads=1):
        def side_effect(arg):
            result = {
                    "feed_url":feed_url,
                    "num_threads":num_threads,
                    }
            if result.has_key(arg):
                return result[arg]
            return None
        config = mock.Mock(spec=PluginCallConfiguration)
        config.get.side_effect = side_effect
        return config

    def test_basic_sync(self):
        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
        importer = YumImporter()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_basic_sync"
        sync_conduit = self.get_sync_conduit()
        config = self.get_basic_config(feed_url)
        summary, details = importer._sync_repo(repo, sync_conduit, config)
        self.assertTrue(summary is not None)
        self.assertTrue(details is not None)
        self.assertEquals(summary["num_synced_new_rpms"], 3)
        self.assertEquals(summary["num_resynced_rpms"], 0)
        self.assertEquals(summary["num_not_synced_rpms"], 0)
        self.assertEquals(summary["num_orphaned_rpms"], 0)
        self.assertEquals(details["size_total"], 6791)

    def test_basic_orphaned_sync(self):
        importer = YumImporter()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_basic_sync"
        unit_key = {}
        for k in RPM_UNIT_KEY:
            unit_key[k] = "test_value"
        existing_units = [Unit(RPM_TYPE_ID, unit_key, "test_metadata", "test_rel_path")]
        sync_conduit = self.get_sync_conduit(existing_units=existing_units)
        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
        config = self.get_basic_config(feed_url)
        summary, details = importer._sync_repo(repo, sync_conduit, config)
        self.assertTrue(summary is not None)
        self.assertTrue(details is not None)
        self.assertEquals(summary["num_synced_new_rpms"], 3)
        self.assertEquals(summary["num_resynced_rpms"], 0)
        self.assertEquals(summary["num_not_synced_rpms"], 0)
        self.assertEquals(summary["num_orphaned_rpms"], 1)
        # Add a verification that sync_conduit.remove_unit was called for our orphaned unit
        # Test package removed from packages dir
        # Test package removed from working repo dir

    def test_basic_missing_file_sync(self):
        # Sync an existing repo
        # Remove rpm from packages dir
        # Verify a re-sync brings package back to packages dir
        pass

    def test_remove_old_packages(self):
        # Sent remove_old
        # Sync a repo that has 2 repos of same name, one new, one old
        # Verify that only new rpm was synced
        pass

    def test_skip_packages(self):
        # Set skip packages
        # Verify no rpms are downloaded
        pass
    
    def test_progress_sync(self):
        global updated_progress
        updated_progress = None

        def set_progress(progress):
            global updated_progress
            updated_progress = progress

        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
        importer = YumImporter()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_progress_sync"
        sync_conduit = self.get_sync_conduit()
        sync_conduit.set_progress = mock.Mock()
        sync_conduit.set_progress.side_effect = set_progress
        config = self.get_basic_config(feed_url)
        summary, details = importer._sync_repo(repo, sync_conduit, config)
        self.assertEquals(summary["num_synced_new_rpms"], 3)
        self.assertTrue(updated_progress is not None)
        for key in YumImporter.PROGRESS_REPORT_FIELDS:
            self.assertTrue(key in updated_progress)
