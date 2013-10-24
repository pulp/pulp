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

from pulp.bindings.responses import STATE_FINISHED
from pulp.client.commands.polling import PollingCommand
from pulp.client.commands.repo import cudl
from pulp.client.commands.options import OPTION_DESCRIPTION, OPTION_NAME, OPTION_NOTES, OPTION_REPO_ID
from pulp.client.extensions.core import TAG_SUCCESS, TAG_TITLE
from pulp.common.compat import json
from pulp.devel.unit import base
from pulp.devel.unit.task_simulator import TaskSimulator


class CreateRepositoryCommandTests(base.PulpClientTests):

    def setUp(self):
        super(CreateRepositoryCommandTests, self).setUp()
        self.command = cudl.CreateRepositoryCommand(self.context)

    def test_structure(self):
        # Ensure all of the expected options are there
        for o in [OPTION_DESCRIPTION, OPTION_NAME, OPTION_NOTES, OPTION_REPO_ID]:
            self.assertTrue(o in self.command.options)

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
        self.assertTrue(isinstance(self.command, PollingCommand))

        # Ensure all of the expected options are there
        self.assertTrue(OPTION_REPO_ID in self.command.options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'delete')
        self.assertEqual(self.command.description, cudl.DESC_DELETE)

    @mock.patch('pulp.client.commands.polling.PollingCommand.poll')
    def test_run(self, mock_poll):
        # Setup
        data = {
            OPTION_REPO_ID.keyword : 'test-repo',
        }

        sim = TaskSimulator()
        sim.add_task_state('123', STATE_FINISHED)

        mock_binding_delete = mock.MagicMock().delete
        mock_binding_delete.return_value = sim.get_all_tasks()
        self.bindings.repo.delete = mock_binding_delete

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, mock_binding_delete.call_count)
        self.assertEqual('test-repo', mock_binding_delete.call_args[0][0])
        self.assertEqual(1, mock_poll.call_count)

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
            OPTION_NOTES.keyword : {'a' : 'a', 'b' : 'b'},
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
        expected_option_names = set(['--details', '--fields', '--all', '--summary'])
        found_option_names = set([o.name for o in self.command.options])
        self.assertEqual(expected_option_names, found_option_names)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'list')
        self.assertEqual(self.command.description, cudl.DESC_LIST)

    def test_no_all_structure(self):
        # Ensure the all argument isn't present
        self.command = cudl.ListRepositoriesCommand(self.context, include_all_flag=False)
        expected_option_names = set(['--details', '--fields', '--summary'])
        found_option_names = set([o.name for o in self.command.options])
        self.assertEqual(expected_option_names, found_option_names)

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list')
    def test_run_with_details(self, mock_call):
        # Setup
        data = {
            'summary' : False,
            'details' : True,
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
        expected = ['id', 'display_name', 'description', 'content_unit_counts',
                    'notes', 'importers', 'distributors']
        self.assertEqual(render_kwargs['filters'], expected)
        self.assertEqual(render_kwargs['order'], expected)

        self.assertEqual(1, len(self.prompt.get_write_tags())) # only one title, not the others

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list')
    def test_run_with_fields(self, mock_call):
        # Setup
        data = {
            'summary' : False,
            'details' : False,
            'fields' : 'display_name',
        }

        self.server_mock.request.return_value = 200, []

        # Test
        self.command.run(**data)

        # Verify
        render_kwargs = mock_call.call_args[1]
        expected_filters = ['display_name', 'id']

        self.assertEqual(render_kwargs['filters'], expected_filters)
        self.assertEqual(render_kwargs['order'], ['id'])

        self.assertEqual(1, len(self.prompt.get_write_tags())) # only one title, not the others

    def test_all(self):
        # Setup
        data = {
            'summary' : False,
            'details' : True,
            'all' : True,
        }

        self.server_mock.request.return_value = 200, []

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(2, len(self.prompt.get_write_tags())) # only one title, not the others
        self.assertEqual([TAG_TITLE, TAG_TITLE], self.prompt.get_write_tags())

    def test_summary(self):
        # Setup
        data = {
            'summary' : True,
            'details' : False,
        }

        self.command.get_repositories = mock.MagicMock()
        self.command.get_other_repositories = mock.MagicMock()
        self.command.get_repositories.return_value = [
            {'id' : 'abcdef', 'display_name' : 'ABCDEF'},
            {'id' : 'xyz', 'display_name' : 'XYZ'}
        ]

        self.command.prompt.terminal_size = mock.MagicMock()
        self.command.prompt.terminal_size.return_value = 20, 20

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(self.command.get_repositories.call_count, 1)
        self.assertEqual(self.command.get_other_repositories.call_count, 0)

        self.assertEqual(self.recorder.lines[0], 'abcdef  ABCDEF\n')
        self.assertEqual(self.recorder.lines[1], 'xyz     XYZ\n')

