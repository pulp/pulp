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
from pulp.server.util import top_repos_location, get_repomd_filetype_path
from pulp.server.api.repo import RepoApi
import testutil

logging.root.setLevel(logging.ERROR)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

class TestRepoMetadataApi(unittest.TestCase):

    def setUp(self):
        testutil.load_test_config()
        self.rapi = RepoApi()
        self.data_path = \
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")

    def tearDown(self):
        self.rapi.clean()

    def test_repo_metadata_add(self):
        repo = self.rapi.create('test-custom-id', 'custom name', 'noarch')
        custom_metadata_file = "%s/%s" % (self.data_path, "product")
        custom_data = open(custom_metadata_file, 'r').read()
        metadata_dict = {'filetype' : 'product',
                         'filedata' : custom_data}
        self.rapi.add_metadata(repo['id'], metadata_dict)
        repodata_file = "%s/%s/%s/%s" % (top_repos_location(),
                                         repo['relative_path'],
                                         'repodata', 'repomd.xml')
        product_file_path = get_repomd_filetype_path(repodata_file, "product") or None
        print product_file_path
        self.assertTrue(product_file_path is not None)

    def test_repo_metadata_add_preserved(self):
        repo = self.rapi.create('test-custom-id-preserve', 'custom preserve', 'noarch', preserve_metadata=True)
        custom_metadata_file = "%s/%s" % (self.data_path, "product")
        custom_data = open(custom_metadata_file, 'r').read()
        metadata_dict = {'filetype' : 'product',
                         'filedata' : custom_data}
        failure = False
        try:
            self.rapi.add_metadata(repo['id'], metadata_dict)
        except:
            # cannot add custom data to preserved repo
            failure =  True
        self.assertFalse(failure)

    def test_repo_metadata_get(self):
        repo = self.rapi.create('test-get-custom-id', 'custom name', 'noarch')
        custom_metadata_file = "%s/%s" % (self.data_path, "product")
        custom_data = open(custom_metadata_file, 'rb').read()
        metadata_dict = {'filetype' : 'product',
                         'filedata' : custom_data}
        self.rapi.add_metadata(repo['id'], metadata_dict)
        found_custom_xml = self.rapi.get_metadata(repo['id'], filetype='product')
        print "DEBUG: ",found_custom_xml
        self.assertTrue(found_custom_xml is not None)
        not_found_custom_xml = self.rapi.get_metadata(repo['id'], filetype='comps')
        self.assertTrue(not_found_custom_xml is None)

    def test_repo_metadata_list(self):
        repo = self.rapi.create('test-list-custom-id', 'custom name', 'noarch')
        custom_metadata_file = "%s/%s" % (self.data_path, "product")
        custom_data = open(custom_metadata_file, 'rb').read()
        metadata_dict = {'filetype' : 'product',
                         'filedata' : custom_data}
        self.rapi.add_metadata(repo['id'], metadata_dict)
        list_of_metadata_info = self.rapi.list_metadata(repo['id'])
        print list_of_metadata_info
        self.assertTrue(list_of_metadata_info is not None)

    def test_metadata_remove_repo(self):
        pass