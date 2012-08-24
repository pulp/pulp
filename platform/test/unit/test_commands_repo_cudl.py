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

import mock

from pulp.common.json_compat import json

import base

from pulp.client.commands.repo import cudl
from pulp.client.commands.options import OPTION_DESCRIPTION, OPTION_NAME, OPTION_NOTES, OPTION_REPO_ID
from pulp.client.extensions.core import TAG_SUCCESS

class CreateRepositoryCommandTests(base.PulpClientTests):

    def setUp(self):
        super(CreateRepositoryCommandTests, self).setUp()
        self.command = cudl.CreateRepositoryCommand(self.context)

    def test_structure(self):
        # Ensure all of the expected options are there
        found_options = set(self.command.options)
        expected_options = set([OPTION_DESCRIPTION, OPTION_NAME, OPTION_NOTES, OPTION_REPO_ID])
        self.assertEqual(found_options, expected_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'create')
        self.assertEqual(self.command.description, cudl.DESC_CREATE)

    def test_run(self):
        # Setup
        data = {
            OPTION_REPO_ID.keyword : 'test-repo',
            OPTION_NAME.keyword : 'Test Repository',
            OPTION_DESCRIPTION.keyword : 'Repository Description',
            OPTION_NOTES.keyword : ['a=a', 'b=b'],
        }

        self.server_mock.request.return_value = 201, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('POST', self.server_mock.request.call_args[0][0])

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)
        self.assertEqual(body['id'], 'test-repo')
        self.assertEqual(body['display_name'], 'Test Repository')
        self.assertEqual(body['description'], 'Repository Description')
        self.assertEqual(body['notes'], {'a' : 'a', 'b' : 'b'})

        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_SUCCESS, self.prompt.get_write_tags()[0])


class DeleteRepositoryCommandTests(base.PulpClientTests):

    def setUp(self):
        super(DeleteRepositoryCommandTests, self).setUp()
        self.command = cudl.DeleteRepositoryCommand(self.context)

    def test_structure(self):
        # Ensure all of the expected options are there
        found_options = set(self.command.options)
        expected_options = set([OPTION_REPO_ID])
        self.assertEqual(found_options, expected_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'delete')
        self.assertEqual(self.command.description, cudl.DESC_DELETE)

    def test_run(self):
        # Setup
        data = {
            OPTION_REPO_ID.keyword : 'test-repo',
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('DELETE', self.server_mock.request.call_args[0][0])
        url = self.server_mock.request.call_args[0][1]
        self.assertTrue(url.endswith('/repositories/test-repo/'))

        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_SUCCESS, self.prompt.get_write_tags()[0])

    def test_run_not_found(self):
        # Setup
        data = {
            OPTION_REPO_ID.keyword : 'test-repo',
        }

        self.server_mock.request.return_value = 404, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual('not-found', self.prompt.get_write_tags()[0])


class UpdateRepositoryCommandTests(base.PulpClientTests):

    def setUp(self):
        super(UpdateRepositoryCommandTests, self).setUp()
        self.command = cudl.UpdateRepositoryCommand(self.context)

    def test_structure(self):
        # Ensure all of the expected options are there
        found_options = set(self.command.options)
        expected_options = set([OPTION_DESCRIPTION, OPTION_NAME, OPTION_NOTES, OPTION_REPO_ID])
        self.assertEqual(found_options, expected_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'update')
        self.assertEqual(self.command.description, cudl.DESC_UPDATE)

    def test_run(self):
        # Setup
        repo_id = 'test-repo'
        data = {
            OPTION_REPO_ID.keyword : repo_id,
            OPTION_NAME.keyword : 'Test Repository',
            OPTION_DESCRIPTION.keyword : 'Repository Description',
            OPTION_NOTES.keyword : ['a=a', 'b=b'],
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('PUT', self.server_mock.request.call_args[0][0])

        url = self.server_mock.request.call_args[0][1]
        self.assertTrue(url.endswith('/repositories/%s/' % repo_id))

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)
        self.assertEqual(body['delta']['display_name'], 'Test Repository')
        self.assertEqual(body['delta']['description'], 'Repository Description')
        self.assertEqual(body['delta']['notes'], {'a' : 'a', 'b' : 'b'})

        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_SUCCESS, self.prompt.get_write_tags()[0])

    def test_run_not_found(self):
        # Setup
        data = {
            OPTION_REPO_ID.keyword : 'test-repo',
        }

        self.server_mock.request.return_value = 404, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual('not-found', self.prompt.get_write_tags()[0])


class ListRepositoriesCommandTests(base.PulpClientTests):

    def setUp(self):
        super(ListRepositoriesCommandTests, self).setUp()
        self.command = cudl.ListRepositoriesCommand(self.context)

    def test_structure(self):
        # Ensure the correct arguments are present
        expected_option_names = set(['--summary', '--fields', '--importers', '--distributors'])
        found_option_names = set([o.name for o in self.command.options])
        self.assertEqual(expected_option_names, found_option_names)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'list')
        self.assertEqual(self.command.description, cudl.DESC_LIST)

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list')
    def test_run_with_summary(self, mock_call):
        # Setup
        data = {
            'summary' : True,
            'importers' : True,
            'distributors' : True,
        }

        self.server_mock.request.return_value = 200, []

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('GET', self.server_mock.request.call_args[0][0])

        url = self.server_mock.request.call_args[0][1]
        self.assertTrue('/repositories/' in url)
        self.assertTrue('importers=True' in url)
        self.assertTrue('distributors=True' in url)

        render_kwargs = mock_call.call_args[1]
        expected = ['id', 'display_name', 'importers', 'distributors']
        self.assertEqual(render_kwargs['filters'], expected)
        self.assertEqual(render_kwargs['order'], expected)

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list')
    def test_run_with_fields(self, mock_call):
        # Setup
        data = {
            'summary' : None,
            'importers' : None,
            'distributors' : None,
            'fields' : 'display_name'
        }

        self.server_mock.request.return_value = 200, []

        # Test
        self.command.run(**data)

        # Verify
        render_kwargs = mock_call.call_args[1]
        self.assertEqual(render_kwargs['filters'], ['display_name', 'id'])
        self.assertEqual(render_kwargs['order'], ['id'])
