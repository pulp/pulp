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
        d.setUrl(discover_url)
        repourls = d.discover()
        self.assertTrue(len(repourls) != 0)

    def test_invalid_url(self):
        discover_url = 'http://repos.fedorapeople.org/repos/pulp/pulp/fakedir/'
        d = get_discovery("yum")
        failed = False
        try:
            d.setUrl(discover_url)
        except:
            failed = True
        assert(failed)

    def test_repo_discovery_group(self):
        discover_url = 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/'
        groupid = 'testrepos'
        d = get_discovery("yum")
        d.setUrl(discover_url)
        repourls = d.discover()
        self.assertTrue(len(repourls) != 0)
        repourl = repourls[0]
        repo = self.rapi.create('discover_test_repo', 'discovery_test_repo', 'noarch', feed='yum:%s' % repourl, groupid=[groupid])
        r = self.rapi.repository(repo['id'])
        assert(r is not None)
        assert(r['groupid'] == [groupid])
        self.rapi.delete('discover_test_repo')
        r = self.rapi.repository('discover_test_repo')
        assert(r is None)


  