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
from pulp.server.util import top_repos_location

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil
import mock

from pulp.server import async
from pulp.server.api import repo_sync
from pulp.server.api.synchronizers import (FileSynchronizer,
    yum_rhn_progress_callback, local_progress_callback)


class TestFileSync(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.mock(repo_sync, "run_async")
        self.mock(async, 'enqueue')

    def tearDown(self):
        testutil.PulpAsyncTest.tearDown(self)

    def test_file_repo_create(self):
        # create a remote repo
        remote_repo = self.repo_api.create("test_file_repo_id", "test_file_repo_id", "noarch",
            "http://www.example.com/foo", content_types="file")
        assert(remote_repo['content_types'] == "file")

    def test_file_repo_create_no_metadata(self):
        # create a remote repo
        remote_repo = self.repo_api.create("test_file_repo_id", "test_file_repo_id", "noarch",
            "http://www.example.com/foo", content_types="file")
        d = os.path.join(top_repos_location(), remote_repo['relative_path'])
        self.assertTrue(os.path.isdir(d))
        dirList = os.listdir(d)
        # should be empty and no repodata created
        assert(len(dirList) == 0)
        
    def test_file_sync_remote(self):
        # create a remote repo
        remote_repo = self.repo_api.create("test_file_repo_id", "test_file_repo_id", "noarch",
            "http://www.example.com", content_types="file")

        # sync the remote_repo
        repo_sync.sync(remote_repo["id"])

        # run_async called once, and a task is returned
        self.assertEquals(1, async.enqueue.call_count)

    def test_file_sync_local(self):
        # create a local_repo
        local_repo = self.repo_api.create("test_file_repo_local", "test_file_repo_local", "noarch",
            "file://repo", content_types="file")

        # sync the local_repo
        repo_sync.sync(local_repo["id"])

        # run_async called once, and a task is returned
        self.assertEquals(1, async.enqueue.call_count)


