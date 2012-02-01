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
import random
import logging
import sys
import os
import time
import unittest
import uuid

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.api import repo_sync

class TestRepoFilters(testutil.PulpAsyncTest):

    def test_create(self, id = 'filter-test'):
        filter = self.filter_api.create(id, type="blacklist", description="test filter",
                                package_list=['NOTemacs'])
        self.assertTrue(filter is not None)
        filter = self.filter_api.filter(id)
        self.assertTrue(filter is not None)
        self.assertEquals(filter['description'], 'test filter')

    def test_duplicate(self, id = 'dupe-test'):
        filter = self.filter_api.create(id=id, type="whitelist")
        try:
            filter = self.filter_api.create(id=id, type="whitelist")
            raise Exception, 'Duplicate allowed'
        except:
            pass

    def test_filter_list(self, id = 'filter-test' ):
        filter = self.filter_api.create(id, type="blacklist")
        filters = self.filter_api.filters()
        assert(len(filters) == 1)

    def test_clean(self, id = 'filter-test'):
        filter = self.filter_api.create(id, type="blacklist")
        self.filter_api.clean()
        filters = self.filter_api.filters()
        assert(len(filters) == 0)
 
    def test_delete(self, id = 'filter-test'):
        self.filter_api.create(id, type="blacklist")
        self.filter_api.delete(id)
        filter = self.filter_api.filter(id)
        assert(filter is None)

    def test_add_filters_to_repo(self, id = "filter-test1"):
        repoid = 'clone-some-id'
        parent_repo = self.repo_api.create('some-id', 'some name', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/fedora-15/x86_64/')
        self.assertTrue(parent_repo is not None)
        repo_sync._sync(repo_id='some-id')
        repo_sync.clone('some-id', repoid, repoid)
        filter_ids = [id, "filter-test2"]
        # Try without creating filters
        try:
            self.repo_api.add_filters(repoid, filter_ids)
            self.assertTrue(False)
        except Exception:
            self.assertTrue(True)

        # After creating filters
        self.filter_api.create(id, type="blacklist")
        self.filter_api.create('filter-test2', type="whitelist")
        try:
            self.repo_api.add_filters(repoid, filter_ids)
        except Exception:
            self.assertTrue(False)

    def test_remove_filters_from_repo(self, id = "filter-test1"):
        repoid = 'clone-some-id'
        parent_repo = self.repo_api.create('some-id', 'some name', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/fedora-15/x86_64/')
        self.assertTrue(parent_repo is not None)
        repo_sync._sync(repo_id='some-id')
        repo_sync.clone('some-id', repoid, repoid)
        self.filter_api.create(id, type="blacklist")
        self.filter_api.create('filter-test2', type="whitelist")
        filter_ids = [id, "filter-test2"]
        try:
            self.repo_api.add_filters(repoid, filter_ids)
        except Exception:
            self.assertTrue(False)
        # Remove added filters
        try:
            self.repo_api.remove_filters(repoid, filter_ids)
        except Exception:
            self.assertTrue(False)

    def test_list_repo_filters(self, id = "filter-test1"):
        repoid = 'clone-some-id'
        parent_repo = self.repo_api.create('some-id', 'some name', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/fedora-15/x86_64/')
        self.assertTrue(parent_repo is not None)
        repo_sync._sync(repo_id='some-id')
        repo_sync.clone('some-id', repoid, repoid)
        filters = self.repo_api.list_filters(repoid)
        self.assertTrue(len(filters) == 0)

        self.filter_api.create(id, type="blacklist")
        self.filter_api.create('filter-test2', type="whitelist")
        filter_ids = [id, "filter-test2"]
        self.repo_api.add_filters(repoid, filter_ids)
        filters = self.repo_api.list_filters(repoid)
        self.assertTrue(len(filters) == 2)
        
    def test_nonexistent_filter_delete(self, id = "non-existent-filter"):
        try:
            self.filter_api.delete(id)
            self.assertTrue(False)
        except:
            pass
        
    def test_repo_associated_filter_delete(self, id = 'filter-test1'):
        repo = self.repo_api.create('some-id', 'some name', 'i386',
                                'file://test')
        self.assertTrue(repo is not None)
        self.filter_api.create(id, type="blacklist")
        self.repo_api.add_filters('some-id', [id])

        self.filter_api.delete(id)
        filters = self.repo_api.list_filters('some-id')
        self.assertTrue(len(filters) == 0)
        
    def test_add_packages_to_filter(self, id = 'filter-test'):
        filter = self.filter_api.create(id, type="blacklist", description="test filter",
                                package_list=['abc'])
        self.assertTrue(filter is not None)
        added_packages = ["^python","xyz*"]
        self.filter_api.add_packages(id=id, packages=added_packages)
        filter = self.filter_api.filter(id)
        self.assertTrue("^python" in filter['package_list'])
        self.assertTrue("xyz*" in filter['package_list'])

    def test_remove_packages_from_filter(self, id = 'filter-test'):
        filter = self.filter_api.create(id, type="blacklist", description="test filter",
                                package_list=['abc',"^python","xyz*"])
        self.assertTrue(filter is not None)
        removed_packages = ["^python","xyz*"]
        self.filter_api.remove_packages(id=id, packages=removed_packages)
        filter = self.filter_api.filter(id)
        self.assertTrue("^python" not in filter['package_list'])
        self.assertTrue("xyz*" not in filter['package_list'])
        
    def test_add_remove_filters(self, id = 'filter-test1'):
        filter = self.filter_api.create(id, type="blacklist", description="test filter",
                                        package_list=['abc',"^python","xyz*"])
        self.filter_api.create('filter-test2', type="whitelist")
        filter_ids = [id, "filter-test2"]
        yum_repo = self.repo_api.create('some-id', 'some name', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/fedora-15/x86_64/')
        try:
            self.repo_api.add_filters('some-id', filter_ids)
            self.assertTrue(False)
        except:
            pass
        
        local_repo = self.repo_api.create('some-id1', 'some name1', 'i386',
                                      'file://test')
        self.repo_api.add_filters('some-id1', filter_ids)
        filters = self.repo_api.list_filters('some-id1')
        self.assertTrue(len(filters) == 2)
        
        self.repo_api.remove_filters('some-id1', filter_ids)
        filters = self.repo_api.list_filters('some-id1')
        self.assertTrue(len(filters) == 0)
        
    def test_filters_with_i18n_id(self):
        def get_random_unicode():
            return unichr(random.choice((0x300, 0x2000)) + random.randint(0, 0xff))
        self.test_clean(get_random_unicode())
        self.clean()
        self.test_create(get_random_unicode())
        self.clean()
        self.test_delete(get_random_unicode())
        self.clean()
        self.test_duplicate(get_random_unicode())
        self.clean()
        self.test_filter_list(get_random_unicode())
        self.clean()
        self.test_add_filters_to_repo(get_random_unicode())
        self.clean()
        self.test_add_packages_to_filter(get_random_unicode())
        self.clean()
        self.test_add_remove_filters(get_random_unicode())
        self.clean()
        self.test_list_repo_filters(get_random_unicode())
        self.clean()
        self.test_nonexistent_filter_delete(get_random_unicode())
        self.clean()
        self.test_remove_filters_from_repo(get_random_unicode())
        self.clean()
        self.test_remove_packages_from_filter(get_random_unicode())
        self.clean()
        self.test_repo_associated_filter_delete(get_random_unicode())

if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.ERROR)
    unittest.main()
