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
from threading import Thread

srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.server import async
from pulp.server.api import repo_sync
from pulp.server.api.repo import RepoApi
from pulp.server.db.model import persistence
from pulp.server.util import chunks
from pulp.server.util import get_rpm_information
from pulp.server.util import get_repo_packages
from pulp.server.util import get_repo_package
from pulp.server.util import get_relative_path
import testutil

logging.root.setLevel(logging.INFO)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

CERTS_DIR = '/tmp/test_repo_api/repos'
class TestUtil(unittest.TestCase):

    def setUp(self):
        self.config = testutil.load_test_config()
        self.config.set('repos', 'cert_location', CERTS_DIR)

        self.data_path = \
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
        self.rapi = RepoApi()
        async.initialize()
        self.clean()

    def clean(self):
        self.rapi.clean()
        testutil.common_cleanup()
        persistence.TaskSnapshot.get_collection().remove()
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

    def test_get_repo_packages(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir_a = my_dir + "/data/sameNEVRA_differentChecksums/A/repo/"
        packages = get_repo_packages(datadir_a)
        self.assertTrue(len(packages) > 0)
        p = packages[0]
        self.assertTrue(p.name is not None)

    def test_get_repo_package(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir_a = my_dir + "/data/sameNEVRA_differentChecksums/A/repo/"
        package = get_repo_package(datadir_a,
                      'pulp-test-package-same-nevra-0.1.0-1.x86_64.rpm')
        self.assertNotEquals(package, None)
        self.assertNotEquals(package.name, None)

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

    def test_get_repo_packages_multi_repo(self):
        # We are testing 2 issues with this test
        # 1) Trying to re-create "pycurl.error"
        # 2) Causing a Segmentation fault from libcurl 'Curl_done'
        #
        # We want to recreate a scenario to force the below pycurl.error
        #  File "/home/hudson/workspace/pulp-dev/test/unit/../../src/pulp/server/util.py", line 214, in get_repo_packages
        #    r.sack.populate(r, 'metadata', None, 0)
        #  ......
        #  File "/usr/lib/python2.7/site-packages/yum/yumRepo.py", line 1405, in _getRepoXML
        #    self._loadRepoXML(text=self)
        #  ......
        #  File "/usr/lib/python2.7/site-packages/urlgrabber/grabber.py", line 1161, in _set_opts
        #    self.curl_obj.setopt(pycurl.NOPROGRESS, False)
        #error: cannot invoke setopt() - perform() is currently running
        class TestMultiGetRepoPkgsThreads(Thread):
            def __init__ (self, data_dir):
                Thread.__init__(self)
                self.stopped = False
                self.caught = False
                self.caught_exception = None
                self.data_dir = data_dir
            def run(self):
                while not self.stopped:
                    try:
                        get_repo_packages(data_dir)
                    except Exception, e:
                        self.caught = True
                        self.caught_exception = e
                        tb_info = traceback.format_exc()
                        print "Traceback: %s" % (tb_info)

        repo_a = self.rapi.create('test_get_repo_packages_multi_repo_pulp_f14_A',
                                'pulp_f14_background_sync', 'x86_64',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64/')
        self.assertTrue(repo_a is not None)
        background_sync_task_a = repo_sync.sync(repo_a['id'])

        repo_b = self.rapi.create('test_get_repo_packages_multi_repo_pulp_f14_B',
                                'pulp_f14_background_sync', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/i386/')
        self.assertTrue(repo_b is not None)
        background_sync_task_b = repo_sync.sync(repo_b['id'])
        my_dir = os.path.abspath(os.path.dirname(__file__))
        data_dir = my_dir + "/data/sameNEVRA_differentChecksums/A/repo/"
        test_threads = [TestMultiGetRepoPkgsThreads(data_dir) for x in range(0,5)]
        for t in test_threads:
            t.start()
        time.sleep(2)
        caught = False
        for t in test_threads:
            t.stopped = True
            t.join()
            if t.caught:
                caught = True
                print "t.caught_exception = %s" % (t.caught_exception)
        self.assertFalse(caught)






if __name__ == '__main__':
    unittest.main()
