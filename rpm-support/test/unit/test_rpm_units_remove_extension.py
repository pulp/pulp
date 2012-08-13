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

try:
    import json
except ImportError:
    import simplejson as json

import mock
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + '/../../extensions/admin')

from pulp.bindings.responses import STATE_WAITING
from pulp.client.extensions.core import TAG_PARAGRAPH

import rpm_support_base
import rpm_units_remove.pulp_cli

class UnitRemoveTests(rpm_support_base.PulpClientTests):

    def test_remove(self):
        # Setup
        remove_section = rpm_units_remove.pulp_cli.RemoveSection(self.context)
        task_data = {'task_id' : 'abc',
                     'task_group_id' : None,
                     'tags' : [],
                     'start_time' : None,
                     'finish_time' : None,
                     'response' : None,
                     'reasons' : [],
                     'state' : STATE_WAITING,
                     'progress' : None,
                     'result' : None,
                     'exception' : None,
                     'traceback' : None,
                     }
        self.server_mock.request.return_value = (202, task_data)

        # Test
        user_args = {
            'repo-id' : 'test-repo',
            'match' : ['name=remove-me'],
        }
        type_id = 'doomed-type'
        remove_section._remove(type_id, **user_args)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        args = self.server_mock.request.call_args[0]
        self.assertEqual('POST', args[0])
        self.assertEqual('/pulp/api/v2/repositories/%s/actions/unassociate/' % user_args['repo-id'], args[1])

        body = json.loads(args[2])
        self.assertTrue(body['criteria'] is not None)

        tags = self.prompt.get_write_tags()
        self.assertEqual(1, len(tags))
        self.assertEqual(tags[0], TAG_PARAGRAPH)

class RemoveSectionTests(unittest.TestCase):

    def setUp(self):
        self.section = rpm_units_remove.pulp_cli.RemoveSection(mock.MagicMock())

    def test_expected_commands(self):
        # Setup
        ALL_TYPES = ('rpm', 'srpm', 'drpm', 'errata', 'package-group', 'package-category')

        all_command_names = self.section.commands.keys()

        # Test
        self.assertEqual(set(ALL_TYPES), set(all_command_names))

    @mock.patch.object(rpm_units_remove.pulp_cli.RemoveSection, '_remove')
    def test_type_calls(self, mock_copy):
        # Setup
        user_args = {'repo-id' : 'test-repo'}

        # Mapping of type ID to method that handles that type
        call_data = [
            ('rpm', self.section.rpm),
            ('srpm', self.section.srpm),
            ('drpm', self.section.drpm),
            ('erratum', self.section.errata),
            ('package_group', self.section.pkg_group),
            ('package_category', self.section.pkg_category),
        ]

        # Test
        for type_id, func in call_data:
            mock_copy.reset_mock()
            func(**user_args)
            mock_copy.assert_called_once_with(type_id, **user_args)