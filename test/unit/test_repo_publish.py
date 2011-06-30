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

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import pulp.server.api.repo
import pulp.server.crontab
from pulp.server.api import repo_sync

class TestRepoPublish(testutil.PulpAsyncTest):

    def test_repo_publish(self):
        # Setup
        repo_id = 'test_repo_publish'
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        repo = self.repo_api.create(repo_id, 'Repo Publish', 'noarch', 
                'file://%s' % (repo_path))
        # Verify that repo 'published' defaulted to whatever is in config
        self.assertEquals(repo["publish"], 
                self.config.getboolean('repos', 'default_to_published'))
        # Sync Repo
        repo_sync._sync(repo["id"])
        repo = self.repo_api.repository(repo_id)

        # Ensure Repo is Published
        if not repo["publish"]:
            self.repo_api.publish(repo, True)
        repo = self.repo_api.repository(repo_id)
        self.assertTrue(repo["publish"])
        # Verify symlink exists for published repo
        expected_link = os.path.join(self.repo_api.published_path,
            repo['relative_path'])
        self.assertTrue(os.path.islink(expected_link))

        # Disable publish on repo
        self.repo_api.publish(repo_id, False)
        repo = self.repo_api.repository(repo_id)
        self.assertFalse(repo["publish"])
        # Verify symlink does not exist
        self.assertFalse(os.path.islink(expected_link))

