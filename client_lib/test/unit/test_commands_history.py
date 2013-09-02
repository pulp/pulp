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

from pulp.client.commands.repo import history
from pulp.client.commands.options import OPTION_REPO_ID
from pulp.devel.unit import base


class SyncHistoryCommandTests(base.PulpClientTests):

    def setUp(self):
        super(SyncHistoryCommandTests, self).setUp()
        self.command = history.SyncHistoryCommand(self.context)
        # Set a default argument list for the command and return value for the server
        self.arguments = {
            OPTION_REPO_ID.keyword: 'test-repo',
            history.OPTION_LIMIT.keyword: None,
            history.OPTION_SORT.keyword: None,
            history.OPTION_START_DATE.keyword: None,
            history.OPTION_END_DATE.keyword: None,
            history.FLAG_DETAILS.keyword: False
        }
        self.server_mock.request.return_value = 200, []

    def test_structure(self):
        # Ensure the correct options are present
        found_options = set(self.command.options)
        expected_options = set((OPTION_REPO_ID, history.OPTION_LIMIT, history.OPTION_SORT,
                               history.OPTION_START_DATE, history.OPTION_END_DATE, history.FLAG_DETAILS))
        self.assertEqual(found_options, expected_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'sync')
        self.assertEqual(self.command.description, history.DESC_SYNC_HISTORY)

    @mock.patch('pulp.bindings.repository.RepositoryHistoryAPI.sync_history', autospec=True)
    def test_run_binding(self, mock_sync_history):
        args = self.arguments
        args[history.OPTION_START_DATE.keyword] = '2012-12-21T12:00:00Z'
        args[history.OPTION_END_DATE.keyword] = '2012-12-22T12:00:00Z'
        args[history.OPTION_SORT.keyword] = 'descending'
        self.command.run(**args)

        # Verify sync_history got called with the correct arguments
        self.assertEqual(1, mock_sync_history.call_count)
        # Verifies the repo_id
        self.assertEqual('test-repo', mock_sync_history.call_args[0][1])
        # Verifies the limit
        self.assertEqual(5, mock_sync_history.call_args[0][2])
        # Verifies the sort
        self.assertEqual('descending', mock_sync_history.call_args[0][3])
        # Verifies the start_date
        self.assertEqual('2012-12-21T12:00:00Z', mock_sync_history.call_args[0][4])
        # Verifies the end_date
        self.assertEqual('2012-12-22T12:00:00Z', mock_sync_history.call_args[0][5])

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list', autospec=True)
    def test_run_render(self, mock_render_doc_list):
        self.command.run(**self.arguments)

        # Assert that render_document_list was called with the correct items, filter, and order
        render_kwargs = mock_render_doc_list.call_args[1]
        expected_filter = expected_order = ['repo_id', 'result', 'started', 'completed', 'added_count',
                                            'removed_count', 'updated_count']
        self.assertEqual(expected_filter.sort(), render_kwargs['filters'].sort())
        self.assertEqual(expected_order, render_kwargs['order'])
        self.assertEqual([], mock_render_doc_list.call_args[0][1])
        self.assertEqual(1, len(self.prompt.get_write_tags()))

    @mock.patch('pulp.bindings.repository.RepositoryHistoryAPI.sync_history', autospec=True)
    def test_run_with_limit(self, mock_sync_history):
        # set up kwargs with a limit that is not None and add a response body greater than limit
        args = self.arguments.copy()
        args[history.OPTION_LIMIT.keyword] = '1'
        self.command.run(**args)

        # Assert that render_document_list was called and the result list was of length limit
        self.assertEqual(1, mock_sync_history.call_count)
        self.assertEqual(1, mock_sync_history.call_args[0][2])

    @mock.patch('pulp.bindings.repository.RepositoryHistoryAPI.sync_history', autospec=True)
    def test_run_without_limit(self, mock_sync_history):
        self.command.run(**self.arguments)

        self.assertEqual(1, mock_sync_history.call_count)
        self.assertEqual(5, mock_sync_history.call_args[0][2])

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list', autospec=True)
    def test_run_with_details(self, mock_render_doc_list):
        # set up kwargs with the details flag on and then run
        args = self.arguments.copy()
        args[history.FLAG_DETAILS.keyword] = True
        self.command.run(**args)

        # Assert that render_doc_list was called with a filter containing 'details' and 'summary'
        render_kwargs = mock_render_doc_list.call_args[1]
        self.assertTrue('details' and 'summary' in render_kwargs['filters'])
        self.assertTrue('details' and 'summary' in render_kwargs['order'])

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list', autospec=True)
    def test_run_without_details(self, mock_render_doc_list):
        self.command.run(**self.arguments)

        # Assert that render_doc_list was called with a filter containing 'details' and 'summary'
        render_kwargs = mock_render_doc_list.call_args[1]
        self.assertFalse('details' and 'summary' in render_kwargs['filters'])
        self.assertFalse('details' and 'summary' in render_kwargs['order'])


