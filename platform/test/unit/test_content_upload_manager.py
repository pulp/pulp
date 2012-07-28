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

import os
import shutil

import base
import mock_plugins

from   pulp.plugins.model import Repository
from   pulp.server.db.model.repository import Repo, RepoImporter
from   pulp.server.exceptions import MissingResource, PulpDataException, PulpExecutionException
import pulp.server.managers.factory as manager_factory

class ContentUploadManagerTests(base.PulpServerTests):

    def setUp(self):
        base.PulpServerTests.setUp(self)
        mock_plugins.install()

        self.upload_manager = manager_factory.content_upload_manager()
        self.repo_manager = manager_factory.repo_manager()
        self.importer_manager = manager_factory.repo_importer_manager()

        upload_storage_dir = self.upload_manager._upload_storage_dir()

        if os.path.exists(upload_storage_dir):
            shutil.rmtree(upload_storage_dir)
        os.makedirs(upload_storage_dir)

    def tearDown(self):
        base.PulpServerTests.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        base.PulpServerTests.clean(self)
        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()

    # -- uploading bits functionality -----------------------------------------

    def test_save_data_string(self):

        # Test
        upload_id = self.upload_manager.initialize_upload()

        write_us = ['abc', 'de', 'fghi', 'jkl']
        offset = 0
        for w in write_us:
            self.upload_manager.save_data(upload_id, offset, w)
            offset += len(w)

        # Verify
        uploaded_filename = self.upload_manager._upload_file_path(upload_id)
        self.assertTrue(os.path.exists(uploaded_filename))

        written = self.upload_manager.read_upload(upload_id)
        self.assertEqual(written, ''.join(write_us))

    def test_save_data_rpm(self):

        # Setup
        test_rpm_filename = os.path.abspath(os.path.dirname(__file__)) + '/data/pulp-test-package-0.3.1-1.fc11.x86_64.rpm'
        self.assertTrue(os.path.exists(test_rpm_filename))

        # Test
        upload_id = self.upload_manager.initialize_upload()

        f = open(test_rpm_filename)
        offset = 0
        chunk_size = 256
        while True:
            f.seek(offset)
            data = f.read(chunk_size)
            if data:
                self.upload_manager.save_data(upload_id, offset, data)
            else:
                break
            offset += chunk_size
        f.close()

        # Verify
        uploaded_filename = self.upload_manager._upload_file_path(upload_id)
        self.assertTrue(os.path.exists(uploaded_filename))

        expected_size = os.path.getsize(test_rpm_filename)
        found_size = os.path.getsize(uploaded_filename)

        self.assertEqual(expected_size, found_size)

    def test_save_no_init(self):

        # Test
        try:
            self.upload_manager.save_data('foo', 0, 'bar')
            self.fail('Expected exception')
        except MissingResource, e:
            self.assertEqual(e.resources['upload_request'], 'foo')

    def test_delete_upload(self):

        # Setup
        upload_id = self.upload_manager.initialize_upload()
        self.upload_manager.save_data(upload_id, 0, 'fus ro dah')

        uploaded_filename = self.upload_manager._upload_file_path(upload_id)
        self.assertTrue(os.path.exists(uploaded_filename))

        # Test
        self.upload_manager.delete_upload(upload_id)

        # Verify
        self.assertTrue(not os.path.exists(uploaded_filename))

    def test_list_upload_ids(self):

        # Test - Empty
        ids = self.upload_manager.list_upload_ids()
        self.assertEqual(0, len(ids))

        # Test - Non-empty
        id1 = self.upload_manager.initialize_upload()
        id2 = self.upload_manager.initialize_upload()

        ids = self.upload_manager.list_upload_ids()
        self.assertEqual(2, len(ids))
        self.assertTrue(id1 in ids)
        self.assertTrue(id2 in ids)

    # -- import functionality -------------------------------------------------

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

        importer_return_report = object()
        mock_plugins.MOCK_IMPORTER.upload_unit.return_value = importer_return_report

        upload_id = self.upload_manager.initialize_upload()
        file_path = self.upload_manager._upload_file_path(upload_id)

        # Test
        self.upload_manager.import_uploaded_unit('repo-u', 'mock-type', key, metadata, upload_id)

        # Verify
        call_args = mock_plugins.MOCK_IMPORTER.upload_unit.call_args[0]
        self.assertTrue(isinstance(call_args[0], Repository))
        self.assertEqual(call_args[1], 'mock-type')
        self.assertEqual(call_args[2], key)
        self.assertEqual(call_args[3], metadata)
        self.assertEqual(call_args[4], file_path)
        self.assertEqual(call_args[5].repo_id, 'repo-u')

        # Clean up
        mock_plugins.MOCK_IMPORTER.upload_unit.return_value = None

    def test_import_uploaded_unit_missing_repo(self):
        # Test
        self.assertRaises(MissingResource, self.upload_manager.import_uploaded_unit, 'fake', 'mock-type', {}, {}, 'irrelevant')

    def test_import_uploaded_unit_importer_error(self):
        # Setup
        self.repo_manager.create_repo('repo-u')
        self.importer_manager.set_importer('repo-u', 'mock-importer', {})

        mock_plugins.MOCK_IMPORTER.upload_unit.side_effect = Exception()

        upload_id = self.upload_manager.initialize_upload()

        # Test
        self.assertRaises(PulpExecutionException, self.upload_manager.import_uploaded_unit, 'repo-u', 'mock-type', {}, {}, upload_id)