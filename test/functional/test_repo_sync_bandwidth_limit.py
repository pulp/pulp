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
import shutil

try:
    import json
except ImportError:
    import simplejson as json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import pymongo.json_util

from pulp.server.api import repo_sync
from pulp.server.api.repo import RepoApi
from pulp.server.db.model import Delta
from pulp.server.db.model import PackageGroup
from pulp.server.db.model import PackageGroupCategory
from pulp.server.db.model import Consumer
from pulp.server.db.model import RepoSource
from pulp.server.util import random_string
from pulp.server.util import get_rpm_information
from pulp.server.util import top_repos_location
from pulp.server import constants
from pulp.server.exceptions import PulpException

logging.root.setLevel(logging.ERROR)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

class TestRepoSyncBandwidthLimit(testutil.PulpAsyncTest):

    def test_config_only(self):
        threads = 2
        limit = 50 # KB/sec
        self.config.set('yum','threads', str(threads))
        self.config.set('yum','limit_in_KB', str(limit))
        repo = self.repo_api.create('some-id', 'some name',
            'i386', 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/test_bandwidth_repo_smaller/')
        repo_size_kb = 200 # Test repo has 2 100kb packages
        # Test repo has 2 packages, so 2 threads is the maximum
        # benefit we can realize
        start = time.time()
        repo_sync._sync(repo['id'])
        end = time.time()
        found = self.repo_api.repository(repo['id'], )
        self.assertEquals(len(found['packages']), 2)
        self.assertTrue(end-start > (float(repo_size_kb)/(limit*threads)))

    def test_override_config(self):
        self.config.set('yum','threads', '20')
        self.config.set('yum','limit_in_KB', '5000')
        repo = self.repo_api.create('some-id', 'some name',
            'i386', 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/test_bandwidth_repo/')
        repo_size_kb = 5000 # Test repo has 2 100kb packages
        threads = 2
        limit = 100 # KB/sec
        start = time.time()
        repo_sync._sync(repo['id'], max_speed=limit, threads=threads)
        end = time.time()
        found = self.repo_api.repository(repo['id'], )
        assumed_time = (float(repo_size_kb)/(limit*threads))
        self.assertEquals(len(found['packages']), 5)
        self.assertTrue(end-start > assumed_time)

    def test_override_config_to_unlimited(self):
        self.config.set('yum','threads', '1')
        self.config.set('yum','limit_in_KB', '1')
        repo = self.repo_api.create('some-id', 'some name',
            'i386', 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/test_bandwidth_repo_smaller/')
        repo_size_kb = 200 # Test repo has 2 100kb packages
        # Test repo has 2 packages, so 2 threads is the maximum
        # benefit we can realize
        threads = 1
        limit = 0 # unlimited
        start = time.time()
        repo_sync._sync(repo['id'], max_speed=limit)
        end = time.time()
        found = self.repo_api.repository(repo['id'], )
        self.assertEquals(len(found['packages']), 2)
        # We initially set a limit of 1 KB/sec in config file and are overriding it
        # Will check that that the sync completed within at least 30 seconds.
        # If the override failed, the sync would not complete for at least 200 seconds.
        self.assertTrue(end-start < 30)
