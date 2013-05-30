# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 Red Hat, Inc.
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

import base

from pulp.client.commands.repo import history
from pulp.client.commands.options import OPTION_REPO_ID


class SyncHistoryCommandTests(base.PulpClientTests):

    def setUp(self):
        super(SyncHistoryCommandTests, self).setUp()
        self.command = history.SyncHistoryCommand(self.context)

    def test_structure(self):
        # Ensure the correct options are present
        found_options = set(self.command.options)
        expected_options = (OPTION_REPO_ID, history.OPTION_LIMIT, history.FLAG_DETAILS)
        self.assertEqual(found_options, expected_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'sync')
        self.assertEqual(self.command.description, history.DESC_SYNC_HISTORY)

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list', autospec=True)
    def test_run(self, mock_render_document_list):
        # TODO: Test (with mock) that all the right calls are made, with the correct arguments
        # set up the kwargs to pass to the run method
        arguments = {
            'repo-id': 'test-repo',
            'details': True,
            'limit': 1
        }

        # Set the mock server to return 200 as the response status and an empty list as the response body
        self.server_mock.request.return_value = 200, []

        self.command.run(**arguments)

        # Check that the command called the mock server once
        self.assertEqual(1, self.server_mock.request.call_count)
        # self.assertEqual('GET', self.server_mock.request.call_args[0][0])

