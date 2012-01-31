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

import os
import sys

import mock

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.api import repo
from pulp.server.api import repo_sync
from pulp.server.tasking import task
from pulp.server.webservices.controllers import statuses

class DistributionsTest(testutil.PulpWebserviceTest):

    def setUp(self):
        testutil.PulpWebserviceTest.setUp(self)
        self.setup_repos()

    def setup_repos(self):
        # 3 test repos
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        r = self.repo_api.create('rr1',
                'test_name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(r != None)
        rr1 = r["id"]

        repo_path = os.path.join(self.data_path, "repo_resync_a")
        r = self.repo_api.create('rr2',
                'test_name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(r != None)
        rr2 = r["id"]

        repo_path = os.path.join(self.data_path, "repo_resync_a")
        r = self.repo_api.create('rr3',
                'test_name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(r != None)
        rr3 = r["id"]

        # 2 test distributions
        id = 'ks-test-distro-i386'
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
        arch = 'i386'
        repoids = ['rr1']
        distro = self.distribution_api.create(id, description, relativepath, family= family,
                                              variant=variant, version=version, files=files, arch=arch,
                                              repoids=repoids)
        id = 'ks-test-distro-i386-2'
        description = 'test_distro_description'
        relativepath = "/my/test/path/to/distribution/"
        files = ['/my/test/path/to/distribution/images/boot.iso',
                 '/my/test/path/to/distribution/images/efiboot.img',
                 '/my/test/path/to/distribution/images/install.img',
                 '/my/test/path/to/distribution/images/initrd.img',
                 '/my/test/path/to/distribution/images/vmlinuz']
        family = 'Fedora'
        variant = 'Fedora'
        version = 'F15'
        arch = 'i386'
        repoids = ['rr1', 'rr2']
        distro = self.distribution_api.create(id, description, relativepath, family= family,
                                              variant=variant, version=version, files=files, arch=arch,
                                              repoids=repoids)

    def test_get_distributions(self):
        status, body = self.get('/distributions/')
        self.assertEquals(200, status)
        self.assertEquals(2, len(body))

    def test_get_distributions_filtered(self):
        status, body = self.get('/distributions/?repoids=rr1')
        self.assertEquals(200, status)
        self.assertEquals(2, len(body))

        status, body = self.get('/distributions/?repoids=rr2')
        self.assertEquals(200, status)
        self.assertEquals(1, len(body))
        self.assertEquals(['rr1', 'rr2'], body[0]['repoids'])

        status, body = self.get('/distributions/?repoids=rr2&repoids=rr1&_union=repoids')
        self.assertEquals(200, status)
        self.assertEquals(2, len(body))
        self.assertEquals(['rr1', 'rr2'], body[0]['repoids'])
        self.assertEquals(['rr1'], body[1]['repoids'])

        status, body = self.get('/distributions/?repoids=rr2&repoids=rr1&_intersect=repoids')
        self.assertEquals(200, status)
        self.assertEquals(1, len(body))
        self.assertEquals(['rr1', 'rr2'], body[0]['repoids'])
