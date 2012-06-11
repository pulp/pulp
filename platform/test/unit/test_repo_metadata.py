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

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.util import top_repos_location, get_repomd_filetype_path
from pulp.server.api.repo import RepoApi
import testutil

logging.root.setLevel(logging.ERROR)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

class TestRepoMetadataApi(testutil.PulpAsyncTest):

    def test_repo_metadata_add(self):
        repo = self.repo_api.create('test-custom-id', 'custom name', 'noarch')
        custom_metadata_file = "%s/%s" % (self.data_path, "product")
        custom_data = open(custom_metadata_file, 'r').read()
        metadata_dict = {'filetype' : 'product',
                         'filedata' : custom_data}
        self.repo_api.add_metadata(repo['id'], metadata_dict)
        repodata_file = "%s/%s/%s/%s" % (top_repos_location(),
                                         repo['relative_path'],
                                         'repodata', 'repomd.xml')
        product_file_path = get_repomd_filetype_path(repodata_file, "product") or None
        print product_file_path
        self.assertTrue(product_file_path is not None)

    def test_repo_metadata_add_preserved(self):
        repo = self.repo_api.create('test-custom-id-preserve', 'custom preserve', 'noarch', preserve_metadata=True)
        custom_metadata_file = "%s/%s" % (self.data_path, "product")
        custom_data = open(custom_metadata_file, 'r').read()
        metadata_dict = {'filetype' : 'product',
                         'filedata' : custom_data}
        failure = False
        try:
            self.repo_api.add_metadata(repo['id'], metadata_dict)
        except:
            # cannot add custom data to preserved repo
            failure =  True
        self.assertFalse(failure)

    def test_repo_metadata_get(self):
        repo = self.repo_api.create('test-get-custom-id', 'custom name', 'noarch')
        custom_metadata_file = "%s/%s" % (self.data_path, "product")
        custom_data = open(custom_metadata_file, 'rb').read()
        metadata_dict = {'filetype' : 'product',
                         'filedata' : custom_data}
        self.repo_api.add_metadata(repo['id'], metadata_dict)
        found_custom_xml = self.repo_api.get_metadata(repo['id'], filetype='product')
        print "DEBUG: ",found_custom_xml
        self.assertTrue(found_custom_xml is not None)
        not_found_custom_xml = self.repo_api.get_metadata(repo['id'], filetype='comps')
        self.assertTrue(not_found_custom_xml is None)

    def test_repo_metadata_list(self):
        repo = self.repo_api.create('test-list-custom-id', 'custom name', 'noarch')
        custom_metadata_file = "%s/%s" % (self.data_path, "product")
        custom_data = open(custom_metadata_file, 'rb').read()
        metadata_dict = {'filetype' : 'product',
                         'filedata' : custom_data}
        self.repo_api.add_metadata(repo['id'], metadata_dict)
        list_of_metadata_info = self.repo_api.list_metadata(repo['id'])
        print list_of_metadata_info
        self.assertTrue(list_of_metadata_info is not None)

    def _test_metadata_remove_repo(self):
        # Turn this test off until --remove patch makes it into upstream create repo for el5/6
        repo = self.repo_api.create('test-list-custom-id', 'custom name', 'noarch')
        custom_metadata_file = "%s/%s" % (self.data_path, "product")
        custom_data = open(custom_metadata_file, 'rb').read()
        metadata_dict = {'filetype' : 'product',
                         'filedata' : custom_data}
        self.repo_api.add_metadata(repo['id'], metadata_dict)
        found_custom_xml = self.repo_api.get_metadata(repo['id'], filetype='product')
        self.assertTrue(found_custom_xml is not None)
        self.repo_api.remove_metadata(repo['id'], "product")
        found_custom_xml = self.repo_api.get_metadata(repo['id'], filetype='product')
        print found_custom_xml
        assert(found_custom_xml is None)

    def test_metadata(self):
        repo = self.repo_api.create('some-id', 'some name', \
            'i386', 'http://example.com')
        p1 = testutil.create_package(self.package_api, 'test_pkg_by_name', filename="test01.rpm")
        self.repo_api.add_package(repo["id"], [p1['id']])

        p2 = testutil.create_package(self.package_api, 'test_pkg2_by_name', filename="test02.rpm")
        self.repo_api.add_package(repo["id"], [p2['id']])

        pkgs = self.repo_api.packages(repo['id'])
        self.assertTrue(len(pkgs) == 2)
        self.assertTrue(p1["id"] in pkgs)
        self.assertTrue(p2["id"] in pkgs)
        success = True
        try:
            self.repo_api._generate_metadata(repo['id'])
        except:
            raise
            success = False
        assert(success)

