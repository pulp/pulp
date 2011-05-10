#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

# Python
import os
import sys
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import mocks
import pulp.server.api.repo
import pulp.server.api.repo_sync as repo_sync
import pulp.server.crontab
import testutil
from pulp.server import constants

constants.LOCAL_STORAGE="/tmp/pulp/"

class TestRepoSyncSchedule(unittest.TestCase):

    def clean(self):
        self.rapi.clean()
        testutil.common_cleanup()

    def setUp(self):
        mocks.install()
        self.config = testutil.load_test_config()
        self.data_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
        self.rapi = pulp.server.api.repo.RepoApi()
        self.clean()

    def tearDown(self):
        self.clean()

    def test_clone(self):

        repo = self.rapi.create('some-id', 'some name', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64/')
        self.assertTrue(repo is not None)
        try:
            self.rapi._sync(repo['id'])
        except Exception:
            # No need for this, an exception with register as a failure and
            # be more informative than the failed assertion
            #self.assertTrue(False)
            raise

        # Try repo cloning default case: feed = parent
        try:
            self.rapi._clone(repo['id'], 'clone-some-id-parent', 'clone-some-id-parent')
        except Exception:
            self.assertTrue(False)
        # Check that local storage has dir and rpms
        dirList = os.listdir(constants.LOCAL_STORAGE + '/repos/' + 'clone-some-id-parent')
        assert(len(dirList) > 0)
        found = self.rapi.repository('clone-some-id-parent')
        packages = found['packages']
        assert(packages is not None)
        assert(len(packages) > 0)

        # Try repo cloning with origin feed
        try:
            self.rapi._clone(repo['id'], 'clone-some-id-origin', 'clone-some-id-origin', feed="origin")
        except Exception:
            self.assertTrue(False)
        # Check that local storage has dir and rpms
        dirList = os.listdir(constants.LOCAL_STORAGE + '/repos/' + 'clone-some-id-origin')
        assert(len(dirList) > 0)
        found = self.rapi.repository('clone-some-id-origin')
        packages = found['packages']
        assert(packages is not None)
        assert(len(packages) > 0)

        # Try repo cloning with no feed
        try:
            self.rapi._clone(repo['id'], 'clone-some-id-none', 'clone-some-id-none', feed="none")
        except Exception:
            self.assertTrue(False)
        # Check that local storage has dir and rpms
        dirList = os.listdir(constants.LOCAL_STORAGE + '/repos/' + 'clone-some-id-none')
        assert(len(dirList) > 0)
        found = self.rapi.repository('clone-some-id-none')
        packages = found['packages']
        assert(packages is not None)
        assert(len(packages) > 0)


    def test_clone_non_existent_repo(self):
        # Negative case where parent repo does not exist
        try:
            self.rapi._clone('some-random-id', 'clone-some-id-parent', 'clone-some-id-parent')
            self.assertTrue(False)
        except Exception:
            self.assertTrue(True)

    def test_clone_repo_with_same_id(self):
        # negative case where repo with clone_id exists
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        repo = self.rapi.create('some-id', 'some name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(repo is not None)
        repo1 = self.rapi.create('some-id-1', 'some name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(repo1 is not None)

        try:
            self.rapi._clone('some-id', 'some-id-1', 'clone-some-id-parent')
            self.assertTrue(False)
        except Exception:
            self.assertTrue(True)

