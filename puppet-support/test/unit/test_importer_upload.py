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
import tempfile
import unittest

import mock
from pulp.plugins.model import Repository

from pulp_puppet.common import constants
from pulp_puppet.importer import upload

DATA_DIR = os.path.abspath(os.path.dirname(__file__)) + '/../data'

class UploadTests(unittest.TestCase):

    def setUp(self):
        self.unit_key = {
            'name' : 'pulp',
            'version' : '2.0.0',
            'author' : 'jdob',
        }
        self.unit_metadata = {
            'source' : 'http://pulpproject.org',
        }
        self.dest_dir = tempfile.mkdtemp(prefix='puppet-upload-test')
        self.dest_file = os.path.join(self.dest_dir, 'jdob-valid-1.0.0.tar.gz')
        self.source_file = os.path.join(DATA_DIR, 'good-modules',
                                          'jdob-valid', 'pkg', 'jdob-valid-1.0.0.tar.gz')

        self.conduit = mock.MagicMock()

        self.working_dir = tempfile.mkdtemp(prefix='puppet-sync-tests')
        self.repo = Repository('test-repo', working_dir=self.working_dir)

    def tearDown(self):
        shutil.rmtree(self.working_dir)
        if os.path.exists(self.dest_dir):
            shutil.rmtree(self.dest_dir)

    def test_handle_uploaded_unit(self):
        # Setup
        initialized_unit = mock.MagicMock()
        initialized_unit.storage_path = self.dest_dir
        self.conduit.init_unit.return_value = initialized_unit

        # Test
        upload.handle_uploaded_unit(self.repo, constants.TYPE_PUPPET_MODULE, self.unit_key,
                                    self.unit_metadata, self.source_file, self.conduit)

        # Verify
        self.assertTrue(os.path.exists(self.dest_file))

        self.assertEqual(1, self.conduit.init_unit.call_count)
        self.assertEqual(1, self.conduit.save_unit.call_count)

    def test_handle_uploaded_unit_bad_type(self):
        self.assertRaises(NotImplementedError, upload.handle_uploaded_unit, self.repo, 'foo', None, None, None, None)