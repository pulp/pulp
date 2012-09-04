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

import mock
from pulp.client.commands.repo.upload import UploadCommand

import base_cli
from pulp_puppet.common import constants
from pulp_puppet.common.model import Module
from pulp_puppet.extension.admin import upload

MODULES_DIR = os.path.abspath(os.path.dirname(__file__)) + '/../data/good-modules/jdob-valid/pkg'

class UploadModuleCommandTests(base_cli.ExtensionTests):

    def setUp(self):
        super(UploadModuleCommandTests, self).setUp()
        self.upload_manager = mock.MagicMock()
        self.command = upload.UploadModuleCommand(self.context, self.upload_manager)
        self.filename = os.path.join(MODULES_DIR, 'jdob-valid-1.0.0.tar.gz')

    def test_structure(self):
        self.assertTrue(isinstance(self.command, UploadCommand))

    def test_generate_unit_key(self):
        # Test
        key = self.command.generate_unit_key(self.filename)

        # Verify
        expected_key = Module.generate_unit_key('valid', '1.0.0', 'jdob')
        self.assertEqual(key, expected_key)

    def test_determine_type_id(self):
        type_id = self.command.determine_type_id(self.filename)
        self.assertEqual(type_id, constants.TYPE_PUPPET_MODULE)

    def test_matching_files_in_dir(self):
        # Test
        module_files = self.command.matching_files_in_dir(MODULES_DIR)

        # Verify

        # Simple filename check
        expected = set(['jdob-valid-1.0.0.tar.gz', 'jdob-valid-1.1.0.tar.gz'])
        found = set([os.path.basename(m) for m in module_files])
        self.assertEqual(expected, found)

        # Make sure the full paths are valid
        for m in module_files:
            self.assertTrue(os.path.exists(m))