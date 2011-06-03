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
import sys
import os
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.server.api.discovery import get_discovery
from pulp.server.api.repo import RepoApi
import testutil

logging.root.setLevel(logging.ERROR)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

class TestRepoDiscoveryApi(unittest.TestCase):

    def setUp(self):
        self.rapi = RepoApi()

    def tearDown(self):
        self.rapi.clean()

    def test_get_discovery(self):
        d = get_discovery("yum")
        assert(d is not None)
        failed = False
        try:
            get_discovery("fake")
        except:
            failed = True
        assert(failed)

    def test_discovery(self):
        discover_url = 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/'
        d = get_discovery("yum")
        d.setup(discover_url)
        repourls = d.discover()
        self.assertTrue(len(repourls) != 0)

    def test_invalid_url(self):
        discover_url = 'proto://repos.fedorapeople.org/repos/pulp/pulp/fakedir/'
        d = get_discovery("yum")
        failed = False
        try:
            d.setup(discover_url)
        except:
            failed = True
        assert(failed)

    def test_repo_discovery_group(self):
        discover_url = 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/'
        groupid = 'testrepos'
        d = get_discovery("yum")
        d.setup(discover_url)
        repourls = d.discover()
        self.assertTrue(len(repourls) != 0)
        repourl = repourls[0]
        repo = self.rapi.create('discover_test_repo', 'discovery_test_repo', 'noarch', feed='%s' % repourl, groupid=[groupid])
        r = self.rapi.repository(repo['id'])
        assert(r is not None)
        assert(r['groupid'] == [groupid])
        self.rapi.delete('discover_test_repo')
        r = self.rapi.repository('discover_test_repo')
        assert(r is None)


  