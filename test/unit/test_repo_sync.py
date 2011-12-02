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

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil
import mock

from pulp.server import async
from pulp.server.api import repo_sync
from pulp.server.api.synchronizers import (YumSynchronizer, 
    yum_rhn_progress_callback, local_progress_callback)


class TestRepoSync(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.mock(repo_sync, "run_async")

    def tearDown(self):
        testutil.PulpAsyncTest.tearDown(self)

    def test_sync_remote(self):
        # create a remote repo
        remote_repo = self.repo_api.create("testrepoid", "testrepoid", "x86_64",
            "http://www.example.com")

        # sync the remote_repo
        repo_sync.sync(remote_repo["id"])

        # run_async called once, and a task is returned
        self.assertEquals(1, repo_sync.run_async.call_count)
        task = repo_sync.run_async.return_value

        # task.set_progress called
        self.assertEquals(1, task.set_progress.call_count)
        call_args = task.set_progress.call_args[0]
        self.assertEquals(2, len(call_args))
        self.assertEquals("progress_callback", call_args[0])
        self.assertEquals(yum_rhn_progress_callback, call_args[1])

        # task.set_synchronizer called
        self.assertEquals(1, task.set_synchronizer.call_count)
        call_args = task.set_synchronizer.call_args[0]
        self.assertEquals(1, len(call_args))
        self.assertTrue(isinstance(call_args[0], YumSynchronizer))

    def test_sync_local(self):
        # create a local_repo
        local_repo = self.repo_api.create("testrepoid2", "testrepoid2", "x86_64",
            "file://repo")

        # sync the local_repo
        repo_sync.sync(local_repo["id"])

        # run_async called once, and a task is returned
        self.assertEquals(1, repo_sync.run_async.call_count)
        task = repo_sync.run_async.return_value

        # task.set_progress called
        self.assertEquals(1, task.set_progress.call_count)
        call_args = task.set_progress.call_args[0]
        self.assertEquals(2, len(call_args))
        self.assertEquals("progress_callback", call_args[0])
        self.assertEquals(local_progress_callback, call_args[1])

        # task.set_synchronizer called
        self.assertEquals(1, task.set_synchronizer.call_count)
        call_args = task.set_synchronizer.call_args[0]
        self.assertEquals(1, len(call_args))
        self.assertTrue(isinstance(call_args[0], YumSynchronizer))

    def test_local_sync(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir = my_dir + "/data/repo_resync_b"
        print "Data DIR %s" % datadir
        repo = self.repo_api.create('some-id', 'some name', 'i386',
                                'file://%s' % datadir)

        repo_sync._sync(repo['id'])
        found = self.repo_api.repository(repo['id'])
        packages = found['packages']
        print "Packages :: %s" % packages
        assert(packages is not None)
        assert(len(packages) > 0)
        p = packages[0]
        assert(p is not None)
        # versions = p['versions']

    def test_clone(self):
        local_repo = self.repo_api.create("testrepocln", "testrepocln", "x86_64",
            "file://repo")
        # clone
        repo_sync.clone(local_repo["id"], "testrepocln_clone", "testrepocln_clone")

        # run_async called once, and a task is returned
        self.assertEquals(1, repo_sync.run_async.call_count)
        task = repo_sync.run_async.return_value

        # task.set_progress called
        self.assertEquals(1, task.set_progress.call_count)
        call_args = task.set_progress.call_args[0]
        self.assertEquals(2, len(call_args))
        self.assertEquals("progress_callback", call_args[0])
        self.assertEquals(local_progress_callback, call_args[1])

        # task.set_synchronizer called
        self.assertEquals(1, task.set_synchronizer.call_count)
        call_args = task.set_synchronizer.call_args[0]
        self.assertEquals(1, len(call_args))
        self.assertTrue(isinstance(call_args[0], YumSynchronizer))
        # validate if the clone is enabled on the synchronizer
        self.assertEquals(local_repo["id"], call_args[0].clone)
