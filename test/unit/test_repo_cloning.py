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
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import pulp.server.api.repo
import pulp.server.api.repo_sync as repo_sync
import pulp.server.crontab
from pulp.server import constants, async
from pulp.server.api import repo_sync

constants.LOCAL_STORAGE="/tmp/pulp/"

class TestRepoSyncSchedule(testutil.PulpAsyncTest):

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

    def test_clone(self):

        repo = self.repo_api.create('some-id', 'some name', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/fedora-15/x86_64/')
        self.assertTrue(repo is not None)
        try:
            repo_sync._sync(repo['id'])
        except Exception:
            # No need for this, an exception with register as a failure and
            # be more informative than the failed assertion
            #self.assertTrue(False)
            raise

        # Try repo cloning default case: feed = parent
        try:
            repo_sync.clone(repo['id'], 'clone-some-id-parent', 'clone-some-id-parent')
        except Exception, e:
            print "Exception caught: ", e
            self.assertTrue(False)
            raise

        running_clone = self.check_if_running_clone('clone-some-id-parent')
        while running_clone:
            time.sleep(2)
            running_clone = self.check_if_running_clone('clone-some-id-parent')
            print "Clone still running"

        # Check that local storage has dir and rpms
        dirList = os.listdir(constants.LOCAL_STORAGE + '/repos/' + 'clone-some-id-parent')
        assert(len(dirList) > 0)
        found = self.repo_api.repository('clone-some-id-parent')
        packages = found['packages']
        assert(packages is not None)
        #assert(len(packages) > 0)
        #validate content_types
        assert(found['content_types'] == repo['content_types'])

        # Try repo cloning with origin feed
        try:
            repo_sync.clone(repo['id'], 'clone-some-id-origin', 'clone-some-id-origin', feed="origin")
        except Exception:
            self.assertTrue(False)

        running_clone = self.check_if_running_clone('clone-some-id-parent')
        while running_clone:
            time.sleep(2)
            running_clone = self.check_if_running_clone('clone-some-id-parent')
            print "Clone still running"

        # Check that local storage has dir and rpms
        dirList = os.listdir(constants.LOCAL_STORAGE + '/repos/' + 'clone-some-id-origin')
        assert(len(dirList) > 0)
        found = self.repo_api.repository('clone-some-id-origin')
        packages = found['packages']
        assert(packages is not None)
        #assert(len(packages) > 0)

        # Try repo cloning with no feed
        try:
            repo_sync.clone(repo['id'], 'clone-some-id-none', 'clone-some-id-none', feed="none")
        except Exception:
            self.assertTrue(False)

        running_clone = self.check_if_running_clone('clone-some-id-parent')
        while running_clone:
            time.sleep(2)
            running_clone = self.check_if_running_clone('clone-some-id-parent')
            print "Clone still running"

        # Check that local storage has dir and rpms
        dirList = os.listdir(constants.LOCAL_STORAGE + '/repos/' + 'clone-some-id-none')
        assert(len(dirList) > 0)
        found = self.repo_api.repository('clone-some-id-none')
        packages = found['packages']
        assert(packages is not None)
        #assert(len(packages) > 0)


    def test_clone_non_existent_repo(self):
        # Negative case where parent repo does not exist
        try:
            repo_api.clone('some-random-id', 'clone-some-id-parent', 'clone-some-id-parent')
            self.assertTrue(False)
        except Exception:
            self.assertTrue(True)

    def test_clone_repo_with_same_id(self):
        # negative case where repo with clone_id exists
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        repo = self.repo_api.create('some-id', 'some name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(repo is not None)
        repo1 = self.repo_api.create('some-id-1', 'some name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(repo1 is not None)

        try:
            repo_api.clone('some-id-1', 'some-id', 'clone-some-id-parent')
            self.assertTrue(False)
        except Exception:
            self.assertTrue(True)

