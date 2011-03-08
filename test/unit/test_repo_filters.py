#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
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
import time
import unittest
import uuid

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.server.api.filter import FilterApi
from pulp.server.api.repo import RepoApi
import testutil


class TestRepoFilters(unittest.TestCase):

    def clean(self):
        self.filter_api.clean()
        self.rapi.clean()

    def setUp(self):
        self.config = testutil.load_test_config()
        self.filter_api = FilterApi()
        self.rapi = RepoApi()
        self.clean()

    def tearDown(self):
        self.clean()
        testutil.common_cleanup()

    def test_create(self):
        filter = self.filter_api.create('filter-test', type="blacklist", description="test filter",
                                package_list=['NOTemacs'])
        self.assertTrue(filter is not None)
        filter = self.filter_api.filter('filter-test')
        self.assertTrue(filter is not None)
        self.assertEquals(filter['description'], 'test filter')

    def test_duplicate(self):
        id = 'dupe-test'
        filter = self.filter_api.create(id=id, type="whitelist")
        try:
            filter = self.filter_api.create(id=id, type="whitelist")
            raise Exception, 'Duplicate allowed'
        except:
            pass

    def test_filter_list(self):
        filter = self.filter_api.create('filter-test', type="blacklist")
        filters = self.filter_api.filters()
        assert(len(filters) == 1)

    def test_clean(self):
        filter = self.filter_api.create('filter-test', type="blacklist")
        self.filter_api.clean()
        filters = self.filter_api.filters()
        assert(len(filters) == 0)
 
    def test_delete(self):
        self.filter_api.create('filter-test', type="blacklist")
        self.filter_api.delete('filter-test')
        filter = self.filter_api.filter('filter-test')
        assert(filter is None)

    def test_add_filters_to_repo(self):
        repoid = 'clone-some-id'
        parent_repo = self.rapi.create('some-id', 'some name', 'i386',
                                'yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64/')
        self.assertTrue(parent_repo is not None)
        self.rapi._sync(id='some-id')
        self.rapi._clone('some-id', repoid, repoid)
        filter_ids = ["filter-test1", "filter-test2"]
        # Try without creating filters
        try:
            self.rapi.add_filters(repoid, filter_ids)
            self.assertTrue(False)
        except Exception:
            self.assertTrue(True)

        # After creating filters
        self.filter_api.create('filter-test1', type="blacklist")
        self.filter_api.create('filter-test2', type="whitelist")
        try:
            self.rapi.add_filters(repoid, filter_ids)
        except Exception:
            self.assertTrue(False)

    def test_remove_filters_from_repo(self):
        repoid = 'clone-some-id'
        parent_repo = self.rapi.create('some-id', 'some name', 'i386',
                                'yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64/')
        self.assertTrue(parent_repo is not None)
        self.rapi._sync(id='some-id')
        self.rapi._clone('some-id', repoid, repoid)
        self.filter_api.create('filter-test1', type="blacklist")
        self.filter_api.create('filter-test2', type="whitelist")
        filter_ids = ["filter-test1", "filter-test2"]
        try:
            self.rapi.add_filters(repoid, filter_ids)
        except Exception:
            self.assertTrue(False)
        # Remove added filters
        try:
            self.rapi.remove_filters(repoid, filter_ids)
        except Exception:
            self.assertTrue(False)

    def test_list_repo_filters(self):
        repoid = 'clone-some-id'
        parent_repo = self.rapi.create('some-id', 'some name', 'i386',
                                'yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64/')
        self.assertTrue(parent_repo is not None)
        self.rapi._sync(id='some-id')
        self.rapi._clone('some-id', repoid, repoid)
        filters = self.rapi.list_filters(repoid)
        self.assertTrue(len(filters) == 0)

        self.filter_api.create('filter-test1', type="blacklist")
        self.filter_api.create('filter-test2', type="whitelist")
        filter_ids = ["filter-test1", "filter-test2"]
        self.rapi.add_filters(repoid, filter_ids)
        filters = self.rapi.list_filters(repoid)
        self.assertTrue(len(filters) == 2)

if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.ERROR)
    unittest.main()
