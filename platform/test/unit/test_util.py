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

import logging
import os
import sys
import time
import traceback
import unittest
import shutil
from threading import Thread

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server import async
from pulp.server.api import repo_sync
from pulp.server.api.repo import RepoApi
from pulp.server.db.model import persistence
from pulp.server.util import chunks
from pulp.server.tasking import task
from pulp.server.util import get_rpm_information
from pulp.server.util import get_repo_packages
from pulp.server.util import get_repo_package
from pulp.server.util import get_relative_path
from pulp.server.util import makedirs

logging.root.setLevel(logging.INFO)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

CERTS_DIR = '/tmp/test_repo_api/repos'


class TestUtil(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.config.set('repos', 'cert_location', CERTS_DIR)

    def clean(self):
        testutil.PulpAsyncTest.clean(self)
        persistence.TaskSnapshot.get_collection().remove(safe=True)
        persistence.TaskHistory.get_collection().remove()

    def test_getrpminfo(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir = my_dir + "/data"
        info = get_rpm_information(datadir + '/pulp-test-package-0.2.1-1.fc11.x86_64.rpm')
        assert(info is not None)
        assert(info['version'] == '0.2.1')
        assert(info['name'] == 'pulp-test-package')

    def test_chunks(self):
        list = range(1003)
        ck = chunks(list, 100)
        assert(len(ck) == 11)
        total = 0
        for chunk in ck:
            total = total + len(chunk)
        assert(total == 1003)

    def test_get_relative_path(self):
        src = "/var/lib/pulp/repos/released/F-13/GOLD/Fedora/x86_64/os/Packages/bzip2-devel-1.0.5-6.fc12.i686.rpm"
        dst = "/var/lib/pulp/repos/released/F-13/GOLD/Fedora/x86_64/os/Packages/new_name.rpm"
        rel = get_relative_path(src, dst)
        expected_rel = "bzip2-devel-1.0.5-6.fc12.i686.rpm"
        self.assertEquals(rel, expected_rel)

        src = "/var/lib/pulp/repos/released/F-13/GOLD/Fedora/x86_64/bzip2-devel-1.0.5-6.fc12.i686.rpm"
        dst = "/var/lib/pulp/repos/released/F-13/GOLD/Fedora/x86_64/os/Packages/bzip2-devel-1.0.5-6.fc12.i686.rpm"
        rel = get_relative_path(src, dst)
        expected_rel = "../../bzip2-devel-1.0.5-6.fc12.i686.rpm"
        self.assertEquals(rel, expected_rel)

        #Test typical case
        src = "/var/lib/pulp//packages/ece/bzip2-devel/1.0.5/6.fc12/i686/bzip2-devel-1.0.5-6.fc12.i686.rpm"
        dst = "/var/lib/pulp/repos/released/F-13/GOLD/Fedora/x86_64/os/Packages/bzip2-devel-1.0.5-6.fc12.i686.rpm"
        rel = get_relative_path(src, dst)
        expected_rel = "../../../../../../../../packages/ece/bzip2-devel/1.0.5/6.fc12/i686/bzip2-devel-1.0.5-6.fc12.i686.rpm"
        self.assertEqual(rel, expected_rel)


        #Test case where no common path element exists except for "/"
        src = "/packages/ece/bzip2-devel/1.0.5/6.fc12/i686/bzip2-devel-1.0.5-6.fc12.i686.rpm"
        dst = "/var/lib/pulp/repos/released/F-13/GOLD/Fedora/x86_64/os/Packages/bzip2-devel-1.0.5-6.fc12.i686.rpm"
        rel = get_relative_path(src, dst)
        expected_rel = "../../../../../../../../../../.." + src
        self.assertEquals(rel, expected_rel)

        src = "/var/lib/pulp/packages/ruby-gofer/0.20/1.fc14/noarch/804/ruby-gofer-0.20-1.fc14.noarch.rpm"
        dst = "/var/lib/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/ruby-gofer-0.20-1.fc14.noarch.rpm"
        rel = get_relative_path(src, dst)
        expected_rel = "../../../../../../packages/ruby-gofer/0.20/1.fc14/noarch/804/ruby-gofer-0.20-1.fc14.noarch.rpm"
        self.assertEquals(rel, expected_rel)

    def test_makdirs(self):
        root = '/tmp/test_makedirs'
        shutil.rmtree(root, True)
        path = os.path.join(root, 'A/B/C')
        makedirs(path)
        self.assertTrue(os.path.exists(path) and os.path.isdir(path))
        for d in ('A','B','C'):
            path = os.path.join(root, d)
            makedirs(path)
            self.assertTrue(os.path.exists(path) and os.path.isdir(path))
        for d in ('C','//B','A'):
            path = '/'.join((root, d))
            makedirs(path)
            self.assertTrue(os.path.exists(path) and os.path.isdir(path))
        # test non-dir in the path
        shutil.rmtree(root, True)
        makedirs(root)
        path = os.path.join(root, 'A')
        f = open(path, 'w')
        f.close()
        path = os.path.join(path, 'B', 'C')
        self.assertRaises(OSError, makedirs, path)
        shutil.rmtree(root, True)

if __name__ == '__main__':
    unittest.main()
