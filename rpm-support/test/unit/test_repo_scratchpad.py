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
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../common")

import importer_mocks
from yum_importer.importer import YumImporter
from pulp.plugins.model import Repository

class TestRepoScratchpad(unittest.TestCase):

    def setUp(self):
        super(TestRepoScratchpad, self).setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = os.path.join(self.temp_dir, "working")
        self.pkg_dir = os.path.join(self.temp_dir, "packages")
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "../data"))

    def tearDown(self):
        super(TestRepoScratchpad, self).tearDown()

    def test_repo_scratchpad_settings(self):
        global repo_scratchpad
        repo_scratchpad = {}

        def set_repo_scratchpad(data):
            global repo_scratchpad
            repo_scratchpad = data

        def get_repo_scratchpad():
            global repo_scratchpad
            return repo_scratchpad

        feed_url = "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/"
        importer = YumImporter()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_repo_scratchpad"
        sync_conduit = importer_mocks.get_sync_conduit(pkg_dir=self.pkg_dir)
        sync_conduit.set_repo_scratchpad = mock.Mock()
        sync_conduit.set_repo_scratchpad.side_effect = set_repo_scratchpad
        sync_conduit.get_repo_scratchpad = mock.Mock()
        sync_conduit.get_repo_scratchpad.side_effect = get_repo_scratchpad
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importer._sync_repo(repo, sync_conduit, config)
        print "SCRATCHPAD %s" %  repo_scratchpad
        self.assertEquals(repo_scratchpad['checksum_type'], 'sha256')
        self.assertEquals(repo_scratchpad['importer_working_dir'], os.path.join(repo.working_dir, repo.id))
