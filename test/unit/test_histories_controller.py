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

import datetime
import os
import sys

import mock

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.common import dateutils
from pulp.server.api import repo
from pulp.server.api import repo_sync
from pulp.server.api import repo_sync_task
from pulp.server.db.model import TaskHistory
from pulp.server.tasking import task
from pulp.server.webservices.controllers import statuses

class HistoriesTest(testutil.PulpWebserviceTest):

    def setUp(self):
        testutil.PulpWebserviceTest.setUp(self)
        self.setup_repos()

    def setup_repos(self):
        # 3 test repos
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        r = self.repo_api.create('rr1',
                'test_name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(r != None)
        rr1 = r["id"]

        repo_path = os.path.join(self.data_path, "repo_resync_a")
        r = self.repo_api.create('rr2',
                'test_name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(r != None)
        rr2 = r["id"]

        scheduled_time = datetime.datetime.now(dateutils.local_tz())
        start_time = datetime.datetime.now(dateutils.local_tz())
        finish_time = start_time + datetime.timedelta(days=1)

        rst1 = repo_sync_task.RepoSyncTask(lambda: None, [rr1])
        rst1.scheduled_time= scheduled_time
        rst1.start_time = start_time
        rst1.finish_time = finish_time
        th1 = TaskHistory(rst1)
        TaskHistory.get_collection().save(th1, safe=True)
        rst2 = repo_sync_task.RepoSyncTask(lambda: None, [rr1])
        rst2.scheduled_time = scheduled_time
        rst2.start_time = start_time
        rst2.finish_time = finish_time
        th2 = TaskHistory(rst2)
        TaskHistory.get_collection().save(th2, safe=True)

        rst3 = repo_sync_task.RepoSyncTask(lambda: None, [rr2])
        rst3.scheduled_time = scheduled_time
        rst3.start_time = start_time
        rst3.finish_time = finish_time
        th3 = TaskHistory(rst3)
        TaskHistory.get_collection().save(th3, safe=True)

    def test_get_histories(self):
        status, body = self.get('/histories/')
        self.assertEquals(200, status)
        self.assertEquals(3, len(body))

    def test_get_repository_histories(self):
        status, body = self.get('/histories/repository/')
        self.assertEquals(200, status)
        self.assertEquals(3, len(body))

    def test_get_repository_sync_histories(self):
        status, body = self.get('/histories/repository/syncs/')
        self.assertEquals(200, status)
        self.assertEquals(3, len(body))

    def test_get_repository_sync_histories_filtered(self):
        status, body = self.get('/histories/repository/syncs/?repoid=rr1')
        self.assertEquals(200, status)
        self.assertEquals(2, len(body))

        status, body = self.get('/histories/repository/syncs/?repoid=rr2')
        self.assertEquals(200, status)
        self.assertEquals(1, len(body))

        status, body = self.get('/histories/repository/syncs/?repoid=rr1&repoid=rr2&_union=repoid')
        self.assertEquals(200, status)
        self.assertEquals(3, len(body))
