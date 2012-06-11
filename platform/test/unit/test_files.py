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
import os
import sys

from pymongo.errors import DuplicateKeyError

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import pulp
from pulp.server import updateinfo
from pulp.server.api.file import FileApi, FileHasReferences
from pulp.server.api.repo import RepoApi

class TestFiles(testutil.PulpAsyncTest):

    def test_create(self):
        filename = "pulp-test.iso"
        id = 'test_create_errata_id'
        description = 'pulp test iso image'
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        size = "4096"
        sample_file = self.file_api.create(filename, checksum_type, checksum, size, description)
        assert(sample_file is not None)
        self.assertTrue(sample_file["filename"] == filename)
        self.assertTrue(sample_file["description"] == description)
        self.assertTrue(sample_file["checksum"] == {checksum_type : checksum})
        self.assertTrue(sample_file["size"] == int(size))

    def test_duplicate(self):
        filename = "pulp-test.iso"
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        sample_file_1 = self.file_api.create(filename, checksum_type, checksum, None, None)
        assert(sample_file_1 is not None)
        sample_file_2 = self.file_api.create(filename, checksum_type, checksum, None, None)
        assert(sample_file_2 is not None)
        self.assertTrue(sample_file_1['id'] == sample_file_2["id"])

    def test_delete(self):
        filename = "pulp-test.iso"
        id = 'test_create_errata_id'
        description = 'pulp test iso image'
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        size = "4096"
        sample_file = self.file_api.create(filename,  checksum_type, checksum, size, description)
        self.assertTrue(sample_file is not None)
        found = self.file_api.file(sample_file['id'])
        self.assertTrue(found is not None)
        self.file_api.delete(found['id'])
        found = self.file_api.file(sample_file['id'])
        self.assertTrue(found is None)

    def test_add_file_to_repo(self):
        filename = "pulp-test.iso"
        id = 'test_create_errata_id'
        description = 'pulp test iso image'
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        size = "4096"
        sample_file = self.file_api.create(filename, checksum_type, checksum, size, description)
        self.assertTrue(sample_file is not None)
        fileid = sample_file['id']
        id = 'file-repo'
        repo = self.repo_api.create(id, 'file repo', 'noarch')
        repo = self.repo_api.repository(id)
        assert(repo is not None)
        self.repo_api.add_file(repo['id'], [fileid])
        repo = self.repo_api.repository(repo['id'])
        assert(fileid in repo['files'])
        self.repo_api.delete(id=repo['id'])
        repo = self.repo_api.repository(repo['id'])
        assert(repo is None)

    def test_file_delete_with_references(self):
        filename = "pulp-test.iso"
        id = 'test_create_errata_id'
        description = 'pulp test iso image'
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        size = "4096"
        sample_file = self.file_api.create(filename, checksum_type, checksum, size, description)
        self.assertTrue(sample_file is not None)
        fileid = sample_file['id']
        id = 'file-repo'
        repo = self.repo_api.create(id, 'file repo', 'noarch')
        repo = self.repo_api.repository(id)
        assert(repo is not None)
        self.repo_api.add_file(repo['id'], [fileid])
        repo = self.repo_api.repository(repo['id'])
        assert(fileid in repo['files'])
        success = False
        try:
            self.file_api.delete(fileid)
        except FileHasReferences:
            success = True
        assert(success)
        
    def test_list_repo_files(self):
        filename = "pulp-test.iso"
        id = 'test_create_errata_id'
        description = 'pulp test iso image'
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        size = "4096"
        sample_file = self.file_api.create(filename, checksum_type, checksum, size, description)
        self.assertTrue(sample_file is not None)
        fileid = sample_file['id']
        id = 'file-repo'
        repo = self.repo_api.create(id, 'file repo', 'noarch')
        repo = self.repo_api.repository(id)
        assert(repo is not None)
        self.repo_api.add_file(repo['id'], [fileid])
        repo = self.repo_api.repository(repo['id'])
        assert(fileid in repo['files'])
        found = self.repo_api.list_files(repo['id'])
        assert(len(found) > 0)

    def test_remove_file_from_repo(self):
        filename = "pulp-test.iso"
        id = 'test_create_errata_id'
        description = 'pulp test iso image'
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        size = "4096"
        sample_file = self.file_api.create(filename,checksum_type, checksum, size, description)
        self.assertTrue(sample_file is not None)
        fileid = sample_file['id']
        id = 'file-repo'
        repo = self.repo_api.create(id, 'file repo', 'noarch')
        repo = self.repo_api.repository(id)
        assert(repo is not None)
        self.repo_api.add_file(repo['id'], [fileid])
        repo = self.repo_api.repository(repo['id'])
        assert(fileid in repo['files'])
        self.repo_api.remove_file(repo['id'], [fileid])
        repo = self.repo_api.repository(repo['id'])
        assert(fileid not in repo['files'])
        
    def test_find_repos_by_files(self):
        filename = "pulp-test.iso"
        id = 'test_create_errata_id'
        description = 'pulp test iso image'
        checksum_type = "sha256"
        checksum = "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
        size = "4096"
        sample_file = self.file_api.create(filename, checksum_type, checksum, size, description)
        self.assertTrue(sample_file is not None)
        fileid = sample_file['id']
        id = 'file-repo'
        repo = self.repo_api.create(id, 'file repo', 'noarch')
        repo = self.repo_api.repository(id)
        assert(repo is not None)
        self.repo_api.add_file(repo['id'], [fileid])
        repo = self.repo_api.repository(repo['id'])
        assert(fileid in repo['files'])
        found = self.repo_api.find_repos_by_files(fileid)
        print "CCCCCCCCC",found
        assert(len(found) > 0)
