# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
import shutil
import sys
import logging
from pulp.server.exceptions import PulpException
from pulp.server.tasking.exception import ConflictingOperationException

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

logging.root.setLevel(logging.ERROR)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)
from pulp.server.api import exporter, repo_sync
from pulp.server import async, constants, util

class TestExporterApi(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.testpath = "/tmp/pulp/my_new_export/"
        if not os.path.exists(self.testpath):
            os.mkdir(self.testpath)

    def tearDown(self):
        testutil.PulpAsyncTest.tearDown(self)
        shutil.rmtree(self.testpath)

    def test_validate_target_path(self):
        testpath = "/tmp/pulp/my_new_export/"
        success = True
        try:
            exporter.validate_target_path(testpath)
        except:
            success = False
        assert success
        assert(os.path.exists(testpath))
        temp_file = "%s/%s" % (testpath, 'temp')
        open(temp_file, 'a').close()
        success = False
        try:
            exporter.validate_target_path(testpath)
        except:
            # should raise an exception
            success = True
        assert success
        # with overwrite
        try:
            exporter.validate_target_path(testpath, overwrite=True)
        except:
            # should raise an exception
            success = False
        assert success
        #target path is None
        success = False
        try:
            exporter.validate_target_path(None, overwrite=True)
        except PulpException:
            success = True
        assert success

        exporter.validate_target_path("/tmp/pulp/my_new_export/foo/", overwrite=True)
        assert os.path.exists("/tmp/pulp/my_new_export/foo/")

    def test_export_invalid_repo(self):
        success = False
        try:
            exporter.export('invalid-repo-id', target_directory='/tmp/pulp/my_new_export', overwrite=True)
        except PulpException,pe:
            print pe
            # should raise invalid repo id
            success = True
        assert success

    def test_export_valid(self):
        repoobj = self.repo_api.create("testrepoid1", "testrepoid", "x86_64",
            "http://www.example.com")
        assert(repoobj is not None)
        # export a repo
        task = exporter.export(repoobj["id"], target_directory='/tmp/pulp/my_new_export', overwrite=True)
        assert(task is not None)

    def test_multiple_exports(self):
        repoobj = self.repo_api.create("testrepoid", "testrepoid", "x86_64",
            "http://www.example.com")
        assert(repoobj is not None)
        # export a repo
        task1 = exporter.export(repoobj["id"], target_directory='/tmp/pulp/my_new_export', overwrite=True)
        assert(task1 is not None)
        # should return None and not create a task
        task2 = exporter.export(repoobj["id"], target_directory='/tmp/pulp/my_new_export', overwrite=True)
        assert(task2 is None)

    def _test_repo_sync_export(self):
        # this seems to hit a lock error invoking sync
        # need to revisit
        repoobj = self.repo_api.create("testrepoid2", "testrepoid", "x86_64",
            "http://www.example.com")
        assert(repoobj is not None)
        repo_sync._sync(repoobj['id'])
        success = False
        try:
            task1 = exporter.export(repoobj["id"], target_directory='/tmp/pulp/my_new_export', overwrite=True)
        except ConflictingOperationException:
            success = True
        assert success

    def test_export_list(self):
        repoobj = self.repo_api.create("testrepoid3", "testrepoid", "x86_64",
            "http://www.example.com")
        assert(repoobj is not None)
        # export a repo
        task = exporter.export(repoobj["id"], target_directory='/tmp/pulp/my_new_export', overwrite=True)
        assert(task is not None)
        print task
        #found_tasks = exporter.list_exports("testrepoid")
        found_tasks = async.find_async(id=task.id)
        print found_tasks
        self.assertEquals(len(found_tasks), 1)

