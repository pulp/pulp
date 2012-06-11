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
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil
import mock

from pulp.server import async
from pulp.server.api import repo_sync, repo_clone_task
from pulp.server.api.synchronizers import (YumSynchronizer, 
    yum_rhn_progress_callback, local_progress_callback)


class TestRepoSync(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.mock(repo_sync, "run_async")
        self.mock(async, 'enqueue')
        self.test_data_dir = os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                "data")


    def tearDown(self):
        testutil.PulpAsyncTest.tearDown(self)

    def clean(self):
        self.repo_api.clean()

    def _task_to_dict(self, task):
        """
        Convert a task to a dictionary (non-destructive) while retaining the
        pertinent information for a status check.
        @type task: Task instance
        @param task: task to convert
        @return dict representing task
        """
        fields = ('id', 'state')
        d = dict((f, getattr(task, f)) for f in fields)
        return d

    def running_task(self, task_list):
        """
        Iterate over a list of tasks and return one that is currently running.
        If no such task is found, return None.
        """
        for task in task_list:
            if task['state'] == 'running' or task['state'] == 'waiting':
                return task
        return None

    def check_if_running_clone(self, id):
        clones = [t for t in async.find_async(method_name='_clone')
                 if (t.args and id in t.args) or
                 (t.kwargs and id in t.kwargs.values())]
        if clones:
            clone_infos = []
            for clone in clones:
                info = self._task_to_dict(clone)
                clone_infos.append(info)
            running_clone = self.running_task(clone_infos)
            return running_clone

    def test_sync_remote(self, id = "testrepoid"):
        # create a remote repo
        remote_repo = self.repo_api.create(id, "testrepoid", "x86_64",
            "http://www.example.com")
        orig_async_count = async.enqueue.call_count
        # sync the remote_repo
        repo_sync.sync(remote_repo["id"])

        # run_async called once, and a task is returned
        self.assertEquals(1 + orig_async_count, async.enqueue.call_count)

    def test_sync_local(self, id = "testrepoid2"):
        # create a local_repo
        local_repo = self.repo_api.create(id, "testrepoid2", "x86_64",
            "file://repo")
        orig_async_count = async.enqueue.call_count
        # sync the local_repo
        repo_sync.sync(local_repo["id"])

        # run_async called once, and a task is returned
        self.assertEquals(1 + orig_async_count, async.enqueue.call_count)

    def test_local_sync(self, id = 'some-id'):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir = my_dir + "/data/repo_resync_b"
        print "Data DIR %s" % datadir
        repo = self.repo_api.create(id, 'some name', 'i386',
                                'file://%s' % datadir)

        repo_sync._sync(id)
        found = self.repo_api.repository(id)
        packages = found['packages']
        print "Packages :: %s" % packages
        assert(packages is not None)
        assert(len(packages) > 0)
        p = packages[0]
        assert(p is not None)
        # versions = p['versions']

    def test_clone(self, id = "testrepocln"):
        local_repo = self.repo_api.create(id, "testrepocln", "x86_64",
            "file://repo")
        # clone
        repo_sync.clone(local_repo["id"], "testrepocln_clone", "testrepocln_clone")

        # run_async called once, and a task is returned
        self.assertEquals(1, async.enqueue.call_count)

        running_clone = self.check_if_running_clone('testrepocln_clone')
        while running_clone:
            time.sleep(2)
            running_clone = self.check_if_running_clone('testrepocln_clone')
            print "Clone still running"

    def test_repo_sync_with_i18n_id(self):
        id = u'\u0938\u093e\u092f\u0932\u0940'
        self.test_clone(id)
        self.clean()
        self.test_sync_local(id)
        self.clean()
        self.test_sync_remote(id)

    def test_repo_sync_local_read_only_source(self):
        read_only_dir = os.path.join(self.test_data_dir, "repo_no_write_perms")
        r_id = "test_repo_sync_local_read_only_source"
        print "read_only_dir = %s" % (read_only_dir)
        r = self.repo_api.create(r_id, r_id, "x86_64", "file://%s" % read_only_dir)
        repo_sync._sync(r_id)
        found = self.repo_api.repository(r_id)
        self.assertEquals(len(found["packages"]), 1)

if __name__ == "__main__":
    unittest.main()
