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
from pulp.server import constants
from pulp.server.api import repo_sync

constants.LOCAL_STORAGE="/tmp/pulp/"

class TestRepoSyncSchedule(testutil.PulpAsyncTest):

    def test_clone(self):

        repo = self.repo_api.create('some-id', 'some name', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64/')
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

