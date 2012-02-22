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
import urlparse

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.api.discovery import get_discovery
from pulp.server.api.repo import RepoApi

logging.root.setLevel(logging.ERROR)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

class TestRepoDiscoveryApi(testutil.PulpAsyncTest):

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
        repourls = d.discover(discover_url)
        self.assertTrue(len(repourls) != 0)

    def test_invalid_url(self):
        discover_url = 'proto://repos.fedorapeople.org/repos/pulp/pulp/fakedir/'
        d = get_discovery("yum")
        failed = False
        try:
            d.validate_url(discover_url)
        except:
            failed = True
        assert(failed)

    def test_url_without_trailing_slash(self):
        discover_url = 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos'
        d = get_discovery("yum")
        repourls = d.discover(discover_url)
        self.assertTrue(len(repourls) != 0)

    def test_repo_discovery_group(self):
        discover_url = 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/'
        groupid = 'testrepos'
        d = get_discovery("yum")
        repourls = d.discover(discover_url)
        self.assertTrue(len(repourls) != 0)
        repourl = repourls[0]
        repo = self.repo_api.create('discover_test_repo', 'discovery_test_repo', 'noarch', feed='%s' % repourl, groupid=[groupid])
        r = self.repo_api.repository(repo['id'])
        assert(r is not None)
        assert(r['groupid'] == [groupid])
        self.repo_api.delete('discover_test_repo')
        r = self.repo_api.repository('discover_test_repo')
        assert(r is None)

    def test_local_discovery(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir = my_dir + "/data/repo_for_export/"
        discover_url = 'file://%s' % datadir
        d = get_discovery("yum")
        repourls = d.discover(discover_url)
        print repourls
        self.assertTrue(len(repourls) != 0)
        proto, netloc, path, params, query, frag = urlparse.urlparse(repourls[0])
        assert os.path.exists(path)
        assert os.path.exists("%s/%s" % (path, "repodata/repomd.xml"))


  
