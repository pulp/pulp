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

import sys
import os
import copy

from okaara.cli import CommandUsage

try:
    from urlparse import parse_qs
except ImportError:
    # this was moved to the urlparse module in python 2.6
    from cgi import parse_qs

import mock

sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)),
    '../../extensions/admin/'))

import base_builtins
from pulp_repo import pulp_cli

class TestRepoSearch(base_builtins.PulpClientTests):
    def setUp(self):
        super(TestRepoSearch, self).setUp()
        self.repo_section = pulp_cli.RepoSection(self.context)

    def test_has_command(self):
        """
        Make sure the command was added to the section
        """
        self.assertTrue('search' in self.repo_section.commands)

    @mock.patch('pulp.bindings.search.SearchAPI.search')
    def test_calls_search_api(self, mock_search):
        self.repo_section.search(limit=20)
        self.assertEqual(mock_search.call_count, 1)
        self.assertTrue('limit' in mock_search.call_args[1])
        self.assertEqual(mock_search.call_args[1]['limit'], 20)

    @mock.patch('pulp.bindings.search.SearchAPI.search', return_value=[1,2])
    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document')
    def test_calls_render(self, mock_render, mock_search):
        """
        the values 1 and 2 are just stand-in unique values that would actually
        be dict-like documents as returned by mongo. For this test, we just need
        to know that a value gets passed from one place to another.
        """
        self.repo_section.search(limit=20)
        self.assertEqual(mock_render.call_count, 2)
        self.assertTrue(mock_render.call_args_list[0][0][0] in (1, 2))
        self.assertTrue(mock_render.call_args_list[1][0][0] in (1, 2))

    def test_invalid_input(self):
        self.assertRaises(CommandUsage, self.repo_section.search, x=2)


class TestRepoExtension(base_builtins.PulpClientTests):
    @property
    def REPO1(self):
        return copy.copy({
            'id' : 'repo-1',
            'display_name' : 'Repository 1',
            'importers' : ({'id' : 'imp-1'},),
            'distributors' : ({'id' : 'dist-1'},)
        })

    def setUp(self):
        super(TestRepoExtension, self).setUp()
        self.repo_section = pulp_cli.RepoSection(self.context)

    def test_create(self):
        section = pulp_cli.RepoSection(mock.MagicMock())
        ARGS = {
            'repo-id' : 'repo1',
            # note the '-' is intentional for CLI convenient instead of '_'
            'display-name' : 'repo 1',
            'description' : 'a great repo',
            'note' : ['x=1', 'y=2']
        }
        section.create(**ARGS)

        section.context.server.repo.create.assert_called_once_with(
            ARGS['repo-id'], ARGS['display-name'], ARGS['description'],
                {'x':'1', 'y':'2'})
        self.assertEqual(section.prompt.render_success_message.call_count, 1)

    def test_update_notes(self):
        section = pulp_cli.RepoSection(mock.MagicMock())
        DELTA = {'note' : ['x=1', 'y=2']}
        PARAMS = copy.copy(DELTA)
        PARAMS['repo-id'] = 'repo1'
        section.update(**PARAMS)
        section.context.server.repo.update.assert_called_once_with(
            'repo1', {'delta':{'notes':{'x':'1', 'y':'2'}}})

    def test_has_group_subsection(self):
        self.assertTrue('group' in self.repo_section.subsections)

    def test_list_no_data(self):
        """
        Test retrieving the list of repos when there are no repos present.
        """
        self.server_mock.request.return_value = (200, ())

        self.repo_section.list(summary=True, importers=False, distributors=False)

        self.assertEqual(len(self.recorder.lines), 4)

    def test_list(self):
        """
        Test retrieving the list of repos when there is at least one present.
        """
        self.server_mock.request.return_value = (200, (self.REPO1,))

        self.repo_section.list(summary=True, importers=False, distributors=False)

        self.assertTrue(len(self.recorder.lines) > 4)

    def test_list_with_importers(self):
        self.server_mock.request = mock.MagicMock(return_value = (200, ()))
        self.repo_section.list(summary=True, importers=True, distributors=False)

        self.assertEqual(self.server_mock.request.call_count, 1)
        call_args = self.server_mock.request.call_args[0]
        self.assertEqual(call_args[0], 'GET')
        self.assertTrue(call_args[1].endswith('/repositories/?importers=True'))

    def test_list_without_importers(self):
        self.server_mock.request = mock.MagicMock(return_value = (200, ()))
        self.repo_section.list(summary=True, importers=False, distributors=False)

        self.assertEqual(self.server_mock.request.call_count, 1)
        call_args = self.server_mock.request.call_args[0]
        self.assertEqual(call_args[0], 'GET')
        self.assertTrue(call_args[1].endswith('/repositories/'))

    def test_list_with_distributors(self):
        self.server_mock.request = mock.MagicMock(return_value = (200, ()))
        self.repo_section.list(summary=True, importers=False, distributors=True)

        self.assertEqual(self.server_mock.request.call_count, 1)
        call_args = self.server_mock.request.call_args[0]
        self.assertEqual(call_args[0], 'GET')
        self.assertTrue(call_args[1].endswith('/repositories/?distributors=True'))

    def test_list_without_distributors(self):
        self.server_mock.request = mock.MagicMock(return_value = (200, ()))
        self.repo_section.list(summary=True, importers=False, distributors=False)

        self.assertEqual(self.server_mock.request.call_count, 1)
        call_args = self.server_mock.request.call_args[0]
        self.assertEqual(call_args[0], 'GET')
        self.assertTrue(call_args[1].endswith('/repositories/'))

    def test_list_with_importers_and_distributors(self):
        self.server_mock.request = mock.MagicMock(return_value = (200, ()))
        self.repo_section.list(summary=True, importers=True, distributors=True)

        self.assertEqual(self.server_mock.request.call_count, 1)
        call_args = self.server_mock.request.call_args[0]
        self.assertEqual(call_args[0], 'GET')
        self.assertTrue(call_args[1].find('/repositories/?') >= 0)

        query_string = call_args[1][call_args[1].find('?') + 1:]
        query_params = parse_qs(query_string)
        for param in ('importers', 'distributors'):
            self.assertTrue(param in query_params)
            self.assertTrue(query_params[param][0])

