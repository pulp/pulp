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

import mock

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.api import repo
from pulp.server.api import repo_sync
from pulp.server.tasking import task
from pulp.server.webservices.controllers import statuses

class BaseStatusesTest(testutil.PulpWebserviceTest):

    def setUp(self):
        testutil.PulpWebserviceTest.setUp(self)
        self.setup_repo_statuses()

    def setup_repo_statuses(self):
        # A repo with a running sync
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        r = self.repo_api.create('rr1',
                'test_name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(r != None)
        rr1 = r["id"]

        # Another repo with a running sync
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        r = self.repo_api.create('rr2',
                'test_name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(r != None)
        rr2 = r["id"]

        # A repo with no running sync
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        r = self.repo_api.create('nrr1',
                'test_name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(r != None)
        nrr1 = r["id"]

        # A repo with an errored sync
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        r = self.repo_api.create('er1',
                'test_name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(r != None)
        er1 = r["id"]

        running_task1 = task.Task(repo_sync._sync, [rr1])
        running_task1.state = task.task_running
        running_task2 = task.Task(repo_sync._sync, [rr2])
        running_task2.state = task.task_running
        error_task1 = task.Task(repo_sync._sync, [er1])
        error_task1.state = task.task_error

        mock_find_async = mock.Mock(return_value=[running_task1,
            running_task2, error_task1])
        self.mock(repo, "find_async", mock_find_async)
        self.mock(statuses, "find_async", mock_find_async)
        
class StatusesTest(BaseStatusesTest):

    def test_get_statuses(self):
        status, body = self.get('/statuses/')
        self.assertEquals(200, status)
        self.assertEquals(3, len(body))
        rt = [t for t in body if t["state"] == task.task_running]
        self.assertEquals(2, len(rt))
        et = [t for t in body if t["state"] == task.task_error]
        self.assertEquals(1, len(et))

    def test_get_repository_statuses(self):
        status, body = self.get('/statuses/repository/')
        self.assertEquals(200, status)
        self.assertEquals(3, len(body))
        rt = [t for t in body if t["state"] == task.task_running]
        self.assertEquals(2, len(rt))
        et = [t for t in body if t["state"] == task.task_error]
        self.assertEquals(1, len(et))

    def test_get_sync_statuses(self):
        status, body = self.get('/statuses/repository/syncs/')
        self.assertEquals(200, status)
        self.assertEquals(3, len(body))
        rt = [t for t in body if t["state"] == task.task_running]
        self.assertEquals(2, len(rt))
        et = [t for t in body if t["state"] == task.task_error]
        self.assertEquals(1, len(et))

    def test_get_filtered_sync_statuses(self):
        status, body = self.get('/statuses/repository/syncs/?repoid=rr1')
        self.assertEquals(200, status)
        self.assertEquals(1, len(body))
        self.assertEquals("rr1", body[0]["repoid"])

        status, body = self.get(
            '/statuses/repository/syncs/?repoid=rr1&repoid=rr2&_union=repoid')
        self.assertEquals(200, status)
        self.assertEquals(2, len(body))
        repo_ids = [r["repoid"] for r in body]
        repo_ids.sort()
        self.assertEquals(["rr1", "rr2"], repo_ids)

        status, body = self.get(
            '/statuses/repository/syncs/?state=running')
        self.assertEquals(200, status)
        self.assertEquals(2, len(body))
        repo_ids = [r["repoid"] for r in body]
        repo_ids.sort()
        self.assertEquals(["rr1", "rr2"], repo_ids)

        status, body = self.get(
            '/statuses/repository/syncs/?state=running&repoid=rr1')
        self.assertEquals(200, status)
        self.assertEquals(1, len(body))
        self.assertEquals("rr1", body[0]["repoid"])
