#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import sys
import os

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../unit/'
sys.path.insert(0, commondir)

from pulp.client.connection import RepoConnection
from pulp.client.connection import ConsumerConnection
from pulp.client.connection import ConsumerGroupConnection
from pulp.client.connection import ErrataConnection
from pulp.client.connection import PackageConnection
from pulp.client.connection import PackageGroupConnection
from pulp.client.connection import PackageGroupCategoryConnection
from test_api import TestApi
import testutil

class RemoteTestApi(TestApi):
    """
    This class subclasses TestApi and overrides the API handlers to actually
    use the same classes the CLI uses.  This ensures we are using the API exactly
    like we are when we call the pulp python API directly.
    
    The overridden testcases in this class indicate tests that *dont* pass yet.
    """

    def setUp(self):
        d = dict(host='localhost',
                 port=443,
                 username="admin",
                 password="admin")
        self.config = testutil.load_test_config()
        self.eapi = ErrataConnection(**d)
        self.rapi = RepoConnection(**d)
        self.capi = ConsumerConnection(**d)
        self.papi = PackageConnection(**d)
        self.cgapi = ConsumerGroupConnection(**d)
        self.pgapi = PackageGroupConnection(**d)
        self.pgcapi = PackageGroupCategoryConnection(**d)

    def tearDown(self):
        testutil.common_cleanup()

    def test_sync_two_repos_share_common_package(self):
        pass

    def test_sync(self):
        pass

    def test_local_sync(self):
        pass

    def test_packages(self):
        pass

    def test_package_groups(self):
        pass

    def test_package_group_categories(self):
        pass

    def test_consumerwithpackage(self):
        pass

    def test_sync_feedless(self):
        pass

    # Package group syncing is currently disabled,
    # it will be fixed later portion of Sprint 14
    # after that change below two package group
    # tests should be enabled
    def test_repo_package_groups(self):
        pass

    def test_repo_package_group_categories(self):
        pass

    # Errata API work is on-going, below errata
    # tests should be skipped through WS until
    # WS work is completed, planned completion is end
    # of sprint 14
    def test_repo_erratum(self):
        pass

    def test_repo_errata(self):
        pass


