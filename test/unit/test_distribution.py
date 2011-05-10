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
import sys
import unittest

from pymongo.errors import DuplicateKeyError

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import mocks
import pulp
from pulp.server import updateinfo
from pulp.server.api.repo import RepoApi
from pulp.server.api.distribution import DistributionApi
import testutil

class TestDistribution(unittest.TestCase):

    def clean(self):
        self.dapi.clean()
        self.rapi.clean()

    def setUp(self):
        mocks.install()
        self.config = testutil.load_test_config()
        self.data_path = \
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
        self.rapi = RepoApi()
        self.dapi = DistributionApi()
        self.clean()

    def tearDown(self):
        self.clean()
        testutil.common_cleanup()

    def test_create(self):
        repo = self.rapi.create('test-distro', 'test distro',
            'i386', 'http://example.com')
        assert(repo is not None)
        id = 'ks-test-sistro-i386'
        description = 'test_distro_description'
        relativepath = "/my/test/path/to/distribution/"
        files = ['/my/test/path/to/distribution/images/boot.iso',
                 '/my/test/path/to/distribution/images/efiboot.img',
                 '/my/test/path/to/distribution/images/install.img',
                 '/my/test/path/to/distribution/images/initrd.img',
                 '/my/test/path/to/distribution/images/vmlinuz']
        distro = self.dapi.create(id, description, relativepath, files=files)
        self.assertTrue(distro is not None)

    def test_duplicate(self):
        id = 'test_duplicate_distro'
        distro1 = self.dapi.create(id, None, None, [])
        assert(distro1 is not None)
        distro2 = self.dapi.create(id, None, None, [])
        assert(distro2 is not None)
        self.assertTrue(distro1 == distro2)

        status = True
        try:
            distro = self.dapi.create("test_distro", None, None, [])
        except DuplicateKeyError:
            status = False
        self.assertTrue(status)
#
    def test_delete(self):
        id = 'test_delete_distro'
        distro = self.dapi.create(id, None, None, [])
        self.assertTrue(distro is not None)
        found = self.dapi.distribution(id)
        self.assertTrue(found is not None)
        self.dapi.delete(id)
        found = self.dapi.distribution(id)
        self.assertTrue(found is None)

    def test_update(self):
        id = 'test_update_distro'
        description = 'test distro typo'
        distro = self.dapi.create(id, description, None, [])
        self.assertTrue(distro is not None)
        found = self.dapi.distribution(id)
        self.assertTrue(found is not None)
        self.assertTrue(found['description'] == description)
        new_description = "test distro"
        self.dapi.update(id, {'description':new_description})
        found = self.dapi.distribution(id)
        self.assertTrue(found is not None)
        self.assertTrue(found['description'] == new_description)
        
    def test_add_distro_to_repo(self):
        distroid = 'test_repo_distro'
        distro = self.dapi.create(distroid, None, None, [])
        
        repoid = 'test-repodist'
        self.rapi.create(repoid, 'some name', 'i386', 'http://example.com')
        self.rapi.add_distribution(repoid, distroid)
        repo = self.rapi.repository(repoid)
        assert(distroid in repo['distributionid'])
        
        self.rapi.delete(id=repoid)
        repo = self.rapi.repository(repoid)
        assert(repo is None)
        
    def test_remove_distro_from_repo(self):
        distroid = 'test_repo_distro'
        distro = self.dapi.create(distroid, None, None, [])
        found = self.dapi.distribution(distroid)
        self.assertTrue(found is not None)
        
        repoid = 'test-repodist'
        self.rapi.create(repoid, 'some name', 'i386', 'http://example.com/test/path')
        self.rapi.add_distribution(repoid, distroid)
        repo = self.rapi.repository(repoid)
        assert(distroid in repo['distributionid'])
        
        self.rapi.remove_distribution(repoid, distroid)
        repo = self.rapi.repository(repoid)
        found = self.dapi.distribution(distroid)
        self.assertTrue(found is None)
        assert(distroid not in repo['distributionid'])
         
         
