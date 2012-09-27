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

from pulp_rpm.common.ids import TYPE_ID_PKG_GROUP
from pulp_rpm.extension.admin.upload import group
import rpm_support_base


class CreatePackageGroupCommand(rpm_support_base.PulpClientTests):

    def setUp(self):
        super(CreatePackageGroupCommand, self).setUp()
        self.upload_manager = mock.MagicMock()
        self.command = group.CreatePackageGroupCommand(self.context, self.upload_manager)

    def test_structure(self):
        self.assertTrue(isinstance(self.command, UploadCommand))
        self.assertEqual(self.command.name, group.NAME)
        self.assertEqual(self.command.description, group.DESC)

        expected_options = set([group.OPT_GROUP_ID, group.OPT_NAME, group.OPT_DESCRIPTION,
                                group.OPT_CONDITIONAL_NAME, group.OPT_MANDATORY_NAME,
                                group.OPT_OPTIONAL_NAME, group.OPT_DEFAULT_NAME,
                                group.OPT_DISPLAY_ORDER, group.OPT_LANGONLY,
                                group.OPT_DEFAULT, group.OPT_USER_VISIBLE,
                                FLAG_VERBOSE, OPTION_REPO_ID
                                ])
        found_options = set(self.command.options)

        self.assertEqual(expected_options, found_options)

    def test_determine_type_id(self):
        type_id = self.command.determine_type_id(None)
        self.assertEqual(type_id, TYPE_ID_PKG_GROUP)

    def test_generate_unit_key(self):
        args = {group.OPT_GROUP_ID.keyword : 'test-group',
                OPTION_REPO_ID.keyword : 'test-repo'}
        unit_key = self.command.generate_unit_key(None, **args)

        self.assertEqual(unit_key['id'], 'test-group')
        self.assertEqual(unit_key['repo_id'], 'test-repo')

    def test_generate_metadata(self):
        args = {
            group.OPT_NAME.keyword : 'test-name',
            group.OPT_DESCRIPTION.keyword : 'test-description',
            group.OPT_MANDATORY_NAME.keyword : 'test-mandatory',
            group.OPT_OPTIONAL_NAME.keyword : 'test-optional',
            group.OPT_DEFAULT_NAME.keyword : 'test-default',
            group.OPT_DISPLAY_ORDER.keyword : 'test-order',
            group.OPT_DEFAULT.keyword : 'test-default',
            group.OPT_LANGONLY.keyword : 'test-lang',
            group.OPT_USER_VISIBLE.keyword : 'test-user-visible',
            group.OPT_CONDITIONAL_NAME.keyword : ['a:A', 'b : B'] # with and without spaces around :
        }

        metadata = self.command.generate_metadata(None, **args)

        self.assertEqual(metadata['name'], 'test-name')
        self.assertEqual(metadata['description'], 'test-description')
        self.assertEqual(metadata['mandatory_package_names'], 'test-mandatory')
        self.assertEqual(metadata['optional_package_names'], 'test-optional')
        self.assertEqual(metadata['default_package_names'], 'test-default')
        self.assertEqual(metadata['conditional_package_names'], [('a', 'A'), ('b', 'B')])
        self.assertEqual(metadata['default'], 'test-default')
        self.assertEqual(metadata['user_visible'], 'test-user-visible')
        self.assertEqual(metadata['langonly'], 'test-lang')
        self.assertEqual(metadata['display_order'], 'test-order')
        self.assertEqual(metadata['translated_description'], {})
        self.assertEqual(metadata['translated_name'], '')
