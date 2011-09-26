#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
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

# Python
import os
import sys

from pymongo.errors import DuplicateKeyError

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import pulp
from pulp.server import updateinfo
from pulp.server.api.repo import RepoApi
from pulp.server.api.distribution import DistributionApi

class TestDistribution(testutil.PulpAsyncTest):

    def test_create(self):
        repo = self.repo_api.create('test-distro', 'test distro',
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
        family = 'Fedora'
        variant = 'Fedora'
        version = 'F14'
        distro = self.distribution_api.create(id, description, relativepath, family= family,
                                              variant=variant, version=version, files=files)
        self.assertTrue(distro is not None)

    def test_duplicate(self):
        id = 'test_duplicate_distro'
        distro1 = self.distribution_api.create(id, None, None, [])
        assert(distro1 is not None)
        distro2 = self.distribution_api.create(id, None, None, [])
        assert(distro2 is not None)
        self.assertTrue(distro1['id'] == distro2['id'])

        status = True
        try:
            distro = self.distribution_api.create("test_distro", None, None, [])
        except DuplicateKeyError:
            status = False
        self.assertTrue(status)
#
    def test_delete(self):
        id = 'test_delete_distro'
        distro = self.distribution_api.create(id, None, None, [])
        self.assertTrue(distro is not None)
        found = self.distribution_api.distribution(id)
        self.assertTrue(found is not None)
        self.distribution_api.delete(id)
        found = self.distribution_api.distribution(id)
        self.assertTrue(found is None)

    def test_update(self):
        id = 'test_update_distro'
        description = 'test distro typo'
        distro = self.distribution_api.create(id, description, None,
                                              family='fedora', variant='fedora', version='15', files=[])
        self.assertTrue(distro is not None)
        found = self.distribution_api.distribution(id)
        self.assertTrue(found is not None)
        self.assertTrue(found['description'] == description)
        new_description = "test distro"
        self.distribution_api.update(id, {'description':new_description})
        found = self.distribution_api.distribution(id)
        self.assertTrue(found is not None)
        self.assertTrue(found['description'] == new_description)
        new_family = "new fedora"
        self.distribution_api.update(id, {'family':new_family})
        found = self.distribution_api.distribution(id)
        self.assertTrue(found is not None)
        self.assertTrue(found['family'] == new_family)
        new_variant = "new fedora"
        self.distribution_api.update(id, {'variant':new_variant})
        found = self.distribution_api.distribution(id)
        self.assertTrue(found is not None)
        self.assertTrue(found['variant'] == new_variant)
        new_version = "16"
        self.distribution_api.update(id, {'version':new_version})
        found = self.distribution_api.distribution(id)
        self.assertTrue(found is not None)
        self.assertTrue(found['version'] == new_version)
        
    def test_add_distro_to_repo(self):
        distroid = 'test_repo_distro'
        distro = self.distribution_api.create(distroid, None, None, [])
        
        repoid = 'test-repodist'
        self.repo_api.create(repoid, 'some name', 'i386', 'http://example.com')
        self.repo_api.add_distribution(repoid, distroid)
        repo = self.repo_api.repository(repoid)
        assert(distroid in repo['distributionid'])
        
        self.repo_api.delete(id=repoid)
        repo = self.repo_api.repository(repoid)
        assert(repo is None)
        
    def test_remove_distro_from_repo(self):
        distroid = 'test_repo_distro'
        distro = self.distribution_api.create(distroid, None, None, [])
        found = self.distribution_api.distribution(distroid)
        self.assertTrue(found is not None)
        
        repoid = 'test-repodist'
        self.repo_api.create(repoid, 'some name', 'i386', 'http://example.com/test/path')
        self.repo_api.add_distribution(repoid, distroid)
        repo = self.repo_api.repository(repoid)
        assert(distroid in repo['distributionid'])
        
        self.repo_api.remove_distribution(repoid, distroid)
        repo = self.repo_api.repository(repoid)
        found = self.distribution_api.distribution(distroid)
        self.assertTrue(found is None)
        assert(distroid not in repo['distributionid'])
         
         
