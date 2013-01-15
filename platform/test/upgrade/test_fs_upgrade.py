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
from pulp.server.upgrade.filesystem import rpms, distribution
from pulp.server.upgrade.model import UpgradeStepReport

DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
V1_TEST_FILESYSTEM = os.path.join(DATA_DIR, 'filesystem/v1')
V2_TEST_FILESYSTEM = os.path.join(DATA_DIR, 'filesystem/v2')
V1_REPOS_DIR = os.path.join(V1_TEST_FILESYSTEM, "var/lib/pulp/repos")

class TestFileSystemUpgrade(BaseFileUpgradeTests):

    def tearDown(self):
        v2_var_dir = V2_TEST_FILESYSTEM + '/var'
        if os.path.exists(v2_var_dir):
            shutil.rmtree(v2_var_dir)

    def test_rpms(self):
        report = UpgradeStepReport()
        rpms.V1_DIR_RPMS = "%s/%s" % (V1_TEST_FILESYSTEM, rpms.V1_DIR_RPMS)
        rpms.DIR_RPMS = "%s/%s" % (V2_TEST_FILESYSTEM, rpms.DIR_RPMS)
        status = rpms._rpms(self.v1_test_db.database, self.v2_test_db.database, report)
        self.assertTrue(status)
        v1_rpms_list = get_files_in_dir('*.rpm', rpms.V1_DIR_RPMS)
        v2_rpms_list = get_files_in_dir('*.rpm', rpms.DIR_RPMS)
        self.assertEquals(len(v1_rpms_list), 0)
        self.assertEquals(len(v2_rpms_list), 3)

    def test_distributions(self):
        report = UpgradeStepReport()
        distribution.V1_DIR_DISTROS = "%s/%s" % (V1_TEST_FILESYSTEM, distribution.V1_DIR_DISTROS)
        distribution.DIR_DISTROS = "%s/%s" % (V2_TEST_FILESYSTEM, distribution.DIR_DISTROS)
        status = distribution._distribution(self.v1_test_db.database, self.v2_test_db.database, report)
        self.assertTrue(status)
        v1_distro_list = get_files_in_dir('*', distribution.V1_DIR_DISTROS)
        v2_distro_list = get_files_in_dir('*', distribution.DIR_DISTROS)
        self.assertEquals(len(v1_distro_list), 0)
        self.assertEquals(len(v2_distro_list), 4)

class DRPMUpgradeTests(BaseFileUpgradeTests):

    def setUp(self):
        super(DRPMUpgradeTests, self).setUp()
        new_repo = {
                'id' : 'test_drpm_repo',
                'content_types' : 'yum',
                'repomd_xml_path' : os.path.join(V1_REPOS_DIR,
                    'repos/pulp/pulp/demo_repos/test_drpm_repo/repodata/repomd.xml'),
                'relative_path' : 'repos/pulp/pulp/demo_repos/test_drpm_repo/',
            }
        if self.v1_test_db.database.repos.find_one({'id' : 'test_drpm_repo'}):
            self.v1_test_db.database.repos.remove({'id' : 'test_drpm_repo'})
        self.v1_test_db.database.repos.insert(new_repo, safe=True)

    def test_drpms(self):
        report = UpgradeStepReport()
        rpms.DIR_DRPM = "%s/%s" % (V2_TEST_FILESYSTEM, rpms.DIR_DRPM)
        status = rpms._drpms(self.v1_test_db.database, self.v2_test_db.database, report)
        self.assertTrue(status)
        v2_rpms_list = get_files_in_dir('*.drpm', rpms.DIR_DRPM)
        self.assertEquals(18, len(v2_rpms_list))

def get_files_in_dir(pattern, path):
    files = []
    for d,_,_ in os.walk(path):
        files.extend(glob.glob(os.path.join(d,pattern)))
    return files