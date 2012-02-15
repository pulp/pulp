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

    def clean(self):
        pulp.server.api.repo.RepoApi().clean()

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

    def test_clone(self, id = 'some-id', clone_id = 'clone-some-id-parent', clone_id1 = 'clone-some-id-origin',
                   clone_id2 = 'clone-some-id-none'):

        repo = self.repo_api.create(id, 'some name', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/v1/testing/fedora-15/x86_64/')
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
            repo_sync.clone(repo['id'], clone_id, 'clone-some-id-parent')
        except Exception, e:
            print "Exception caught: ", e
            self.assertTrue(False)
            raise

        running_clone = self.check_if_running_clone(clone_id)
        while running_clone:
            time.sleep(2)
            running_clone = self.check_if_running_clone(clone_id)
            print "Clone still running"

        # Check that local storage has dir and rpms
        dirList = os.listdir(constants.LOCAL_STORAGE + '/repos/' + clone_id)
        assert(len(dirList) > 0)
        found = self.repo_api.repository(clone_id)
        packages = found['packages']
        assert(packages is not None)
        #assert(len(packages) > 0)
        #validate content_types
        assert(found['content_types'] == repo['content_types'])

        # Try repo cloning with origin feed
        try:
            repo_sync.clone(repo['id'], clone_id1, 'clone-some-id-origin', feed="origin")
        except Exception:
            self.assertTrue(False)

        running_clone = self.check_if_running_clone(clone_id1)
        while running_clone:
            time.sleep(2)
            running_clone = self.check_if_running_clone(clone_id1)
            print "Clone still running"

        # Check that local storage has dir and rpms
        dirList = os.listdir(constants.LOCAL_STORAGE + '/repos/' + clone_id1)
        assert(len(dirList) > 0)
        found = self.repo_api.repository(clone_id1)
        packages = found['packages']
        assert(packages is not None)
        #assert(len(packages) > 0)

        # Try repo cloning with no feed
        try:
            repo_sync.clone(repo['id'], clone_id2, 'clone-some-id-none', feed="none")
        except Exception:
            self.assertTrue(False)

        running_clone = self.check_if_running_clone(clone_id2)
        while running_clone:
            time.sleep(2)
            running_clone = self.check_if_running_clone(clone_id2)
            print "Clone still running"

        # Check that local storage has dir and rpms
        dirList = os.listdir(constants.LOCAL_STORAGE + '/repos/' + clone_id2)
        assert(len(dirList) > 0)
        found = self.repo_api.repository(clone_id2)
        packages = found['packages']
        assert(packages is not None)
        #assert(len(packages) > 0)


    def test_clone_non_existent_repo(self, id = 'some-random-id', clone_id = 'clone-some-id-parent'):
        # Negative case where parent repo does not exist
        try:
            repo_api.clone(id, clone_id, 'clone-some-id-parent')
            self.assertTrue(False)
        except Exception:
            self.assertTrue(True)

    def test_clone_repo_with_same_id(self, id = 'some-id1', clone_id = 'some-id2'):
        # negative case where repo with clone_id exists
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        repo = self.repo_api.create(id, 'some name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(repo is not None)
        repo1 = self.repo_api.create(clone_id, 'some name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(repo1 is not None)

        try:
            repo_api.clone(id, clone_id, 'clone-some-id-parent')
            self.assertTrue(False)
        except Exception:
            self.assertTrue(True)

    def test_clone_publish(self, id = 'some-id', clone_id = 'clone-publish-true', clone_id1 = 'clone-publish-false',
                           clone_id2 = 'clone-publish-default'):

        repo = self.repo_api.create(id, 'some name', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/v1/testing/fedora-15/x86_64/')
        self.assertTrue(repo is not None)
        try:
            repo_sync._sync(repo['id'])
        except Exception:
            raise

        repo_sync.clone(repo['id'], clone_id, 'clone-publish-true', publish=True)
        clone_repo = self.repo_api.repository(clone_id)
        self.assertEquals(clone_repo['publish'], True)

        repo_sync.clone(repo['id'], clone_id1, 'clone-publish-false', publish=False)
        clone_repo = self.repo_api.repository(clone_id1)
        self.assertEquals(clone_repo['publish'], False)

        repo_sync.clone(repo['id'], clone_id2, 'clone-publish-false')
        clone_repo = self.repo_api.repository(clone_id2)
        self.assertEquals(clone_repo['publish'], True)

    def test_repo_clone_with_i18n_id(self):
        id = u'\u0938\u093e\u092f\u0932\u0940'
        clone_id = u'\u0938\u093e\u092f\u0932'
        clone_id1 = u'\u0938\u093e\u092f'
        clone_id2 = u'\u0938\u093e'
        self.test_clone(id, clone_id, clone_id1, clone_id2)
        self.clean()
        self.test_clone_repo_with_same_id(id, clone_id)
        self.clean()
        self.test_clone_non_existent_repo(id, clone_id)
        self.clean()
        self.test_clone_publish(id, clone_id, clone_id1, clone_id2)
