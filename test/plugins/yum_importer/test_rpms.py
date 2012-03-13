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

import glob
import mock
import os
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../plugins/importers/yum_importer/")
import importer_mocks
from importer import YumImporter
from importer import YUM_IMPORTER_TYPE_ID
from importer_rpm import RPM_TYPE_ID, RPM_UNIT_KEY
import importer_rpm

from pulp.server.content.plugins.model import Repository, Unit

class TestRPMs(unittest.TestCase):

    def setUp(self):
        super(TestRPMs, self).setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = os.path.join(self.temp_dir, "working")
        self.pkg_dir = os.path.join(self.temp_dir, "packages")

    def tearDown(self):
        super(TestRPMs, self).tearDown()
        #shutil.rmtree(self.temp_dir)

    def get_files_in_dir(self, pattern, path):
        files = []
        for d,_,_ in os.walk(path):
            files.extend(glob.glob(os.path.join(d,pattern))) 
        return files

    def test_metadata(self):
        metadata = YumImporter.metadata()
        self.assertEquals(metadata["id"], YUM_IMPORTER_TYPE_ID)
        self.assertTrue(RPM_TYPE_ID in metadata["types"])

    def get_simple_rpm(self, value=None):
        if not value:
            value = "test_value"
        rpm = {}
        for k in RPM_UNIT_KEY:
            rpm[k] = value
        for k in ("vendor", "description", "buildhost", "license", 
                "vendor", "requires", "provides", "pkgpath"):
            rpm[k] = value
        return rpm

    def test_basic_sync(self):
        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
        importer = YumImporter()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_basic_sync"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        summary, details = importer_rpm._sync(repo, sync_conduit, config)
        self.assertTrue(summary is not None)
        self.assertTrue(details is not None)
        self.assertEquals(summary["num_synced_new_rpms"], 3)
        self.assertEquals(summary["num_resynced_rpms"], 0)
        self.assertEquals(summary["num_not_synced_rpms"], 0)
        self.assertEquals(summary["num_orphaned_rpms"], 0)
        self.assertEquals(details["size_total"], 6791)
        # Confirm regular RPM files exist under self.pkg_dir
        pkgs = self.get_files_in_dir("*.rpm", self.pkg_dir)
        self.assertEquals(len(pkgs), 3)
        for p in pkgs:
            self.assertTrue(os.path.isfile(p))
        # Confirm symlinks to RPMs exist under repo.working_dir
        sym_links = self.get_files_in_dir("*.rpm", repo.working_dir)
        self.assertEquals(len(pkgs), 3)
        for link in sym_links:
            self.assertTrue(os.path.islink(link))

    def test_validate_config(self):
        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
        importer = YumImporter()
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        repo = mock.Mock(spec=Repository)
        state, msg = importer.validate_config(repo, config)
        self.assertTrue(state)

        # Ensure if we are missing a required argument validate fails and the missing 
        # config parameter is mentioned in the message
        config = importer_mocks.get_basic_config()
        state, msg = importer.validate_config(repo, config)
        self.assertFalse(state)
        self.assertTrue("feed_url" in msg)

        # Test that an unknown argument in the config throws an error 
        # and the unknown arg is identified in the message
        config = importer_mocks.get_basic_config(feed_url=feed_url, bad_unknown_arg="blah")
        state, msg = importer.validate_config(repo, config)
        self.assertFalse(state)
        self.assertTrue("bad_unknown_arg" in msg)

    def test_remove_packages(self):
        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
        importer = YumImporter()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_remove_packages"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        summary, details = importer_rpm._sync(repo, sync_conduit, config)
        self.assertEquals(summary["num_synced_new_rpms"], 3)
        self.assertEquals(len(self.get_files_in_dir("*.rpm", self.pkg_dir)), 3)
        self.assertEquals(len(self.get_files_in_dir("*.rpm", repo.working_dir)), 3)
        #print "RPMs should be at: %s" % (self.pkg_dir)
        #print "SymLinks should be at: %s" % (repo.working_dir)

    def test_basic_orphaned_sync(self):
        importer = YumImporter()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_basic_sync"
        unit_key = {}
        for k in RPM_UNIT_KEY:
            unit_key[k] = "test_value"
        existing_units = [Unit(RPM_TYPE_ID, unit_key, "test_metadata", os.path.join(self.pkg_dir, "test_rel_path"))]
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=existing_units, pkg_dir=self.pkg_dir)
        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        summary, details = importer_rpm._sync(repo, sync_conduit, config)
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
            if "Errata" not in progress["step"]:
                # We want to skip checking the fields for Errata steps
                for key in importer_rpm.PROGRESS_REPORT_FIELDS:
                    self.assertTrue(key in updated_progress)

        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
        importer = YumImporter()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_progress_sync"
        sync_conduit = importer_mocks.get_sync_conduit(pkg_dir=self.pkg_dir)
        sync_conduit.set_progress = mock.Mock()
        sync_conduit.set_progress.side_effect = set_progress
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        summary, details = importer._sync_repo(repo, sync_conduit, config)
        self.assertEquals(summary["num_synced_new_rpms"], 3)
        self.assertTrue(updated_progress is not None)
        self.assertTrue(updated_progress.has_key("step"))
        self.assertTrue(updated_progress["step"])

    def test_get_existing_units(self):
        unit_key = {}
        for k in RPM_UNIT_KEY:
            unit_key[k] = "test_value"
        existing_units = [Unit(RPM_TYPE_ID, unit_key, "test_metadata", os.path.join(self.pkg_dir, "test_rel_path"))]
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=existing_units, pkg_dir=self.pkg_dir)
        actual_existing_units = importer_rpm.get_existing_units(sync_conduit)
        self.assertEquals(len(actual_existing_units), 1)
        self.assertEquals(len(existing_units), len(actual_existing_units))
        lookup_key = importer_rpm.form_lookup_key(unit_key)
        self.assertEqual(existing_units[0], actual_existing_units[lookup_key])

    def test_get_available_rpms(self):
        rpm = {}
        for k in RPM_UNIT_KEY:
            rpm[k] = "test_value"
        available_rpms = importer_rpm.get_available_rpms([rpm])
        lookup_key = importer_rpm.form_lookup_key(rpm)
        self.assertEqual(available_rpms[lookup_key], rpm)

    def test_get_orphaned_units(self):
        # Create A & B, Orphan B
        unit_key_a = {}
        for k in RPM_UNIT_KEY:
            unit_key_a[k] = "test_value"
        unit_key_b = {}
        for k in RPM_UNIT_KEY:
            unit_key_b[k] = "test_value_b"
        unit_a = Unit(RPM_TYPE_ID, unit_key_a, "test_metadata", "test_rel_path")
        unit_b = Unit(RPM_TYPE_ID, unit_key_b, "test_metadata", "test_rel_path")
        existing_units = {
                importer_rpm.form_lookup_key(unit_key_a):unit_a, 
                importer_rpm.form_lookup_key(unit_key_b):unit_b
                }
        available_rpms = {}
        available_rpms[importer_rpm.form_lookup_key(unit_key_a)] = unit_key_a
        orphaned_units = importer_rpm.get_orphaned_units(available_rpms, existing_units)
        expected_orphan_key = importer_rpm.form_lookup_key(unit_key_b)
        self.assertEquals(len(orphaned_units), 1)
        self.assertTrue(expected_orphan_key in orphaned_units)

    def test_get_new_rpms_and_units(self):
        # 1 Existing RPM
        # 2 RPMs in available
        # Expected 1 New RPM
        rpm_a = self.get_simple_rpm("test_value_a")
        rpm_b = self.get_simple_rpm("test_value_b")
        rpm_lookup_key_a = importer_rpm.form_lookup_key(rpm_a)
        rpm_lookup_key_b = importer_rpm.form_lookup_key(rpm_b)
        available_rpms = {}
        available_rpms[rpm_lookup_key_a] = rpm_a
        available_rpms[rpm_lookup_key_b] = rpm_b

        unit_a = Unit(RPM_TYPE_ID, importer_rpm.form_rpm_unit_key(rpm_a), "test_metadata", "rel_path")
        existing_units = {}
        existing_units[rpm_lookup_key_a] = unit_a
        sync_conduit = importer_mocks.get_sync_conduit(pkg_dir=self.pkg_dir)
        new_rpms, new_units = importer_rpm.get_new_rpms_and_units(available_rpms, 
                existing_units, sync_conduit)
        self.assertEquals(len(new_rpms), 1)
        self.assertEquals(len(new_units), 1)
        self.assertTrue(rpm_lookup_key_b in new_rpms)
        self.assertTrue(rpm_lookup_key_b in new_units)
        self.assertEquals(new_rpms[rpm_lookup_key_b], rpm_b)
        #
        # Repeat test but now nothing is new
        #
        unit_b = Unit(RPM_TYPE_ID, importer_rpm.form_rpm_unit_key(rpm_b), "test_metadata", "rel_path_b")
        existing_units = {}
        existing_units[rpm_lookup_key_a] = unit_a
        existing_units[rpm_lookup_key_b] = unit_b
        new_rpms, new_units = importer_rpm.get_new_rpms_and_units(available_rpms, 
                existing_units, sync_conduit)
        self.assertEquals(len(new_rpms), 0)
        self.assertEquals(len(new_units), 0)
        #
        # Repeat test but now both rpms in available are new
        #
        existing_units = {}
        new_rpms, new_units = importer_rpm.get_new_rpms_and_units(available_rpms, 
                existing_units, sync_conduit)
        self.assertEquals(len(new_rpms), 2)
        self.assertEquals(len(new_units), 2)
        self.assertTrue(rpm_lookup_key_a in new_rpms)
        self.assertTrue(rpm_lookup_key_b in new_rpms)

    def test_get_missing_rpms_and_units(self):
        # 2 Existing RPMs, one is missing
        # Expecting return of the one missing rpm
        # Fake out the verify_exists
        def side_effect(arg):
            if arg == "rel_path_b":
                return False
            return True
        importer_rpm.verify_exists = mock.Mock()
        importer_rpm.verify_exists.side_effect = side_effect

        rpm_a = self.get_simple_rpm("test_value_a")
        rpm_b = self.get_simple_rpm("test_value_b")
        rpm_lookup_key_a = importer_rpm.form_lookup_key(rpm_a)
        rpm_lookup_key_b = importer_rpm.form_lookup_key(rpm_b)
        available_rpms = {}
        available_rpms[rpm_lookup_key_a] = rpm_a
        available_rpms[rpm_lookup_key_b] = rpm_b

        unit_a = Unit(RPM_TYPE_ID, importer_rpm.form_rpm_unit_key(rpm_a), "test_metadata", "rel_path_a")
        unit_b = Unit(RPM_TYPE_ID, importer_rpm.form_rpm_unit_key(rpm_b), "test_metadata", "rel_path_b")
        existing_units = {}
        existing_units[rpm_lookup_key_a] = unit_a
        existing_units[rpm_lookup_key_b] = unit_b

        missing_rpms, missing_units = importer_rpm.get_missing_rpms_and_units(available_rpms, 
                existing_units)
        self.assertEquals(len(missing_rpms), 1)
        self.assertEquals(len(missing_units), 1)
        self.assertTrue(rpm_lookup_key_b in missing_rpms)
        self.assertTrue(rpm_lookup_key_b in missing_units)
        self.assertEquals(missing_rpms[rpm_lookup_key_b], rpm_b)

    def test_remove_old_packages(self):
        feed_url = "http://jmatthews.fedorapeople.org/repo_multiple_versions/"
        importer = YumImporter()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_remove_old_packages"
        sync_conduit = importer_mocks.get_sync_conduit(pkg_dir=self.pkg_dir)
        ###
        # Test that old packages are not in rpmList and are never intended to be downloaded
        # Additionallity verify that already existing packages which are NOT orphaned are also
        # removed with remove_old functionality
        ###
        config = importer_mocks.get_basic_config(feed_url=feed_url, remove_old=False, num_old_packages=0)
        summary, details = importer_rpm._sync(repo, sync_conduit, config)
        self.assertEquals(summary["num_synced_new_rpms"], 12)
        pkgs = self.get_files_in_dir("*.rpm", self.pkg_dir)
        self.assertEquals(len(pkgs), 12)

        yumRepoGrinder = importer_rpm.get_yumRepoGrinder(repo.id, repo.working_dir, config)
        yumRepoGrinder.setup(basepath=repo.working_dir)
        rpm_items = yumRepoGrinder.getRPMItems()
        yumRepoGrinder.stop()
        del yumRepoGrinder
        self.assertEquals(len(rpm_items), 12)

        existing_units = []
        for rpm in rpm_items:
            u = Unit(RPM_TYPE_ID, 
                    importer_rpm.form_rpm_unit_key(rpm), 
                    importer_rpm.form_rpm_metadata(rpm),
                    os.path.join(self.pkg_dir, rpm["pkgpath"], rpm["fileName"]))
            existing_units.append(u)
        config = importer_mocks.get_basic_config(feed_url=feed_url, remove_old=True, num_old_packages=6)
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=existing_units, pkg_dir=self.pkg_dir)
        summary, details = importer_rpm._sync(repo, sync_conduit, config)
        self.assertEquals(summary["num_rpms"], 7)
        self.assertEquals(summary["num_orphaned_rpms"], 5)
        self.assertEquals(summary["num_synced_new_rpms"], 0)
        self.assertEquals(summary["num_not_synced_rpms"], 0)
        pkgs = self.get_files_in_dir("*.rpm", self.pkg_dir)
        self.assertEquals(len(pkgs), 7)

        config = importer_mocks.get_basic_config(feed_url=feed_url, remove_old=True, num_old_packages=0)
        summary, details = importer_rpm._sync(repo, sync_conduit, config)
        self.assertEquals(summary["num_rpms"], 1)
        self.assertEquals(summary["num_orphaned_rpms"], 11)
        self.assertEquals(summary["num_synced_new_rpms"], 0)
        self.assertEquals(summary["num_not_synced_rpms"], 0)
        pkgs = self.get_files_in_dir("*.rpm", self.pkg_dir)
        self.assertEquals(len(pkgs), 1)

    def test_srpm_sync(self):
        feed_url = "http://pkilambi.fedorapeople.org/test_srpm_repo/"
        importer = YumImporter()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_srpm_sync"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        summary, details = importer_rpm._sync(repo, sync_conduit, config)
        self.assertTrue(summary is not None)
        self.assertTrue(details is not None)
        self.assertEquals(summary["num_rpms"], 3)
        self.assertEquals(summary["num_synced_new_srpms"], 3)
        self.assertEquals(summary["num_synced_new_rpms"], 0)


