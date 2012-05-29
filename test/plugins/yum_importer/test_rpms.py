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
import pycurl
import shutil
import sys
import tempfile
import threading
import time
import unittest

from grinder.BaseFetch import BaseFetch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../plugins/importers/yum_importer/")
import importer_mocks
from importer import YumImporter
from importer import YUM_IMPORTER_TYPE_ID
from importer_rpm import RPM_TYPE_ID, RPM_UNIT_KEY
import importer_rpm
from pulp.yum_plugin import util

from pulp.server.content.plugins.model import Repository, Unit

class TestRPMs(unittest.TestCase):

    def setUp(self):
        super(TestRPMs, self).setUp()
        self.saved_verify_exists = util.verify_exists
        self.init()

    def tearDown(self):
        super(TestRPMs, self).tearDown()
        util.verify_exists = self.saved_verify_exists
        self.clean()

    def init(self):
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = os.path.join(self.temp_dir, "working")
        self.pkg_dir = os.path.join(self.temp_dir, "packages")
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "../data"))

    def clean(self):
        shutil.rmtree(self.temp_dir)

    def get_files_in_dir(self, pattern, path):
        files = []
        for d,_,_ in os.walk(path):
            files.extend(glob.glob(os.path.join(d,pattern))) 
        return files

    def get_expected_rpms_from_pulp_unittest(self, repo_label, pkg_dir=None, repo_working_dir=None):
        """
        @param repo_label label of repo, typically repo.id
        @type repo_label str

        @param pkg_dir: path of where packages are stored
        @type pkg_dir: str

        @param repo_working_dir: path of where symlinks to RPMs are stored
        @type repo_working_dir: str
        """
        if not pkg_dir:
            pkg_dir = self.pkg_dir
        if not repo_working_dir:
            repo_working_dir = self.working_dir
        rpms = {
                ('pulp-test-package', '0', '0.2.1', 'x86_64', 'pulp-test-package-0.2.1-1.fc11.x86_64.rpm', 'sha256', '4dbde07b4a8eab57e42ed0c9203083f1d61e0b13935d1a569193ed8efc9ecfd7'):{
                    'size': 2216, 
                    'vendor': '', 
                    'checksumtype': 'sha256', 
                    'license': 'MIT', 
                    'checksum': '4dbde07b4a8eab57e42ed0c9203083f1d61e0b13935d1a569193ed8efc9ecfd7', 
                    'description': 'Test package.  Nothing to see here.', 
                    'pkgpath': '%s/.//pulp-test-package/0.2.1/1.fc11/x86_64/4dbde07b4a8eab57e42ed0c9203083f1d61e0b13935d1a569193ed8efc9ecfd7' % (pkg_dir), 
                    'savepath': '%s/%s/' % (repo_working_dir, repo_label), 
                    'filename': 'pulp-test-package-0.2.1-1.fc11.x86_64.rpm', 
                    'downloadurl': 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/pulp-test-package-0.2.1-1.fc11.x86_64.rpm', 
                    'item_type': 'rpm', 
                    'epoch': '0', 
                    'version': '0.2.1', 
                    'arch': 'x86_64', 
                    'provides': [
                            ('pulp-test-package(x86-64)', 'EQ', ('0', '0.2.1', '1.fc11')), 
                            ('pulp-test-package', 'EQ', ('0', '0.2.1', '1.fc11')), 
                            ('config(pulp-test-package)', 'EQ', ('0', '0.2.1', '1.fc11'))
                            ], 
                    'relativepath': 'pulp-test-package-0.2.1-1.fc11.x86_64.rpm', 
                    'release': '1.fc11', 
                    'buildhost': 'gibson', 
                    'requires': [], 
                    'name': 'pulp-test-package'
                }, 
                ('pulp-dot-2.0-test', '0', '0.1.2', 'x86_64', 'pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm', 'sha256', '435d92e6c09248b501b8d2ae786f92ccfad69fab8b1bc774e2b66ff6c0d83979'):{
                    'size': 2359, 
                    'vendor': '', 
                    'checksumtype': 'sha256', 
                    'license': 'MIT', 
                    'checksum': '435d92e6c09248b501b8d2ae786f92ccfad69fab8b1bc774e2b66ff6c0d83979', 
                    'description': 'Test package to see how we deal with packages with dots in the name', 
                    'pkgpath': '%s/.//pulp-dot-2.0-test/0.1.2/1.fc11/x86_64/435d92e6c09248b501b8d2ae786f92ccfad69fab8b1bc774e2b66ff6c0d83979' % (pkg_dir), 
                    'savepath': '%s/%s/' % (repo_working_dir, repo_label), 
                    'filename': 'pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm', 
                    'downloadurl': 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm', 
                    'item_type': 'rpm', 
                    'epoch': '0', 
                    'version': '0.1.2', 
                    'arch': 'x86_64', 
                    'provides': [
                        ('pulp-dot-2.0-test(x86-64)', 'EQ', ('0', '0.1.2', '1.fc11')), 
                        ('pulp-dot-2.0-test', 'EQ', ('0', '0.1.2', '1.fc11')), 
                        ('config(pulp-dot-2.0-test)', 'EQ', ('0', '0.1.2', '1.fc11'))
                        ], 
                    'relativepath': 'pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm', 
                    'release': '1.fc11', 
                    'buildhost': 'gibson', 
                    'requires': [], 
                    'name': 'pulp-dot-2.0-test'
                }, 
                ('pulp-test-package', '0', '0.3.1', 'x86_64', 'pulp-test-package-0.3.1-1.fc11.x86_64.rpm', 'sha256', '6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f'): {
                    'size': 2216, 
                    'vendor': '', 
                    'checksumtype': 'sha256', 
                    'license': 'MIT', 
                    'checksum': '6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f', 
                    'description': 'Test package.  Nothing to see here.', 
                    'pkgpath': '%s/.//pulp-test-package/0.3.1/1.fc11/x86_64/6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f' % (pkg_dir), 
                    'savepath': '%s/%s/' % (repo_working_dir, repo_label), 
                    'filename': 'pulp-test-package-0.3.1-1.fc11.x86_64.rpm', 
                    'downloadurl': 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/pulp-test-package-0.3.1-1.fc11.x86_64.rpm', 
                    'item_type': 'rpm', 
                    'epoch': '0', 
                    'version': '0.3.1', 
                    'arch': 'x86_64', 
                    'provides': [
                        ('pulp-test-package(x86-64)', 'EQ', ('0', '0.3.1', '1.fc11')), 
                        ('pulp-test-package', 'EQ', ('0', '0.3.1', '1.fc11')), 
                        ('config(pulp-test-package)', 'EQ', ('0', '0.3.1', '1.fc11'))
                    ], 
                    'relativepath': 'pulp-test-package-0.3.1-1.fc11.x86_64.rpm', 
                    'release': '1.fc11', 
                    'buildhost': 'gibson', 
                    'requires': [], 
                    'name': 'pulp-test-package'
                    }
                }
        return rpms


    def get_simple_rpm(self, value=None):
        if not value:
            value = "test_value"
        rpm = {}
        for k in RPM_UNIT_KEY:
            rpm[k] = value
        for k in ("filename", "vendor", "description", "buildhost", "license",
                "vendor", "requires", "provides", "pkgpath", "relativepath"):
            rpm[k] = value
        return rpm
    
    def test_metadata(self):
        metadata = YumImporter.metadata()
        self.assertEquals(metadata["id"], YUM_IMPORTER_TYPE_ID)
        self.assertTrue(RPM_TYPE_ID in metadata["types"])

    def test_basic_sync(self):
        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_basic_sync"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        self.assertTrue(summary is not None)
        self.assertTrue(details is not None)
        self.assertTrue(status)
        self.assertEquals(summary["num_synced_new_rpms"], 3)
        self.assertEquals(summary["num_resynced_rpms"], 0)
        self.assertEquals(summary["num_not_synced_rpms"], 0)
        self.assertEquals(summary["num_orphaned_rpms"], 0)
        self.assertEquals(details["size_total"], 6868)
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

    def test_cancel_sync(self):
        global updated_progress
        updated_progress = None

        def set_progress(progress):
            global updated_progress
            updated_progress = progress

        class SyncThread(threading.Thread):
            def __init__(self, importer, repo, sync_conduit, config):
                threading.Thread.__init__(self)
                self.importer = importer
                self.repo = repo
                self.sync_conduit = sync_conduit
                self.config = config
                self.status = None
                self.summary = None
                self.details = None
                self.finished = False

            def run(self):
                status, summary, details = self.importer._sync_repo(self.repo, self.sync_conduit, self.config)
                self.status = status
                self.summary = summary
                self.details = details
                self.finished = True

        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/v1/testing/6Server/x86_64/"
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_cancel_sync"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        sync_conduit.set_progress = mock.Mock()
        sync_conduit.set_progress.side_effect = set_progress
        config = importer_mocks.get_basic_config(feed_url=feed_url, num_threads=1, max_speed=25)
        importer = YumImporter()
        sync_thread = SyncThread(importer, repo, sync_conduit, config)
        sync_thread.start()
        # Wait to confirm that sync has started and we are downloading packages
        # We are intentionally setting the 'config' to use 1 thread and max_speed to be low so we will
        # have a chance to cancel the sync before it completes
        for i in range(30):
            if updated_progress and updated_progress.has_key("content") and updated_progress["content"].has_key("state") \
                and updated_progress["content"]["state"] == "IN_PROGRESS":
                break
            time.sleep(1)
        self.assertEquals(updated_progress["metadata"]["state"], "FINISHED")
        self.assertEquals(updated_progress["content"]["state"], "IN_PROGRESS")
        ###
        ### Issue Cancel
        ###
        importer.cancel_sync_repo()
        # Wait for cancel of sync
        for i in range(45):
            if sync_thread.finished:
                break
            time.sleep(1)
        self.assertEquals(updated_progress["content"]["state"], "CANCELED")
        self.assertFalse(sync_thread.status)
    
    def test_basic_local_sync(self):
        feed_url = "file://%s/pulp_unittest/" % (self.data_dir)
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_basic_local_sync"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        self.assertTrue(summary is not None)
        self.assertTrue(details is not None)
        self.assertTrue(status)
        self.assertEquals(summary["num_synced_new_rpms"], 3)
        self.assertEquals(summary["num_resynced_rpms"], 0)
        self.assertEquals(summary["num_not_synced_rpms"], 0)
        self.assertEquals(summary["num_orphaned_rpms"], 0)
        self.assertEquals(details["size_total"], 6868)
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
        state, msg = importer.validate_config(repo, config, [])
        self.assertTrue(state)

        # Test that an unknown argument in the config throws an error 
        # and the unknown arg is identified in the message
        config = importer_mocks.get_basic_config(feed_url=feed_url, bad_unknown_arg="blah")
        state, msg = importer.validate_config(repo, config, [])
        self.assertFalse(state)
        self.assertTrue("bad_unknown_arg" in msg)

    def test_basic_orphaned_sync(self):
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_basic_sync"
        unit_key = {}
        for k in RPM_UNIT_KEY:
            unit_key[k] = "test_value"
        metadata = {"filename" : "test_value"}
        existing_units = [Unit(RPM_TYPE_ID, unit_key, metadata, os.path.join(self.pkg_dir, "test_rel_path"))]
        sync_conduit = importer_mocks.get_sync_conduit(type_id=RPM_TYPE_ID, existing_units=existing_units, pkg_dir=self.pkg_dir)
        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        self.assertTrue(summary is not None)
        self.assertTrue(details is not None)
        self.assertTrue(status)
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

        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
        importer = YumImporter()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_progress_sync"
        sync_conduit = importer_mocks.get_sync_conduit(pkg_dir=self.pkg_dir)
        sync_conduit.set_progress = mock.Mock()
        sync_conduit.set_progress.side_effect = set_progress
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        status, summary, details = importer._sync_repo(repo, sync_conduit, config)
        self.assertTrue(status)
        self.assertEquals(summary["num_synced_new_rpms"], 3)
        self.assertTrue(updated_progress is not None)
        self.assertTrue("metadata" in updated_progress)
        self.assertTrue(updated_progress["metadata"].has_key("state"))
        self.assertTrue("errata" in updated_progress)
        self.assertTrue(updated_progress["errata"].has_key("state"))
        self.assertTrue("content" in updated_progress)
        self.assertTrue(updated_progress["content"].has_key("state"))
        self.assertEquals(updated_progress["content"]["state"], "FINISHED")
        for key in importer_rpm.PROGRESS_REPORT_FIELDS:
            self.assertTrue(key in updated_progress["content"])

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
        def side_effect(arg, checksum=None, checksum_type="sha256", size=None, verify_options={}):
            if arg == "rel_path_b":
                return False
            return True
        util.verify_exists = mock.Mock()
        util.verify_exists.side_effect = side_effect

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

    def test_remove_packages(self):
        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_remove_packages"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        self.assertTrue(status)
        self.assertEquals(summary["num_synced_new_rpms"], 3)
        self.assertEquals(len(self.get_files_in_dir("*.rpm", self.pkg_dir)), 3)
        self.assertEquals(len(self.get_files_in_dir("*.rpm", repo.working_dir)), 3)
        expected_rpms = self.get_expected_rpms_from_pulp_unittest(repo.id)
        # Confirm that both the RPM and the Symlink for each expected rpm does exist
        #  Then run remove_unit
        # Confirm that both the RPM and the Symlink have been deleted from the file system
        for rpm in expected_rpms.values():
            rpm_save_path = os.path.join(rpm["pkgpath"], rpm["filename"])
            self.assertTrue(os.path.exists(rpm_save_path))

            symlink_save_path = os.path.join(rpm["savepath"], rpm["filename"])
            self.assertTrue(os.path.lexists(symlink_save_path))

            unit = Unit(RPM_TYPE_ID, 
                    importer_rpm.form_rpm_unit_key(rpm), 
                    importer_rpm.form_rpm_metadata(rpm),
                    rpm_save_path)
            importer_rpm.remove_unit(sync_conduit, repo, unit)
            self.assertFalse(os.path.exists(rpm_save_path))
            self.assertFalse(os.path.exists(symlink_save_path))
        self.assertEquals(len(self.get_files_in_dir("*.rpm", self.pkg_dir)), 0)
        self.assertEquals(len(self.get_files_in_dir("*.rpm", repo.working_dir)), 0)

    def test_remove_old_packages(self):
        feed_url = "http://jmatthews.fedorapeople.org/repo_multiple_versions/"
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_remove_old_packages"
        sync_conduit = importer_mocks.get_sync_conduit(type_id=RPM_TYPE_ID, pkg_dir=self.pkg_dir)
        ###
        # Test that old packages are not in rpmList and are never intended to be downloaded
        # Additionallity verify that already existing packages which are NOT orphaned are also
        # removed with remove_old functionality
        ###
        config = importer_mocks.get_basic_config(feed_url=feed_url, remove_old=False, num_old_packages=0)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        self.assertTrue(status)
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
                    os.path.join(self.pkg_dir, rpm["pkgpath"], rpm["filename"]))
            existing_units.append(u)
        config = importer_mocks.get_basic_config(feed_url=feed_url, remove_old=True, num_old_packages=6)
        sync_conduit = importer_mocks.get_sync_conduit(type_id=RPM_TYPE_ID, existing_units=existing_units, pkg_dir=self.pkg_dir)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        self.assertTrue(status)
        self.assertEquals(summary["num_rpms"], 7)
        self.assertEquals(summary["num_orphaned_rpms"], 5)
        self.assertEquals(summary["num_synced_new_rpms"], 0)
        self.assertEquals(summary["num_not_synced_rpms"], 0)
        pkgs = self.get_files_in_dir("*.rpm", self.pkg_dir)
        self.assertEquals(len(pkgs), 7)

        config = importer_mocks.get_basic_config(feed_url=feed_url, remove_old=True, num_old_packages=0)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        self.assertTrue(status)
        self.assertEquals(summary["num_rpms"], 1)
        self.assertEquals(summary["num_orphaned_rpms"], 11)
        self.assertEquals(summary["num_synced_new_rpms"], 0)
        self.assertEquals(summary["num_not_synced_rpms"], 0)
        pkgs = self.get_files_in_dir("*.rpm", self.pkg_dir)
        self.assertEquals(len(pkgs), 1)

    def test_srpm_sync(self):
        feed_url = "http://pkilambi.fedorapeople.org/test_srpm_repo/"
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_srpm_sync"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        self.assertTrue(status)
        self.assertTrue(summary is not None)
        self.assertTrue(details is not None)
        self.assertEquals(summary["num_rpms"], 3)
        self.assertEquals(summary["num_synced_new_srpms"], 3)
        self.assertEquals(summary["num_synced_new_rpms"], 0)


    def test_grinder_config(self):
        repo_label = "test_grinder_config"
        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
        num_threads = 25
        max_speed = 1
        proxy_url = "http://example.com"
        proxy_port = "3128"
        proxy_user = "username"
        proxy_pass = "password"
        ssl_verify = True
        ssl_ca_cert = "ca_cert_data"
        ssl_client_cert = "client_cert_data"
        ssl_client_key = "client_key_data"
        newest = True
        remove_old = True
        num_old_packages = 99
        tmp_path = "/tmp"

        config = importer_mocks.get_basic_config(feed_url=feed_url, num_threads=num_threads, max_speed=max_speed,
                proxy_url=proxy_url, proxy_port=proxy_port, proxy_user=proxy_user, proxy_pass=proxy_pass,
                ssl_verify=ssl_verify, 
                ssl_ca_cert=ssl_ca_cert, ssl_client_cert=ssl_client_cert, ssl_client_key=ssl_client_key,
                newest=newest, remove_old=remove_old, num_old_packages=num_old_packages)
        yumRepoGrinder = importer_rpm.get_yumRepoGrinder(repo_label, tmp_path, config)
        self.assertEquals(yumRepoGrinder.repo_label, repo_label)
        self.assertEquals(yumRepoGrinder.repo_url, feed_url)
        self.assertEquals(yumRepoGrinder.numThreads, num_threads)
        self.assertEquals(yumRepoGrinder.max_speed, max_speed)
        self.assertEquals(yumRepoGrinder.proxy_url, proxy_url)
        self.assertEquals(yumRepoGrinder.proxy_port, proxy_port)
        self.assertEquals(yumRepoGrinder.proxy_user, proxy_user)
        self.assertEquals(yumRepoGrinder.proxy_pass, proxy_pass)
        self.assertEquals(yumRepoGrinder.sslverify, ssl_verify)
        self.assertEquals(yumRepoGrinder.newest, newest)
        self.assertEquals(yumRepoGrinder.remove_old, remove_old)
        self.assertEquals(yumRepoGrinder.numOldPackages, num_old_packages)
        self.assertEquals(yumRepoGrinder.tmp_path, tmp_path)
        # Verify that the pkgpath is set to "./", hardcoded in importer_rpm to 
        # force the package dir to be a relative path with the checksum components in the path
        self.assertEquals(yumRepoGrinder.pkgpath, "./")

    def test_bandwidth_limit(self):
        # This test assumes an available bandwidth of more than 100KB for 2 threads
        feed_url = 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/test_bandwidth_repo_smaller/'
        expected_size_bytes = 209888 # 5 1MB RPMs are in this repo
        expected_num_packages = 2
        num_threads = 2
        max_speed = 25 # KB/sec

        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_bandwidth_limit"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url, num_threads=num_threads, max_speed=max_speed)

        start = time.time()
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        end = time.time()
        self.assertTrue(status)
        self.assertEquals(summary["num_synced_new_rpms"], expected_num_packages)
        self.assertEquals(summary["num_resynced_rpms"], 0)
        self.assertEquals(summary["num_not_synced_rpms"], 0)
        self.assertEquals(summary["num_orphaned_rpms"], 0)
        self.assertEquals(details["size_total"], expected_size_bytes)

        expected = (float(expected_size_bytes)/(num_threads*max_speed*1000))
        actual_A = end - start
        self.assertTrue(actual_A > expected)
        #
        # Clean up and resync with no bandwidth limit
        # Ensure result is quicker than above
        #
        max_speed = 0
        self.clean()
        self.init()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_bandwidth_limit"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url, num_threads=num_threads, max_speed=max_speed)
        start = time.time()
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        end = time.time()
        self.assertTrue(status)
        self.assertEquals(summary["num_synced_new_rpms"], expected_num_packages)
        self.assertEquals(summary["num_resynced_rpms"], 0)
        self.assertEquals(summary["num_not_synced_rpms"], 0)
        self.assertEquals(summary["num_orphaned_rpms"], 0)
        self.assertEquals(details["size_total"], expected_size_bytes)
        # This check is presenting a problem in rhel-6.
        # Current thinking is that the packages in this repo are not large enough
        # to test the bandwidth limit.  
        # self.assertTrue(end-start < actual_A)

    def test_remote_sync_with_bad_url(self):
        feed_url = "http://repos.fedorapeople.org/INTENTIONAL_BAD_URL/demo_repos/pulp_unittest/"
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_remote_sync_with_bad_url"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        caught_exception = False
        try:
            importerRPM = importer_rpm.ImporterRPM()
            status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        except:
            caught_exception = True
        self.assertTrue(caught_exception)

        importer = YumImporter()
        caught_exception = False
        try:
            report = importer.sync_repo(repo, sync_conduit, config)
        except:
            caught_exception = True
        self.assertFalse(caught_exception)

    def test_local_sync_with_bad_url(self):
        feed_url = "file:///INTENTIONAL_BAD_URL/demo_repos/pulp_unittest/"
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_local_sync_with_bad_url"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        caught_exception = False
        try:
            importerRPM = importer_rpm.ImporterRPM()
            status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        except:
            caught_exception = True
        self.assertTrue(caught_exception)

        importer = YumImporter()
        caught_exception = False
        try:
            report = importer.sync_repo(repo, sync_conduit, config)
        except:
            caught_exception = True
        self.assertFalse(caught_exception)

    def test_errors_with_local_sync(self):
        global updated_progress
        updated_progress = None

        def set_progress(progress):
            global updated_progress
            updated_progress = progress

        importer = YumImporter()
        feed_url = "file://%s/local_errors/" % (self.data_dir)
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_errors_with_local_sync"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        sync_conduit.set_progress = mock.Mock()
        sync_conduit.set_progress.side_effect = set_progress
        config = importer_mocks.get_basic_config(feed_url=feed_url)

        test_rpm_with_error = os.path.join(self.data_dir, "local_errors", "pulp-test-package-0.3.1-1.fc11.x86_64.rpm")
        orig_stat = os.stat(test_rpm_with_error)
        try:
            os.chmod(test_rpm_with_error, 0000)
            self.assertFalse(os.access(test_rpm_with_error, os.R_OK))
            status, summary, details = importer._sync_repo(repo, sync_conduit, config)
        finally:
            os.chmod(test_rpm_with_error, orig_stat.st_mode)

        self.assertFalse(status)
        self.assertTrue(summary is not None)
        self.assertTrue(details is not None)
        self.assertEquals(summary["num_not_synced_rpms"], 1)
        self.assertEquals(details["size_total"], 6791)
        # Confirm regular RPM files exist under self.pkg_dir
        pkgs = self.get_files_in_dir("*.rpm", self.pkg_dir)
        self.assertEquals(len(pkgs), 2)
        sym_links = self.get_files_in_dir("*.rpm", repo.working_dir)
        self.assertEquals(len(pkgs), 2)

        expected_details = {
                'rpm': 
                    {
                        'num_success': 2, 'total_count': 3, 'items_left': 0, 
                        'size_left': 0.0, 'total_size_bytes': 6791, 'num_error': 1
                    }
                }
        self.assertTrue(updated_progress.has_key("metadata"))
        self.assertEqual(updated_progress["metadata"]["state"], "FINISHED")
        self.assertTrue(updated_progress.has_key("errata"))
        self.assertEqual(updated_progress["errata"]["state"], "FINISHED")
        self.assertEqual(updated_progress["errata"]["num_errata"], 52)
        self.assertTrue(updated_progress.has_key("content"))
        self.assertEqual(updated_progress["content"]["state"], "FINISHED")
        self.assertEqual(updated_progress["content"]["items_total"], 3)
        self.assertEqual(updated_progress["content"]["items_left"], 0)
        self.assertEqual(updated_progress["content"]["num_success"], 2)
        self.assertEqual(updated_progress["content"]["num_error"], 1)
        self.assertEqual(updated_progress["content"]["size_total"], 6791)
        self.assertEqual(updated_progress["content"]["size_left"], 0)
        for type_id in (BaseFetch.FILE, BaseFetch.TREE_FILE, BaseFetch.DELTA_RPM):
            self.assertTrue(updated_progress["content"]["details"].has_key(type_id))
            self.assertEqual(updated_progress["content"]["details"][type_id]["num_success"], 0)
            self.assertEqual(updated_progress["content"]["details"][type_id]["num_error"], 0)
            self.assertEqual(updated_progress["content"]["details"][type_id]["size_total"], 0)
            self.assertEqual(updated_progress["content"]["details"][type_id]["size_left"], 0)
            self.assertEqual(updated_progress["content"]["details"][type_id]["items_total"], 0)
            self.assertEqual(updated_progress["content"]["details"][type_id]["items_left"], 0)
        # 'rpm': {'num_success': 2, 'size_total': 6791, 'items_left': 0, 
        #    'items_total': 3, 'size_left': 0.0, 'num_error': 1}
        self.assertTrue(updated_progress["content"]["details"].has_key("rpm"))
        self.assertEqual(updated_progress["content"]["details"]["rpm"]["num_success"], 2)
        self.assertEqual(updated_progress["content"]["details"]["rpm"]["num_error"], 1)
        self.assertEqual(updated_progress["content"]["details"]["rpm"]["size_total"], 6791)
        self.assertEqual(updated_progress["content"]["details"]["rpm"]["size_left"], 0)
        self.assertEqual(updated_progress["content"]["details"]["rpm"]["items_total"], 3)
        self.assertEqual(updated_progress["content"]["details"]["rpm"]["items_left"], 0)
        #
        # Check error_details
        # error has keys of: {"error_type", "traceback", "value", "exception"}
        #
        self.assertEqual(len(updated_progress["content"]["error_details"]), 1)
        error = updated_progress["content"]["error_details"][0]
        self.assertEqual(error["filename"], "pulp-test-package-0.3.1-1.fc11.x86_64.rpm")
        self.assertEqual(error["value"], 
            '(37, "Couldn\'t open file %s")' % (test_rpm_with_error))
        self.assertTrue('pycurl.error' in error["error_type"])
        self.assertTrue(isinstance(error["exception"], basestring)) 
        self.assertTrue(len(error["traceback"]) > 0)

    def test_local_sync_with_packages_in_subdir(self):
        feed_url = "file://%s/repo_packages_in_subdirs/" % (self.data_dir)
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_local_sync_with_packages_in_subdir"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        self.assertTrue(summary is not None)
        self.assertTrue(details is not None)
        self.assertTrue(status)
        self.assertEquals(summary["num_synced_new_rpms"], 3)
        self.assertEquals(summary["num_resynced_rpms"], 0)
        self.assertEquals(summary["num_not_synced_rpms"], 0)
        self.assertEquals(summary["num_orphaned_rpms"], 0)
        self.assertEquals(details["size_total"], 6868)
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


    def test_proxy_sync(self):
        global data_received, num_bytes_received_in_proxy
        data_received = False
        num_bytes_received_in_proxy = 0
        skip_proxy = False
        try:
            from twisted.web import http, proxy
            from twisted.internet import reactor
            from twisted.internet.error import ReactorNotRunning
            class UnitTestProxyProtocol(proxy.Proxy):
                def dataReceived(self, data):
                    global data_received, num_bytes_received_in_proxy
                    data_received = True
                    num_bytes_received_in_proxy += len(data)
                    #print "Data = %s" % (data)
                    return proxy.Proxy.dataReceived(self, data)
            class ProxyFactory(http.HTTPFactory):
                protocol = UnitTestProxyProtocol
            class ProxyServerThread(threading.Thread):
                def __init__(self, proxy_port, proxy_user=None, proxy_pass=None):
                    threading.Thread.__init__(self)
                    self.proxy_port = proxy_port
                    self.proxy_user = proxy_user
                    self.proxy_pass = proxy_pass
                def stop(self):
                    try:
                        reactor.stop()
                    except ReactorNotRunning, e:
                        pass
                def run(self):
                    reactor.listenTCP(proxy_port, ProxyFactory())
                    reactor.run(installSignalHandlers=0)
        except Exception, e:
            print e
            skip_proxy = True
        if skip_proxy:
            print "********************************************************************"
            print "Test Skipped!"
            print "Skipping the proxy test sync since Twisted modules are not available"
            print "To enable these tests run the below"
            print "  yum install python-twisted"
            print "********************************************************************"
            return

        proxy_url = "http://127.0.0.1"
        proxy_port = 8539
        proxy_user = "unit_test_username"
        proxy_pass = "unit_test_password"
        proxy_server = ProxyServerThread(proxy_port=proxy_port, proxy_user=proxy_user, 
                proxy_pass=proxy_pass)
        try:
            proxy_server.start()
            feed_url = 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest'
            repo = mock.Mock(spec=Repository)
            repo.working_dir = self.working_dir
            repo.id = "test_proxy_sync"
            sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
            config = importer_mocks.get_basic_config(feed_url=feed_url, 
                    proxy_url=proxy_url, proxy_port=proxy_port,
                    proxy_user=proxy_user, proxy_pass=proxy_pass)
            importerRPM = importer_rpm.ImporterRPM()
            status, summary, details = importerRPM.sync(repo, sync_conduit, config)
            #print "Status = %s" % (status)
            #print "Summary = %s" % (summary)
            #print "Details = %s" % (details)
        finally:
            proxy_server.stop()
        self.assertTrue(status)
        self.assertTrue(data_received)
        self.assertEquals(summary["num_synced_new_rpms"], 3)
        self.assertEquals(summary["num_resynced_rpms"], 0)
        self.assertEquals(summary["num_not_synced_rpms"], 0)
        self.assertEquals(summary["num_orphaned_rpms"], 0)
        self.assertEquals(details["size_total"], 6868)
