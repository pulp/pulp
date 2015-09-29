import errno
import os
import shutil

import unittest
import mock

from .... import base
from pulp.devel import mock_plugins
from pulp.plugins.conduits.upload import UploadConduit
from pulp.server.db import models
from pulp.server.db.model.auth import User
from pulp.server.db.model.repository import RepoImporter
from pulp.server.exceptions import (MissingResource, PulpDataException, PulpExecutionException,
                                    InvalidValue)
from pulp.server.managers.content.upload import ContentUploadManager
import pulp.server.managers.factory as manager_factory


class ContentUploadManagerTests(base.PulpServerTests):

    def setUp(self):
        base.PulpServerTests.setUp(self)
        mock_plugins.install()

        self.upload_manager = manager_factory.content_upload_manager()
        self.importer_manager = manager_factory.repo_importer_manager()

    def tearDown(self):
        base.PulpServerTests.tearDown(self)
        mock_plugins.reset()

        upload_storage_dir = self.upload_manager._upload_storage_dir()
        shutil.rmtree(upload_storage_dir)

    def clean(self):
        base.PulpServerTests.clean(self)
        models.Repository.drop_collection()
        RepoImporter.get_collection().remove()

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
        test_rpm_filename = os.path.abspath(os.path.dirname(__file__)) + \
            '/../../../../data/pulp-test-package-0.3.1-1.fc11.x86_64.rpm'
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

    def test_delete_non_existent_upload(self):

        # Setup
        upload_id = '1234'

        uploaded_filename = self.upload_manager._upload_file_path(upload_id)
        self.assertFalse(os.path.exists(uploaded_filename))

        # Test
        try:
            self.upload_manager.delete_upload(upload_id)
        except Exception:
            self.fail('An Exception should not have been raised.')

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

    @mock.patch('pulp.server.managers.repo.importer.models.Repository.objects')
    def test_is_valid_upload(self, mock_repo_qs):
        self.importer_manager.set_importer('repo-u', 'mock-importer', {})
        valid = self.upload_manager.is_valid_upload('repo-u', 'mock-type')
        self.assertTrue(valid)

    @mock.patch('pulp.server.managers.repo.importer.models.Repository.objects')
    def test_is_valid_upload_missing_or_bad_repo(self, mock_repo_qs):
        self.assertRaises(MissingResource, self.upload_manager.is_valid_upload, 'empty',
                          'mock-type')
        self.assertRaises(MissingResource, self.upload_manager.is_valid_upload, 'fake', 'mock-type')

    @mock.patch('pulp.server.managers.repo.importer.models.Repository.objects')
    def test_is_valid_upload_unsupported_type(self, mock_repo_qs):
        self.importer_manager.set_importer('repo-u', 'mock-importer', {})
        # Test
        self.assertRaises(PulpDataException, self.upload_manager.is_valid_upload, 'repo-u',
                          'fake-type')

    @mock.patch('pulp.server.managers.repo.importer.models.Repository.objects')
    def test_import_uploaded_unit(self, mock_repo_qs):
        self.importer_manager.set_importer('repo-u', 'mock-importer', {})

        key = {'key': 'value'}
        metadata = {'k1': 'v1'}

        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        importer_return_report = object()
        mock_plugins.MOCK_IMPORTER.upload_unit.return_value = importer_return_report

        upload_id = self.upload_manager.initialize_upload()
        file_path = self.upload_manager._upload_file_path(upload_id)

        fake_user = User('import-user', '')
        manager_factory.principal_manager().set_principal(principal=fake_user)

        response = self.upload_manager.import_uploaded_unit('repo-u', 'mock-type', key, metadata,
                                                            upload_id)

        # import_uploaded_unit() should have returned our importer_return_report
        self.assertTrue(response is importer_return_report)

        call_args = mock_plugins.MOCK_IMPORTER.upload_unit.call_args[0]
        self.assertTrue(call_args[0] is mock_repo.to_transfer_repo())
        self.assertEqual(call_args[1], 'mock-type')
        self.assertEqual(call_args[2], key)
        self.assertEqual(call_args[3], metadata)
        self.assertEqual(call_args[4], file_path)

        conduit = call_args[5]
        self.assertTrue(isinstance(conduit, UploadConduit))
        self.assertEqual(call_args[5].repo_id, 'repo-u')

        # Clean up
        mock_plugins.MOCK_IMPORTER.upload_unit.return_value = None
        manager_factory.principal_manager().set_principal(principal=None)

    def test_import_uploaded_unit_missing_repo(self):
        # Test
        self.assertRaises(MissingResource, self.upload_manager.import_uploaded_unit, 'fake',
                          'mock-type', {}, {}, 'irrelevant')

    @mock.patch('pulp.server.managers.repo.importer.models.Repository.objects')
    def test_import_uploaded_unit_importer_error(self, mock_repo_qs):
        self.importer_manager.set_importer('repo-u', 'mock-importer', {})
        mock_plugins.MOCK_IMPORTER.upload_unit.side_effect = Exception()
        upload_id = self.upload_manager.initialize_upload()
        self.assertRaises(PulpExecutionException, self.upload_manager.import_uploaded_unit,
                          'repo-u', 'mock-type', {}, {}, upload_id)

    @mock.patch('pulp.server.managers.repo.importer.models.Repository.objects')
    def test_import_uploaded_unit_importer_error_reraise_pulp_exception(self, mock_repo_qs):
        self.importer_manager.set_importer('repo-u', 'mock-importer', {})
        mock_plugins.MOCK_IMPORTER.upload_unit.side_effect = InvalidValue(['filename'])
        upload_id = self.upload_manager.initialize_upload()
        self.assertRaises(InvalidValue, self.upload_manager.import_uploaded_unit, 'repo-u',
                          'mock-type', {}, {}, upload_id)

    def test_upload_dir_auto_created(self):
        # Setup

        # Make sure it definitely doesn't exist before calling this
        upload_storage_dir = self.upload_manager._upload_storage_dir()
        shutil.rmtree(upload_storage_dir)

        # Test
        upload_storage_dir = self.upload_manager._upload_storage_dir()

        # Verify
        self.assertTrue(os.path.exists(upload_storage_dir))


