#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
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

import sys
import os

cdir = os.path.dirname(__file__)
sys.path.append(os.path.join(cdir, '../../client/src'))
sys.path.append(os.path.join(cdir, '../unit'))

from connection import RepoConnection as RepoApi
from connection import ConsumerConnection as ConsumerApi
from connection import PackageConnection as PackageApi
from connection import PackageVersionConnection as PackageVersionApi
from connection import PackageGroupConnection as PackageGroupApi
from connection import PackageGroupCategoryConnection as PackageGroupCategoryApi

from test_api import TestApi

class RemoteTestApi(TestApi):

    def setUp(self):
        d = dict(host='localhost', port=8811)
        self.rapi = RepoApi(**d)
        self.capi = ConsumerApi(**d)
        self.papi = PackageApi(**d)
        self.pvapi = PackageVersionApi(**d)
        self.pgapi = PackageGroupApi(**d)
        self.pgcapi = PackageGroupCategoryApi(**d)

    def test_consumerwithpackage(self):
        pass

    def test_json(self):
        pass

    def test_sync_two_repos_share_common_package(self):
        pass

    def test_sync_two_repos_share_common_package(self):
        pass

    def test_sync(self):
        pass

    def test_local_sync(self):
        pass

    def test_package_versions(self):
        pass

    def test_packages(self):
        pass

    def test_package_groups(self):
        pass

    def test_package_group_categories(self):
        pass
