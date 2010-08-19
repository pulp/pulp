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

import pulp.server.api.repo
import pulp.server.api.repo_sync
import pulp.server.crontab
import testutil

class TestRepoSyncSchedule(unittest.TestCase):

    def setUp(self):
        self.config = testutil.load_test_config()
        self.repo_api = pulp.server.api.repo.RepoApi()

    def tearDown(self):
        self.repo_api.clean()
        tab = pulp.server.crontab.CronTab()

        for entry in tab.find_command('pulp repo sync'):
            tab.remove(entry)
        tab.write()

    def test_update_delete_schedule(self):
        '''
        Tests multiple updates to a repo's sync schedule and the case where multiple updates
        are created with no schedules.
        '''

        # Setup
        repo_id = 'repo-sync-schedule'
        sync_schedule = '* * * * *'
        sync_schedule_2 = '2 2 2 2 2'

        #   Create the repo
        self.repo_api.create(repo_id, 'Repo Sync Schedule', 'noarch', 'yum://foo')

        # -- Update #1 ----------
        repo = self.repo_api.repository(repo_id)
        repo['sync_schedule'] = sync_schedule
        self.repo_api.update(repo)

        # Verify
        tab = pulp.server.crontab.CronTab()
        items = tab.find_command('pulp repo sync %s' % repo_id)
        self.assertEqual(1, len(items))

        print('Update #1 [%s]' % items[0].render())

        # -- Update #2 ----------
        repo = self.repo_api.repository(repo_id)
        repo['sync_schedule'] = sync_schedule_2
        self.repo_api.update(repo)

        # Verify
        tab = pulp.server.crontab.CronTab()
        items = tab.find_command('pulp repo sync %s' % repo_id)
        self.assertEqual(1, len(items))

        print('Update #2 [%s]' % items[0].render())

        # -- Delete #1 ----------
        repo = self.repo_api.repository(repo_id)
        repo['sync_schedule'] = None
        self.repo_api.update(repo)

        # Verify
        tab = pulp.server.crontab.CronTab()
        items = tab.find_command('pulp repo sync %s' % repo_id)
        self.assertEqual(0, len(items))

        # -- Delete #2 ----------
        repo = self.repo_api.repository(repo_id)
        repo['sync_schedule'] = None
        self.repo_api.update(repo)

        # Verify
        tab = pulp.server.crontab.CronTab()
        items = tab.find_command('pulp repo sync %s' % repo_id)
        self.assertEqual(0, len(items))

    def test_create_invalid_schedule_syntax(self):
        # Test
        self.assertRaises(Exception, self.repo_api.create, 'invalid', 'Repo Sync Schedule', 'noarch', 'yum://foo', sync_schedule='* * * * foo')

    def test_update_invalid_schedule_syntax(self):
        # Setup
        repo_id = 'invalid-update'
        self.repo_api.create(repo_id, 'Repo Sync Schedule', 'noarch', 'yum://foo')

        # Test
        repo = self.repo_api.repository(repo_id)
        repo['sync_schedule'] = 'foo'
        self.assertRaises(Exception, self.repo_api.update, repo)

    def test_all_schedules(self):
        # Setup
        self.repo_api.create('repo-1', 'repo-1', 'i386', 'yum:localhost', sync_schedule='1 * * * *')
        self.repo_api.create('repo-2', 'repo-2', 'i386', 'yum:localhost', sync_schedule='2 * * * *')
        self.repo_api.create('repo-3', 'repo-3', 'i386', 'yum:localhost', sync_schedule=None)
        self.repo_api.create('repo-4', 'repo-4', 'i386', 'yum:localhost')

        # Test
        schedules = self.repo_api.all_schedules()
        print(schedules)

        # Verify
        self.assertEqual(4, len(schedules))

        self.assertEqual('1 * * * *', schedules['repo-1'])
        self.assertEqual('2 * * * *', schedules['repo-2'])
        self.assertEqual(None, schedules['repo-3'])
        self.assertEqual(None, schedules['repo-4'])
