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

import mock

from pulp.client.commands.repo.upload import UploadCommand, FLAG_VERBOSE
from pulp.client.commands.options import OPTION_REPO_ID

from pulp_rpm.common.ids import TYPE_ID_PKG_CATEGORY
from pulp_rpm.extension.admin.upload import category
import rpm_support_base


class CreatePackageCategoryCommand(rpm_support_base.PulpClientTests):

    def setUp(self):
        super(CreatePackageCategoryCommand, self).setUp()
        self.upload_manager = mock.MagicMock()
        self.command = category.CreatePackageCategoryCommand(self.context, self.upload_manager)

    def test_structure(self):
        self.assertTrue(isinstance(self.command, UploadCommand))
        self.assertEqual(self.command.name, category.NAME)
        self.assertEqual(self.command.description, category.DESC)

        expected_options = set([category.OPT_CATEGORY_ID, category.OPT_NAME,
                                category.OPT_DESCRIPTION, category.OPT_ORDER,
                                category.OPT_GROUP, FLAG_VERBOSE, OPTION_REPO_ID
                                ])
        found_options = set(self.command.options)

        self.assertEqual(expected_options, found_options)

    def test_determine_type_id(self):
        type_id = self.command.determine_type_id(None)
        self.assertEqual(type_id, TYPE_ID_PKG_CATEGORY)

    def test_generate_unit_key(self):
        args = {
            OPTION_REPO_ID.keyword : 'test-repo',
            category.OPT_CATEGORY_ID.keyword : 'test-cat'
        }
        unit_key = self.command.generate_unit_key(None, **args)
        self.assertEqual(unit_key['id'], 'test-cat')
        self.assertEqual(unit_key['repo_id'], 'test-repo')

    def test_generate_metadata(self):
        args = {
            category.OPT_NAME.keyword : 'test-name',
            category.OPT_DESCRIPTION.keyword : 'test-description',
            category.OPT_ORDER.keyword : 'test-order',
            category.OPT_GROUP.keyword : 'test-group',
        }

        metadata = self.command.generate_metadata(None, **args)

        self.assertEqual(metadata['name'], 'test-name')
        self.assertEqual(metadata['description'], 'test-description')
        self.assertEqual(metadata['display_order'], 'test-order')
        self.assertEqual(metadata['packagegroupids'], 'test-group')
        self.assertEqual(metadata['translated_description'], {})
        self.assertEqual(metadata['translated_name'], '')
