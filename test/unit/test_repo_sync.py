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

import sys

sys.path.insert(0, "../common")
import testutil
import dingus

from pulp.server import async
from pulp.server.api import repo_sync
from pulp.server.api.synchronizers import (YumSynchronizer, 
    yum_rhn_progress_callback, local_progress_callback, LocalSynchronizer)


class TestRepoSync(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)
        repo_sync.run_async = dingus.Dingus()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        repo_sync.run_async.reset()

    def test_sync_remote(self):
        # create a remote repo
        remote_repo = self.repo_api.create("testrepoid", "testrepoid", "x86_64",
            "http://www.example.com")

        # sync the remote_repo
        repo_sync.sync(remote_repo["id"])

        # run_async called once, and a task is returned
        self.assertEquals(1, len(repo_sync.run_async.calls))
        task = repo_sync.run_async.calls[0].return_value

        # task.set_progress called
        self.assertEquals(1, len(task.set_progress.calls))
        callArgs = task.set_progress.calls[0].args
        self.assertEquals(2, len(callArgs))
        self.assertEquals("progress_callback", callArgs[0])
        self.assertEquals(yum_rhn_progress_callback, callArgs[1])

        # task.set_synchronizer called
        self.assertEquals(1, len(task.set_synchronizer.calls))
        callArgs = task.set_synchronizer.calls[0].args
        self.assertEquals(1, len(callArgs))
        self.assertTrue(isinstance(callArgs[0], YumSynchronizer))

    def test_sync_local(self):
        # create a local_repo
        local_repo = self.repo_api.create("testrepoid2", "testrepoid2", "x86_64",
            "file://repo")

        # sync the local_repo
        repo_sync.sync(local_repo["id"])

        # run_async called once, and a task is returned
        self.assertEquals(1, len(repo_sync.run_async.calls))
        task = repo_sync.run_async.calls[0].return_value

        # task.set_progress called
        self.assertEquals(1, len(task.set_progress.calls))
        callArgs = task.set_progress.calls[0].args
        self.assertEquals(2, len(callArgs))
        self.assertEquals("progress_callback", callArgs[0])
        self.assertEquals(local_progress_callback, callArgs[1])

        # task.set_synchronizer called
        self.assertEquals(1, len(task.set_synchronizer.calls))
        callArgs = task.set_synchronizer.calls[0].args
        self.assertEquals(1, len(callArgs))
        self.assertTrue(isinstance(callArgs[0], LocalSynchronizer))
