
  #!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
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


from pulp.repo_auth.repo_cert_utils import RepoCertUtils
from pulp.repo_auth.protected_repo_utils import ProtectedRepoUtils
from pulp.server import async
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
        feeds = {"f14_x86_64": ("yum:http://repos.fedorapeople.org/repos/pulp/pulp/testing/fedora-14/x86_64/", "x86_64"),
            "f14_i386": ("yum:http://repos.fedorapeople.org/repos/pulp/pulp/testing/fedora-14/i386/", "i386"),
            "el5_i386": ("yum:http://repos.fedorapeople.org/repos/pulp/pulp/testing/5Server/i386/", "i386"),
            "el5_x86_64": ("yum:http://repos.fedorapeople.org/repos/pulp/pulp/testing/5Server/x86_64/", "x86_64"),
            "el6_i386": ("yum:http://repos.fedorapeople.org/repos/pulp/pulp/testing/6Server/i386/", "i386"),
            "el6_x86_64": ("yum:http://repos.fedorapeople.org/repos/pulp/pulp/testing/6Server/x86_64/", "x86_64")}

        repos = [self.rapi.create(key, key, value[1], value[0]) for key, value in feeds.items()]
        for r in repos:
            print "Created: <%s> repository" % (r["id"])
            self.assertTrue(r)
        sync_tasks = [self.rapi.sync(r["id"]) for r in repos]
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