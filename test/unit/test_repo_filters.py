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
import testutil


class TestRepoFilters(unittest.TestCase):

    def clean(self):
        self.filter_api.clean()

    def setUp(self):
        self.config = testutil.load_test_config()
        self.filter_api = FilterApi()
        self.clean()

    def tearDown(self):
        self.clean()
        testutil.common_cleanup()

    def test_create(self):
        filter = self.filter_api.create('filter-test', type="blacklist", description="test filter",
                                package_list=['emacs'])
        self.assertTrue(filter is not None)
        filter = self.filter_api.filter('filter-test')
        self.assertTrue(filter is not None)

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
 

if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.ERROR)
    unittest.main()
