# -*- coding: utf-8 -*-
# Copyright (c) 2012 Red Hat, Inc.
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
import shutil
import glob
from base_file_upgrade import BaseFileUpgradeTests
from pulp.server.upgrade.filesystem import rpms

DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
V1_TEST_FILESYSTEM = os.path.join(DATA_DIR, 'filesystem/v1')
V2_TEST_FILESYSTEM = os.path.join(DATA_DIR, 'filesystem/v2')
V1_REPOS_DIR = os.path.join(V1_TEST_FILESYSTEM, "var/lib/pulp/repos")

class TestFileUpgrade(BaseFileUpgradeTests):

    def tearDown(self):
        shutil.rmtree(V2_TEST_FILESYSTEM + '/var')

    def get_files_in_dir(self, pattern, path):
        files = []
        for d,_,_ in os.walk(path):
            files.extend(glob.glob(os.path.join(d,pattern)))
        return files

    def test_rpms(self):
        rpms.V1_DIR_RPMS = "%s/%s" % (V1_TEST_FILESYSTEM, rpms.V1_DIR_RPMS)
        rpms.DIR_RPMS = "%s/%s" % (V2_TEST_FILESYSTEM, rpms.DIR_RPMS)
        rpms._rpms(self.v1_test_db.database, self.v2_test_db.database)
        v1_rpms_list = self.get_files_in_dir('*.rpm', rpms.V1_DIR_RPMS)
        v2_rpms_list = self.get_files_in_dir('*.rpm', rpms.DIR_RPMS)
        print len(v1_rpms_list), len(v2_rpms_list)
        self.assertEquals(len(v1_rpms_list), len(v2_rpms_list))