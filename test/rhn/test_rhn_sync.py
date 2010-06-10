#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

# Python
import os
import shutil
import sys
import unittest

# Pulp
import pulp.api.repo
import pulp.api.package

srcdir = os.path.abspath(os.path.dirname(__file__)) + '/../common'
sys.path.append(srcdir)
import util


REPO_ID = 'rhn-server-vt-test'


class TestRhnSync(unittest.TestCase):

    def clean(self):
        self.rapi.clean()
        self.papi.clean()
        dest_dir = '%s/%s/' % (self.config.get('paths', 'local_storage'), REPO_ID)
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
        
    def setUp(self):
        self.config = util.load_test_config()

        self.rapi = pulp.api.repo.RepoApi(self.config)
        self.papi = pulp.api.package.PackageApi(self.config)

        self.clean()
        
    def tearDown(self):
        self.clean()
        
    def test_sync(self):
        # Setup
        repo = self.rapi.create(REPO_ID,'RHN Repo', 'i386', 
                                'rhn:satellite.rhn.redhat.com/rhel-x86_64-server-vt-5')

        # Test
        self.rapi.sync(repo.id)
        
        # Verify
        dirList = os.listdir(self.rapi.localStoragePath + '/' + repo.id)
        self.assertTrue(len(dirList) > 0)

        found = self.rapi.repository(repo.id)
        packages = found['packages']

        self.assertTrue(packages != None)
        self.assertTrue(len(packages) > 0)
