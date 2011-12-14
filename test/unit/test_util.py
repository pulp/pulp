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

        repo_a = self.repo_api.create('test_get_repo_packages_multi_repo_pulp_f14_A',
                                'pulp_f14_background_sync', 'x86_64',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64/')
        self.assertTrue(repo_a is not None)
        #background_sync_task_a = repo_sync.sync(repo_a['id'])

        repo_b = self.repo_api.create('test_get_repo_packages_multi_repo_pulp_f14_B',
                                'pulp_f14_background_sync', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/i386/')
        self.assertTrue(repo_b is not None)
        #background_sync_task_b = repo_sync.sync(repo_b['id'])
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

        sync_tasks = []
        #sync_tasks.append(background_sync_task_a)
        #sync_tasks.append(background_sync_task_b)

        # Poll tasks and wait for sync to finish
        waiting_tasks = [t.id for t in sync_tasks]
        count = 0
        wait_count = 180 # 3 minutes
        while len(waiting_tasks) > 0 and count < wait_count:
            time.sleep(1)
            count += 1
            for t_id in waiting_tasks:
                found_tasks = async.find_async(id=t_id)
                self.assertEquals(len(found_tasks), 1)
                updated_task = found_tasks[0]
                if updated_task.state in task.task_complete_states:
                    self.assertEquals(updated_task.state, task.task_finished)
                    waiting_tasks.remove(t_id)
        self.assertTrue(count < wait_count)

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
