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

class TestImportUnits(unittest.TestCase):

    def setUp(self):
        super(TestImportUnits, self).setUp()
        self.saved_verify_exists = util.verify_exists
        self.init()

    def tearDown(self):
        super(TestImportUnits, self).tearDown()
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

    def setup_source_repo(self):
        # Sync a sample repository to populate and setup up Source Repo
        source_repo = mock.Mock(spec=Repository)
        source_repo.id = "repo_a"
        source_repo.working_dir = os.path.join(self.working_dir, source_repo.id)
        importer = YumImporter()
        feed_url = "file://%s/pulp_unittest/" % (self.data_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        status, summary, details = importer._sync_repo(source_repo, sync_conduit, config)
        self.assertTrue(status)
        self.assertEquals(summary["num_synced_new_rpms"], 3)
        # Confirm regular RPM files exist under self.pkg_dir
        pkgs = self.get_files_in_dir("*.rpm", self.pkg_dir)
        self.assertEquals(len(pkgs), 3)
        for p in pkgs:
            self.assertTrue(os.path.isfile(p))
        # Confirm symlinks to RPMs exist under repo.working_dir
        sym_links = self.get_files_in_dir("*.rpm", source_repo.working_dir)
        self.assertEquals(len(pkgs), 3)
        for link in sym_links:
            self.assertTrue(os.path.islink(link))
        #
        # Now we have some test data in the source repo
        #
        # Simulate what import_conduit.get_source_repos would return
        #
        metadata = {}
        source_units = []
        storage_path = '%s/pulp-dot-2.0-test/0.1.2/1.fc11/x86_64/435d92e6c09248b501b8d2ae786f92ccfad69fab8b1bc774e2b66ff6c0d83979/pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm' % (self.pkg_dir)
        filename = os.path.basename(storage_path)
        unit_key = {"filename":filename}
        source_units.append(Unit(RPM_TYPE_ID, unit_key, metadata, storage_path))
        storage_path = '%s/pulp-test-package/0.3.1/1.fc11/x86_64/6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f/pulp-test-package-0.3.1-1.fc11.x86_64.rpm' % (self.pkg_dir)
        filename = os.path.basename(storage_path)
        unit_key = {"filename":filename}
        source_units.append(Unit(RPM_TYPE_ID, unit_key, metadata, storage_path))
        storage_path = '%s/pulp-test-package/0.2.1/1.fc11/x86_64/4dbde07b4a8eab57e42ed0c9203083f1d61e0b13935d1a569193ed8efc9ecfd7/pulp-test-package-0.2.1-1.fc11.x86_64.rpm' % (self.pkg_dir)
        filename = os.path.basename(storage_path)
        unit_key = {"filename":filename}
        source_units.append(Unit(RPM_TYPE_ID, unit_key, metadata, storage_path))
        # Pass in the simulated source_units to the import_conduit
        import_conduit = importer_mocks.get_import_conduit(source_units=source_units)
        return importer, source_repo, source_units, import_conduit, config

    def test_basic_import(self):
        importer, source_repo, source_units, import_conduit, config = self.setup_source_repo()
        dest_repo = mock.Mock(spec=Repository)
        dest_repo.id = "repo_b"
        dest_repo.working_dir = os.path.join(self.working_dir, dest_repo.id)
        specific_units = []
        #  We need to test that:
        #   1) associate_unit was called on each unit type
        #   2) symlinks were created in the dest_repo working dir
        importer.import_units(source_repo, dest_repo, import_conduit, config, specific_units)
        #
        #  Test that we called import_conduit.associate_unit for each source_unit
        #  We convert the mock call_list to extract the unit argument per call
        #  Assume only one argument to import_conduit.associate_units()
        #
        associated_units = [mock_call[0][0] for mock_call in import_conduit.associate_unit.call_args_list]
        self.assertEqual(len(associated_units), len(source_units))
        for u in associated_units:
            self.assertTrue(u in source_units)
        #
        # Test that we created the symlinks in the repo working directory
        # Confirm symlinks to RPMs exist under repo.working_dir
        #
        sym_links = self.get_files_in_dir("*.rpm", dest_repo.working_dir)
        self.assertEquals(len(sym_links), 3)
        for link in sym_links:
            self.assertTrue(os.path.islink(link))

    def test_import_specific_units(self):
        importer, source_repo, source_units, import_conduit, config = self.setup_source_repo()
        dest_repo = mock.Mock(spec=Repository)
        dest_repo.id = "repo_b"
        dest_repo.working_dir = os.path.join(self.working_dir, dest_repo.id)
        specific_units = [source_units[0], source_units[1]]
        #  We need to test that:
        #   1) associate_unit was called on each unit of specific_units
        #   2) symlinks were created in the dest_repo working dir
        importer.import_units(source_repo, dest_repo, import_conduit, config, specific_units)
        #
        #  Test that we called import_conduit.associate_unit for each specific_unit
        #  We convert the mock call_list to extract the unit argument per call
        #  Assume only one argument to import_conduit.associate_units()
        #
        associated_units = [mock_call[0][0] for mock_call in import_conduit.associate_unit.call_args_list]
        self.assertEqual(len(associated_units), len(specific_units))
        for u in associated_units:
            self.assertTrue(u in specific_units)
        #
        # Test that we created the symlinks in the repo working directory
        # Confirm symlinks to RPMs exist under repo.working_dir
        #
        sym_links = self.get_files_in_dir("*.rpm", dest_repo.working_dir)
        self.assertEquals(len(sym_links), 2)
        for link in sym_links:
            self.assertTrue(os.path.islink(link))

