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

import glob
import os
import sys
import mock
import unittest
import tempfile

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/")

import importer_mocks
import rpm_support_base
from yum_importer import importer_rpm
from yum_importer.importer import YumImporter, YUM_IMPORTER_TYPE_ID
from yum_importer.distribution import  DISTRO_TYPE_ID
from pulp.plugins.model import Repository

class TestDistribution(rpm_support_base.PulpRPMTests):

    def setUp(self):
        super(TestDistribution, self).setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = os.path.join(self.temp_dir, "working")
        self.pkg_dir = os.path.join(self.temp_dir, "packages")
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "data"))

    def tearDown(self):
        super(TestDistribution, self).tearDown()

    def test_metadata(self):
        metadata = YumImporter.metadata()
        self.assertEquals(metadata["id"], YUM_IMPORTER_TYPE_ID)
        self.assertTrue(DISTRO_TYPE_ID in metadata["types"])

    def test_distributions_sync(self):
        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
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
        self.assertEquals(summary["num_synced_new_distributions"], 1)
        self.assertEquals(summary["num_synced_new_distributions_files"], 3)
        self.assertEquals(summary["num_resynced_distributions"], 0)
        self.assertEquals(summary["num_resynced_distribution_files"], 0)

        distro_tree_files = glob.glob("%s/%s/images/*" % (repo.working_dir, repo.id))
        self.assertEquals(len(distro_tree_files), 3)
