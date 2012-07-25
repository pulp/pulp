# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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

import mock

import base
import dummy_plugins
from pulp.server.db.model.repository import Repo, RepoImporter
import pulp.server.managers.factory as manager_factory
from pulp.server.webservices.controllers.contents import ContentUnitsCollection


class TestContentUnitsCollection(base.PulpWebserviceTests):
    @mock.patch('pulp.server.webservices.serialization.content.content_unit_obj')
    @mock.patch('pulp.server.webservices.serialization.link.search_safe_link_obj')
    @mock.patch('pulp.server.webservices.serialization.content.content_unit_child_link_objs')
    def test_process_unit(self, mock_content_unit_child_link_objs,
                          mock_search_safe_link_obj, mock_content_unit_obj):
        """
        Make sure it calls the right serialization methods
        """
        UNIT = {'_id':'cu1'}
        ContentUnitsCollection.process_unit(UNIT)
        self.assertEqual(mock_content_unit_child_link_objs.call_count, 1)
        self.assertEqual(mock_search_safe_link_obj.call_count, 1)
        self.assertEqual(mock_content_unit_obj.call_count, 1)

    @mock.patch(
        'pulp.server.webservices.controllers.contents.ContentUnitsCollection.process_unit',
        return_value='ContentUnit')
    @mock.patch(
        'pulp.server.managers.content.query.ContentQueryManager.find_by_criteria',
        return_value=['IAmAUnit'])
    def test_get(self, mock_find_by_criteria, mock_process_unit):
        """
        Make sure this calls process_unit for each result. In this case, we mock
        find_by_criteria so we can simulate results from the database.
        """
        status, body = self.get('/v2/content/units/deb/')
        self.assertEqual(status, 200)
        mock_process_unit.assert_called_once_with('IAmAUnit')


class TestContentUnitsSearch(base.PulpWebserviceTests):
    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.get_content_unit_collection')
    def test_post_retrieves_collection(self, mock_get_collection):
        status, body = self.post('/v2/content/units/deb/search/', {'criteria':{}})
        self.assertEqual(status, 200)
        self.assertEqual(mock_get_collection.call_count, 1)
        self.assertEqual(mock_get_collection.call_args[0][0], 'deb')

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.get_content_unit_collection')
    def test_get_retrieves_collection(self, mock_get_collection):
        status, body = self.get('/v2/content/units/deb/search/?limit=20')
        self.assertEqual(status, 200)
        self.assertEqual(mock_get_collection.call_count, 1)
        self.assertEqual(mock_get_collection.call_args[0][0], 'deb')

    @mock.patch(
        'pulp.server.webservices.controllers.contents.ContentUnitsCollection.process_unit',
        return_value='ContentUnit')
    @mock.patch(
        'pulp.server.managers.content.query.ContentQueryManager.find_by_criteria',
        return_value=['IAmAContentUnit'])
    def test_post_processes_units(self, mock_find, mock_process_unit):
        status, body = self.post('/v2/content/units/deb/search/', {'criteria':{}})
        self.assertEqual(status, 200)
        mock_process_unit.assert_called_once_with(mock_find.return_value[0])

    @mock.patch(
        'pulp.server.webservices.controllers.contents.ContentUnitsCollection.process_unit',
        return_value='ContentUnit')
    @mock.patch(
        'pulp.server.managers.content.query.ContentQueryManager.find_by_criteria',
        return_value=['IAmAContentUnit'])
    def test_get_processes_units(self, mock_find, mock_process_unit):
        status, body = self.get('/v2/content/units/deb/search/?limit=20')
        self.assertEqual(status, 200)
        mock_process_unit.assert_called_once_with(mock_find.return_value[0])

class BaseUploadTest(base.PulpWebserviceTests):

    def setUp(self):
        super(BaseUploadTest, self).setUp()
        self.upload_manager = manager_factory.content_upload_manager()

        upload_storage_dir = self.upload_manager._upload_storage_dir()

        if os.path.exists(upload_storage_dir):
            shutil.rmtree(upload_storage_dir)
        os.makedirs(upload_storage_dir)

        dummy_plugins.install()

    def tearDown(self):
        super(BaseUploadTest, self).tearDown()

        dummy_plugins.reset()

    def clean(self):
        super(BaseUploadTest, self).clean()
        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()

class UploadsCollectionTests(BaseUploadTest):

    def test_get_no_uploads(self):
        # Test
        status, body = self.get('/v2/content/uploads/')

        # Verify
        self.assertEqual(200, status)
        self.assertTrue('upload_ids' in body)
        self.assertEqual([], body['upload_ids'])

    def test_get_uploads(self):
        # Setup
        id1 = self.upload_manager.initialize_upload()
        id2 = self.upload_manager.initialize_upload()

        # Test
        status, body = self.get('/v2/content/uploads/')

        # Verify
        self.assertEqual(200, status)
        self.assertTrue('upload_ids' in body)
        self.assertTrue(id1 in body['upload_ids'])
        self.assertTrue(id2 in body['upload_ids'])

    def test_post(self):
        # Test
        status, body = self.post('/v2/content/uploads/')

        # Verify
        self.assertEqual(201, status)
        self.assertTrue('upload_id' in body)
        self.assertTrue('_href' in body)
        self.assertEqual('/v2/content/uploads/%s/' % body['upload_id'], body['_href'])

        upload_file = self.upload_manager._upload_file_path(body['upload_id'])
        self.assertTrue(os.path.exists(upload_file))

class UploadResourceTests(BaseUploadTest):

    def test_delete(self):
        # Setup
        upload_id = self.upload_manager.initialize_upload()

        # Test
        status, body = self.delete('/v2/content/uploads/%s/' % upload_id)

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(None, body)

        upload_file = self.upload_manager._upload_file_path(upload_id)
        self.assertTrue(not os.path.exists(upload_file))

class UploadSegmentResourceTests(BaseUploadTest):

    def test_put(self):

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
                url = '/v2/content/uploads/%s/%s/' % (upload_id, offset)
                ret = self.put(url, data, serialize_json=False)
                self.assertEqual(ret[0], 200)
                self.assertEqual(ret[1], None)
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

    def test_put_invalid_offset(self):

        # Test
        upload_id = self.upload_manager.initialize_upload()

        status, body = self.put('/v2/content/uploads/%s/foo/' % upload_id, 'string data')

        # Verify
        self.assertEqual(400, status)

    def test_put_invalid_upload(self):

        # Test
        status, body = self.put('/v2/content/uploads/foo/0/', 'string data')

        # Verify
        self.assertEqual(404, status)

# Need to touch base with jconnor about coordinator serialization issues with
# the dummy plugins.
#
#class ImportUnitTests(BaseUploadTest):
#
#    def test_post(self):
#        # Setup
#        upload_id = self.upload_manager.initialize_upload()
#        self.upload_manager.save_data(upload_id, 0, 'string data')
#
#        repo_manager = manager_factory.repo_manager()
#        repo_manager.create_repo('repo-upload')
#        importer_manager = manager_factory.repo_importer_manager()
#        importer_manager.set_importer('repo-upload', 'dummy-importer', {})
#
#        # Test
#        body = {
#            'upload_id' : upload_id,
#            'unit_type_id' : 'dummy-type',
#            'unit_key' : {'name' : 'foo'},
#            'unit_metadata' : {'stuff' : 'bar'},
#        }
#        status, body = self.post('/v2/repositories/repo-upload/actions/import_upload/', body)
#
#        # Verify
#        self.assertEqual(200, status)