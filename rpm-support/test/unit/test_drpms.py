# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
import sys
import mock
import unittest
import tempfile
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../plugins/importers/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../common")
import importer_mocks

from yum_importer import drpm, importer_rpm
from yum_importer.importer import YumImporter, YUM_IMPORTER_TYPE_ID
from yum_importer.drpm import DRPM_UNIT_KEY
from pulp.plugins.model import Repository

class TestDRPMS(unittest.TestCase):

    def setUp(self):
        super(TestDRPMS, self).setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = os.path.join(self.temp_dir, "working")
        self.pkg_dir = os.path.join(self.temp_dir, "packages")
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "../data"))

    def tearDown(self):
        super(TestDRPMS, self).tearDown()

    def test_metadata(self):
        metadata = YumImporter.metadata()
        self.assertEquals(metadata["id"], YUM_IMPORTER_TYPE_ID)
        self.assertTrue(drpm.DRPM_TYPE_ID in metadata["types"])

    def test_drpm_sync(self):
        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/test_drpm_repo/"
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_repo"
        sync_conduit = importer_mocks.get_sync_conduit(pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        self.assertTrue(status)
        self.assertTrue(summary is not None)
        self.assertTrue(details is not None)
        self.assertEquals(summary["num_synced_new_drpms"], 18)
        self.assertEquals(summary["num_resynced_drpms"], 0)
        self.assertEquals(summary["num_orphaned_drpms"], 0)
        # validate drpms on filesystem
        def get_drpm_list(dir):
            dpkgs = []
            for root, dirs, files in os.walk(dir):
                for file in files:
                    dpkgs.append("%s/%s" % (root, file))
            return dpkgs
        dpkgs = filter(lambda x: x.endswith(".drpm"), get_drpm_list(self.pkg_dir))
        self.assertEquals(len(dpkgs), 18)
        # Confirm symlinks
        sym_links = filter(lambda x: x.endswith(".drpm"), get_drpm_list(repo.working_dir))
        self.assertEquals(len(sym_links), 18)
        for link in sym_links:
            self.assertTrue(os.path.islink(link))

    def test_get_available_drpms(self):
        deltarpm = {}
        for k in DRPM_UNIT_KEY:
            deltarpm[k] = "test_drpm"
        available_drpms = drpm.get_available_drpms([deltarpm])
        lookup_key = drpm.form_lookup_drpm_key(deltarpm)
        self.assertEqual(available_drpms[lookup_key], deltarpm)

    def test_purge_drpms(self):
        pass


