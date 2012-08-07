#!/usr/bin/python
#
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

try:
    import json
except ImportError:
    import simplejson as json

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + '/../../extensions/admin')

import rpm_support_base
import rpm_units_copy.pulp_cli

from pulp.bindings.responses import STATE_WAITING
from pulp.client.extensions.core import TAG_FAILURE, TAG_PARAGRAPH

class UnitCopyTests(rpm_support_base.PulpClientTests):

    def test_copy(self):
        # Setup
        command = rpm_units_copy.pulp_cli.CopySection(self.context)._copy
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
            'from-repo-id' : 'from-repo',
            'to-repo-id' : 'to-repo',
            'match' : ['name=pulp', 'version=1']
        }
        command('rpm', **user_args)

        # Verify
        args = self.server_mock.request.call_args[0]
        self.assertEqual('POST', args[0])
        self.assertEqual('/pulp/api/v2/repositories/to-repo/actions/associate/', args[1])

        body = json.loads(args[2])
        self.assertEqual(body['source_repo_id'], 'from-repo')

        criteria = body['criteria']
        self.assertTrue(criteria is not None)
        self.assertEqual(criteria['type_ids'], ['rpm'])

        tags = self.prompt.get_write_tags()
        self.assertEqual(1, len(tags))
        self.assertEqual(tags[0], TAG_PARAGRAPH)


class UnitSectionTests(unittest.TestCase):
    def setUp(self):
        self.section = rpm_units_copy.pulp_cli.CopySection(mock.MagicMock())

    def test_command_presence(self):
        commands_present = set(self.section.commands.keys())
        self.assertEquals(set(['rpm', 'drpm', 'srpm']), commands_present)

    @mock.patch.object(rpm_units_copy.pulp_cli.CopySection, '_copy')
    def test_rpm(self, mock_copy):
        kwargs = {'from-repo-id': 'repo1', 'to-repo-id': 'repo2'}
        self.section.rpm(**kwargs)
        mock_copy.assert_called_once_with('rpm', **kwargs)

    @mock.patch.object(rpm_units_copy.pulp_cli.CopySection, '_copy')
    def test_srpm(self, mock_copy):
        kwargs = {'from-repo-id': 'repo1', 'to-repo-id': 'repo2'}
        self.section.srpm(**kwargs)
        mock_copy.assert_called_once_with('srpm', **kwargs)

    @mock.patch.object(rpm_units_copy.pulp_cli.CopySection, '_copy')
    def test_drpm(self, mock_copy):
        kwargs = {'from-repo-id': 'repo1', 'to-repo-id': 'repo2'}
        self.section.drpm(**kwargs)
        mock_copy.assert_called_once_with('drpm', **kwargs)

    def calls_binding(self):
        kwargs = {'from-repo-id': 'repo1', 'to-repo-id': 'repo2'}
        self.section._copy('rpm', **kwargs)
        self.section.context.server.repo_unit.copy.assert_called_once_with(
            'repo1', 'repo2', type_ids=['rpm'])

