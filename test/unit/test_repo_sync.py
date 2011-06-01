
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
import logging
import stat
import sys
import os
import time
import unittest
import shutil

try:
    import json
except ImportError:
    import simplejson as json

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import mocks
from pulp.repo_auth.repo_cert_utils import RepoCertUtils
from pulp.repo_auth.protected_repo_utils import ProtectedRepoUtils
from pulp.server import async
from pulp.server.api import repo_sync
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.tasking import task
from pulp.server.auth.cert_generator import SerialNumber
from pulp.server import constants
import testutil

logging.root.setLevel(logging.ERROR)
CERTS_DIR = '/tmp/test_repo_api/repos'

class TestRepoSync(unittest.TestCase):

    def clean(self):
        self.rapi.clean()
        self.papi.clean()
        if os.path.exists(CERTS_DIR):
            shutil.rmtree(CERTS_DIR)
        protected_repo_listings_file = self.config.get('repos', 'protected_repo_listing_file')
        if os.path.exists(protected_repo_listings_file):
            os.remove(protected_repo_listings_file)
        testutil.common_cleanup()
        shutil.rmtree(constants.LOCAL_STORAGE, ignore_errors=True)
        sn = SerialNumber()
        sn.reset()

    def setUp(self):
        mocks.install()
        self.config = testutil.load_test_config()
        self.config.set('repos', 'cert_location', CERTS_DIR)
        self.data_path = \
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
        self.rapi = RepoApi()
        self.papi = PackageApi()
        self.repo_cert_utils = RepoCertUtils(self.config)
        self.protected_repo_utils = ProtectedRepoUtils(self.config)
        async.initialize()
        self.clean()

    def tearDown(self):
        self.clean()

    def test_sync_multiple_repos(self):
        feeds = {"f14_x86_64": ("http://repos.fedorapeople.org/repos/pulp/pulp/testing/fedora-14/x86_64/", "x86_64"),
            "f14_i386": ("http://repos.fedorapeople.org/repos/pulp/pulp/testing/fedora-14/i386/", "i386"),
            "el5_i386": ("http://repos.fedorapeople.org/repos/pulp/pulp/testing/5Server/i386/", "i386"),
            "el5_x86_64": ("http://repos.fedorapeople.org/repos/pulp/pulp/testing/5Server/x86_64/", "x86_64"),
            "el6_i386": ("http://repos.fedorapeople.org/repos/pulp/pulp/testing/6Server/i386/", "i386"),
            "el6_x86_64": ("http://repos.fedorapeople.org/repos/pulp/pulp/testing/6Server/x86_64/", "x86_64")}

        repos = [self.rapi.create(key, key, value[1], value[0]) for key, value in feeds.items()]
        for r in repos:
            self.assertTrue(r)
        sync_tasks = [repo_sync.sync(r["id"]) for r in repos]
        # Poll tasks and wait for sync to finish
        waiting_tasks = [t.id for t in sync_tasks]
        while len(waiting_tasks) > 0:
            time.sleep(1)
            for t_id in waiting_tasks:
                found_tasks = async.find_async(id=t_id)
                self.assertEquals(len(found_tasks), 1)
                updated_task = found_tasks[0]
                if updated_task.state in task.task_complete_states:
                    self.assertEquals(updated_task.state, task.task_finished)
                    waiting_tasks.remove(t_id)
                    #print "Task <%s> result = <%s>, exception = <%s>, traceback = <%s>, progress = <%s>" % \
                    #      (t_id, updated_task.result, updated_task.exception, updated_task.traceback, updated_task.progress)
        # Refresh repo objects and verify packages were synced.
        for r in repos:
            synced_repo = self.rapi.repository(r["id"])
            self.assertTrue(synced_repo)
            self.assertTrue(len(synced_repo["packages"]) > 0)

    def test_yum_sync_with_exception(self):
        # We need report to be accessible for writing by the callback
        global report
        report = None
        def callback(r):
            global report
            report = r

        repo = self.rapi.create('some-id', 'some name', 'i386',
                                'http://jmatthews.fedorapeople.org/repo_with_bad_read_perms/')
        repo_sync._sync(repo['id'], progress_callback=callback)
        found = self.rapi.repository(repo['id'])
        packages = found['packages']
        self.assertTrue(packages is not None)
        self.assertEquals(len(packages),0)
        self.assertEquals(report["items_total"], 3)
        self.assertEquals(report["num_success"], 0)
        self.assertEquals(report["num_error"], 3)
        error_details = report["error_details"]
        self.assertTrue(error_details is not None)
        self.assertTrue(len(error_details) == 3)
        keys = ("checksumtype", "checksum", "downloadurl", "item_type",
                        "savepath", "pkgpath", "size")
        for error_entry in error_details:
            for key in keys:
                self.assertNotEquals(error_entry[key], "")
                self.assertTrue(error_entry.has_key("error_type"))
                self.assertTrue(error_entry.has_key("traceback"))
        for e in error_details:
            self.assertTrue(e["fileName"] in ("pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm",
                "pulp-test-package-0.2.1-1.fc11.x86_64.rpm",
                "pulp-test-package-0.3.1-1.fc11.x86_64.rpm"))
            self.assertTrue("HTTP status code of 403" in e["error"])
        
    def test_local_sync_with_exception(self):
        #This test will only run correctly as a non-root user
        if os.getuid() == 0:
            return

        # We need report to be accessible for writing by the callback
        global report
        report = None
        def callback(r):
            global report
            report = r
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir = my_dir + "/data/repo_with_bad_read_perms/"
        bad_rpm_path = os.path.join(datadir, "pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm")
        bad_tree_path = os.path.join(datadir, "images/file3.img")
        bad_rpm_mode = stat.S_IMODE(os.stat(bad_rpm_path).st_mode)
        bad_tree_mode = stat.S_IMODE(os.stat(bad_tree_path).st_mode)
        # We will disable read access to 2 items to simulate an IOError
        os.chmod(bad_rpm_path, 0)
        os.chmod(bad_tree_path, 0)
        try:
            self.assertFalse(os.access(bad_rpm_path, os.R_OK))
            self.assertFalse(os.access(bad_tree_path, os.R_OK))
            repo = self.rapi.create('some-id', 'some name', 'i386',
                                'file://%s' % datadir)
            repo_sync._sync(repo['id'], progress_callback=callback)
            found = self.rapi.repository(repo['id'])
            packages = found['packages']
            self.assertTrue(packages is not None)
            self.assertTrue(len(packages) == 2)
            self.assertTrue(report["items_total"] - report["num_success"] == 2)
            self.assertTrue(report["num_error"] == 2)
            error_details = report["error_details"]
            self.assertTrue(error_details is not None)
            self.assertTrue(len(error_details) == 2)
            # We are checking that the local sync error contains the same fields
            # as what is in a yum sync, these fields are expected to be entry
            empty_keys = ("checksumtype", "checksum", "downloadurl", "item_type",
                          "savepath", "pkgpath", "size")
            for error_entry in error_details:
                for key in empty_keys:
                    self.assertEquals(error_entry[key], "")
                    self.assertTrue(error_entry.has_key("error_type"))
                    self.assertTrue(error_entry.has_key("traceback"))

            self.assertTrue("pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm" in error_details[0]["fileName"])
            self.assertTrue("Permission denied" in error_details[0]["error"])
            self.assertTrue("file3.img" in error_details[1]["fileName"])
            self.assertTrue("Permission denied" in error_details[1]["error"])
        finally:
            os.chmod(bad_rpm_path, bad_rpm_mode)
            os.chmod(bad_tree_path, bad_tree_mode)