class TestContentUploadManager(unittest.TestCase):

    @mock.patch.object(ContentUploadManager, '_upload_file_path')
    @mock.patch('pulp.server.managers.content.upload.os')
    def test_delete_upload_removes_file(self, mock_os, mock__upload_file_path):
        my_upload_id = 'asdf'
        ContentUploadManager().delete_upload(my_upload_id)
        mock__upload_file_path.assert_called_once_with(my_upload_id)
        mock_os.remove.assert_called_once_with(mock__upload_file_path.return_value)

    @mock.patch.object(ContentUploadManager, '_upload_file_path')
    @mock.patch('pulp.server.managers.content.upload.os')
    def test_delete_upload_silences_ENOENT_error(self, mock_os, mock__upload_file_path):
        my_upload_id = 'asdf'
        mock_os.remove.side_effect = OSError(errno.ENOENT, os.strerror(errno.ENOENT))
        try:
            ContentUploadManager().delete_upload(my_upload_id)
        except Exception:
            self.fail('An Exception should not have been raised.')

    @mock.patch.object(ContentUploadManager, '_upload_file_path')
    @mock.patch('pulp.server.managers.content.upload.os')
    def test_delete_upload_allows_non_ENOENT_OSErrors_to_raise(self, mock_os,
                                                               mock__upload_file_path):
        my_upload_id = 'asdf'
        mock_os.remove.side_effect = OSError(errno.EISDIR, os.strerror(errno.EISDIR))
        self.assertRaises(OSError, ContentUploadManager().delete_upload, my_upload_id)

    @mock.patch.object(ContentUploadManager, '_upload_file_path')
    @mock.patch('pulp.server.managers.content.upload.os')
    def test_delete_upload_allows_non_OSErrors_to_raise(self, mock_os, mock__upload_file_path):
        my_upload_id = 'asdf'
        mock_os.remove.side_effect = ValueError()
        self.assertRaises(ValueError, ContentUploadManager().delete_upload, my_upload_id)
