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
import shutil
import sys
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import pulp.api.repo
import pulp.api.repo_sync

import testutil

class TestRepoSyncSchedule(unittest.TestCase):

    def setUp(self):
        self.config = testutil.load_test_config()
        self.repo_api = pulp.api.repo.RepoApi(self.config)
        os.mkdir(self.config.get('paths', 'repo_sync_cron'))

    def tearDown(self):
        self.repo_api.clean()
        shutil.rmtree(self.config.get('paths', 'repo_sync_cron'))

    def test_update_schedule(self):
        # Setup
        repo_id = 'repo-sync-schedule'
        sync_schedule = '* * * * *'

        #   Create the repo
        self.repo_api.create(repo_id, 'Repo Sync Schedule', 'noarch', 'yum://foo')

        #   Set the repo's sync schedule
        repo = self.repo_api.repository(repo_id)
        repo['sync_schedule'] = sync_schedule
        self.repo_api.update(repo)

        # Test
        pulp.api.repo_sync.update_schedule(self.config, repo)

        # Verify
        file_name = pulp.api.repo_sync._sync_file_name(self.config, repo)
        self.assertTrue(os.path.exists(file_name))

        f = open(file_name, 'r')
        contents = f.read()

        self.assertTrue(contents.startswith(sync_schedule))
