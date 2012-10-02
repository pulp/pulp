# Copyright (c) 2012 Red Hat, Inc.
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

from pulp_rpm.common.ids import TYPE_ID_RPM
from pulp_rpm.extension.admin.upload import package
import rpm_support_base


RPM_DIR = os.path.abspath(os.path.dirname(__file__)) + '/data/simple_repo_no_comps'
RPM_FILENAME = 'pulp-test-package-0.3.1-1.fc11.x86_64.rpm'

class CreateRpmCommandTests(rpm_support_base.PulpClientTests):

    def setUp(self):
        super(CreateRpmCommandTests, self).setUp()
        self.upload_manager = mock.MagicMock()
        self.command = package.CreateRpmCommand(self.context, self.upload_manager)

    def test_structure(self):
        self.assertTrue(isinstance(self.command, UploadCommand))
        self.assertEqual(self.command.name, package.NAME)
        self.assertEqual(self.command.description, package.DESC)

    def test_determine_type_id(self):
        type_id = self.command.determine_type_id(None)
        self.assertEqual(type_id, TYPE_ID_RPM)

    def test_matching_files_in_dir(self):
        rpms = self.command.matching_files_in_dir(RPM_DIR)
        self.assertEqual(1, len(rpms))
        self.assertEqual(os.path.basename(rpms[0]), RPM_FILENAME)

    def test_generate_unit_key_and_metadata(self):
        filename = os.path.join(RPM_DIR, RPM_FILENAME)
        unit_key, metadata = self.command.generate_unit_key_and_metadata(filename)

        self.assertEqual(unit_key['name'], 'pulp-test-package')
        self.assertEqual(unit_key['version'], '0.3.1')
        self.assertEqual(unit_key['release'], '1.fc11')
        self.assertEqual(unit_key['epoch'], '0')
        self.assertEqual(unit_key['arch'], 'x86_64')

        self.assertEqual(metadata['buildhost'], 'gibson')
        self.assertTrue(metadata['description'].startswith('Test package'))
        self.assertEqual(metadata['filename'], RPM_FILENAME)
        self.assertEqual(metadata['license'], 'MIT')
        self.assertEqual(metadata['relativepath'], RPM_FILENAME)