class PublishHistoryCommandTests(base.PulpClientTests):
    def setUp(self):
        super(PublishHistoryCommandTests, self).setUp()
        self.command = history.PublishHistoryCommand(self.context)
        self.arguments = {
            OPTION_REPO_ID.keyword: 'test-repo',
            history.OPTION_DISTRIBUTOR_ID.keyword: 'test-distrib',
            history.OPTION_LIMIT.keyword: None,
            history.OPTION_SORT.keyword: None,
            history.OPTION_START_DATE.keyword: None,
            history.OPTION_END_DATE.keyword: None,
            history.FLAG_DETAILS.keyword: False
        }
        self.server_mock.request.return_value = 200, []

    def test_structure(self):
        # Ensure the correct options are present
        found_options = set(self.command.options)
        expected_options = set((OPTION_REPO_ID, history.OPTION_DISTRIBUTOR_ID, history.OPTION_LIMIT,
                                history.OPTION_SORT, history.OPTION_START_DATE, history.OPTION_END_DATE,
                                history.FLAG_DETAILS))
        self.assertEqual(found_options, expected_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'publish')
        self.assertEqual(self.command.description, history.DESC_PUBLISH_HISTORY)

    @mock.patch('pulp.bindings.repository.RepositoryHistoryAPI.publish_history', autospec=True)
    def test_run_bindings(self, mock_publish_history):
        self.command.run(**self.arguments)

        # Verify publish_history got called with the correct arguments
        self.assertEqual(1, mock_publish_history.call_count)
        self.assertEqual('test-repo', mock_publish_history.call_args[0][1])
        self.assertEqual('test-distrib', mock_publish_history.call_args[0][2])

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list', autospec=True)
    def test_run_render(self, mock_render_doc_list):
        self.command.run(**self.arguments)

        # Assert that render_document_list was called with the correct items, filter, and order
        render_kwargs = mock_render_doc_list.call_args[1]
        expected_filters = expected_order = ['repo_id', 'distributor_id', 'result', 'started',
                                             'completed']
        self.assertEqual(1, mock_render_doc_list.call_count)
        self.assertEqual(expected_filters, render_kwargs['filters'])
        self.assertEqual(expected_order, render_kwargs['order'])
        self.assertEqual([], mock_render_doc_list.call_args[0][1])  # Check items arg is an empty list
        self.assertEqual(1, len(self.prompt.get_write_tags()))

    @mock.patch('pulp.bindings.repository.RepositoryHistoryAPI.publish_history', autospec=True)
    def test_run_with_limit(self, mock_publish_history):
        args = self.arguments.copy()
        args[history.OPTION_LIMIT.keyword] = '1'
        self.command.run(**args)

        # Limit is applied by the server, so just confirm publish_history was called with limit='1'
        self.assertEqual(1, mock_publish_history.call_args[0][3])

    @mock.patch('pulp.bindings.repository.RepositoryHistoryAPI.publish_history', autospec=True)
    def test_run_without_limit(self, mock_publish_history):
        self.command.run(**self.arguments)

        # Assert that a default limit of 5 is given to publish_history
        self.assertEqual(5, mock_publish_history.call_args[0][3])

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list', autospec=True)
    def test_run_with_details(self, mock_render_doc_list):
        args = self.arguments.copy()
        args[history.FLAG_DETAILS.keyword] = True
        self.command.run(**args)

        # Assert that render_doc_list was called with a filter containing 'details' and 'summary'
        render_kwargs = mock_render_doc_list.call_args[1]
        self.assertTrue('details' and 'summary' in render_kwargs['filters'])
        self.assertTrue('details' and 'summary' in render_kwargs['order'])

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list', autospec=True)
    def test_run_without_details(self, mock_render_doc_list):
        self.command.run(**self.arguments)

        # Assert that render_doc_list was called with a filter that doesn't have 'details' and 'summary'
        render_kwargs = mock_render_doc_list.call_args[1]
        self.assertFalse('details' and 'summary' in render_kwargs['filters'])
        self.assertFalse('details' and 'summary' in render_kwargs['order'])
