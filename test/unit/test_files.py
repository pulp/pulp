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
import os
import sys
import unittest

from pymongo.errors import DuplicateKeyError

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import pulp
from pulp.server import updateinfo
from pulp.server.api.file import FileApi
from pulp.server.api.repo import RepoApi

import testutil

class TestFiles(unittest.TestCase):

    def clean(self):
        self.rapi.clean()
        self.fapi.clean()

    def setUp(self):
        self.config = testutil.load_test_config()
        self.data_path = \
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
        self.fapi = FileApi()
        self.rapi = RepoApi()
        self.clean()

    def tearDown(self):
        self.clean()
        testutil.common_cleanup()

    def test_create(self):
        filename = "pulp-test.iso"
        id = 'test_create_errata_id'
        description = 'pulp test iso image'
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        size = "4096"
        sample_file = self.fapi.create(filename, checksum_type, checksum, size, description)
        assert(sample_file is not None)
        self.assertTrue(sample_file["filename"] == filename)
        self.assertTrue(sample_file["description"] == description)
        self.assertTrue(sample_file["checksum"] == {checksum_type : checksum})
        self.assertTrue(sample_file["size"] == size)

    def test_duplicate(self):
        filename = "pulp-test.iso"
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        sample_file = self.fapi.create(filename, checksum_type, checksum, None, None)
        assert(sample_file is not None)
        exception_caught = False
        try:
            sample_file = self.fapi.create(filename, checksum_type, checksum, None, None)
        except DuplicateKeyError:
            exception_caught = True
        self.assertTrue(exception_caught)
        checksum_type = "sha256"
        checksum = "c5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        no_exception = True
        try:
            sample_file = self.fapi.create("pulp-test.iso", checksum_type, checksum, None, None)
        except DuplicateKeyError:
            no_exception = False
        self.assertTrue(no_exception)

    def test_delete(self):
        filename = "pulp-test.iso"
        id = 'test_create_errata_id'
        description = 'pulp test iso image'
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        size = "4096"
        sample_file = self.fapi.create(filename,  checksum_type, checksum, size, description)
        self.assertTrue(sample_file is not None)
        found = self.fapi.file(sample_file['id'])
        self.assertTrue(found is not None)
        self.fapi.delete(found['id'])
        found = self.fapi.file(sample_file['id'])
        self.assertTrue(found is None)

    def test_add_file_to_repo(self):
        filename = "pulp-test.iso"
        id = 'test_create_errata_id'
        description = 'pulp test iso image'
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        size = "4096"
        sample_file = self.fapi.create(filename, checksum_type, checksum, size, description)
        self.assertTrue(sample_file is not None)
        fileid = sample_file['id']
        id = 'file-repo'
        repo = self.rapi.create(id, 'file repo', 'noarch')
        repo = self.rapi.repository(id)
        assert(repo is not None)
        self.rapi.add_file(repo['id'], [fileid])
        repo = self.rapi.repository(repo['id'])
        assert(fileid in repo['files'])
        self.rapi.delete(id=repo['id'])
        repo = self.rapi.repository(repo['id'])
        assert(repo is None)
        
    def test_list_repo_files(self):
        filename = "pulp-test.iso"
        id = 'test_create_errata_id'
        description = 'pulp test iso image'
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        size = "4096"
        sample_file = self.fapi.create(filename, checksum_type, checksum, size, description)
        self.assertTrue(sample_file is not None)
        fileid = sample_file['id']
        id = 'file-repo'
        repo = self.rapi.create(id, 'file repo', 'noarch')
        repo = self.rapi.repository(id)
        assert(repo is not None)
        self.rapi.add_file(repo['id'], [fileid])
        repo = self.rapi.repository(repo['id'])
        assert(fileid in repo['files'])
        found = self.rapi.list_files(repo['id'])
        assert(len(found) > 0)

    def test_remove_file_from_repo(self):
        filename = "pulp-test.iso"
        id = 'test_create_errata_id'
        description = 'pulp test iso image'
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        size = "4096"
        sample_file = self.fapi.create(filename,checksum_type, checksum, size, description)
        self.assertTrue(sample_file is not None)
        fileid = sample_file['id']
        id = 'file-repo'
        repo = self.rapi.create(id, 'file repo', 'noarch')
        repo = self.rapi.repository(id)
        assert(repo is not None)
        self.rapi.add_file(repo['id'], [fileid])
        repo = self.rapi.repository(repo['id'])
        assert(fileid in repo['files'])
        self.rapi.remove_file(repo['id'], [fileid])
        repo = self.rapi.repository(repo['id'])
        assert(fileid not in repo['files'])
        
    def test_find_repos_by_files(self):
        filename = "pulp-test.iso"
        id = 'test_create_errata_id'
        description = 'pulp test iso image'
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        size = "4096"
        sample_file = self.fapi.create(filename, checksum_type, checksum, size, description)
        self.assertTrue(sample_file is not None)
        fileid = sample_file['id']
        id = 'file-repo'
        repo = self.rapi.create(id, 'file repo', 'noarch')
        repo = self.rapi.repository(id)
        assert(repo is not None)
        self.rapi.add_file(repo['id'], [fileid])
        repo = self.rapi.repository(repo['id'])
        assert(fileid in repo['files'])
        found = self.rapi.find_repos_by_files(fileid)
        print "CCCCCCCCC",found
        assert(len(found) > 0)
