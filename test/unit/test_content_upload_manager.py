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

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil
import mock_plugins

from pulp.server.db.model.gc_repository import Repo, RepoImporter
from pulp.server.exceptions import MissingResource, PulpDataException, PulpExecutionException
import pulp.server.managers.factory as manager_factory

class ContentUploadManagerTests(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)
        mock_plugins.install()

        self.upload_manager = manager_factory.content_upload_manager()
        self.repo_manager = manager_factory.repo_manager()
        self.importer_manager = manager_factory.repo_importer_manager()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        testutil.PulpTest.clean(self)
        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()

    def test_is_valid_upload(self):
        # Setup
        self.repo_manager.create_repo('repo-u')
        self.importer_manager.set_importer('repo-u', 'mock-importer', {})

        # Test
        valid = self.upload_manager.is_valid_upload('repo-u', 'mock-type')

        # Verify
        self.assertTrue(valid)

    def test_is_valid_upload_missing_or_bad_repo(self):
        # Setup
        self.repo_manager.create_repo('empty')

        # Test
        self.assertRaises(MissingResource, self.upload_manager.is_valid_upload, 'empty', 'mock-type')
        self.assertRaises(MissingResource, self.upload_manager.is_valid_upload, 'fake', 'mock-type')

    def test_is_valid_upload_unsupported_type(self):
        # Setup
        self.repo_manager.create_repo('repo-u')
        self.importer_manager.set_importer('repo-u', 'mock-importer', {})

        # Test
        self.assertRaises(PulpDataException, self.upload_manager.is_valid_upload, 'repo-u', 'fake-type')

    def test_import_uploaded_unit(self):
        # Setup
        self.repo_manager.create_repo('repo-u')
        self.importer_manager.set_importer('repo-u', 'mock-importer', {})

        key = {'key' : 'value'}
        metadata = {'k1' : 'v1'}
        file_path = '/foo/bar'

        importer_return_report = object()
        mock_plugins.MOCK_IMPORTER.upload_unit.return_value = importer_return_report

        # Test
        report = self.upload_manager.import_uploaded_unit('repo-u', 'mock-type', key, metadata, file_path)

        # Verify
        self.assertEqual(report, importer_return_report)

        call_args = mock_plugins.MOCK_IMPORTER.upload_unit.call_args[0]
        self.assertEqual(call_args[0], 'mock-type')
        self.assertEqual(call_args[1], key)
        self.assertEqual(call_args[2], metadata)
        self.assertEqual(call_args[3], file_path)
        self.assertEqual(call_args[4].repo_id, 'repo-u')

        # Clean up
        mock_plugins.MOCK_IMPORTER.upload_unit.return_value = None

    def test_import_uploaded_unit_missing_repo(self):
        # Test
        self.assertRaises(MissingResource, self.upload_manager.import_uploaded_unit, 'fake', 'mock-type', {}, {}, '/tmp')

    def test_import_uploaded_unit_importer_error(self):
        # Setup
        self.repo_manager.create_repo('repo-u')
        self.importer_manager.set_importer('repo-u', 'mock-importer', {})

        mock_plugins.MOCK_IMPORTER.upload_unit.side_effect = Exception()

        # Test
        self.assertRaises(PulpExecutionException, self.upload_manager.import_uploaded_unit, 'repo-u', 'mock-type', {}, {}, '/tmp')