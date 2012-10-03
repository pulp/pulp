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

from pulp.client.commands.criteria import CriteriaCommand
from pulp.client.commands import options
from pulp.client.commands.repo import cudl
from pulp.client.extensions.core import TAG_SUCCESS, TAG_REASONS, TAG_DOCUMENT, TAG_TITLE
from pulp.common.compat import json

import base_cli
from pulp_puppet.common import constants
from pulp_puppet.extension.admin import repo as commands

class CreatePuppetRepositoryCommandTests(base_cli.ExtensionTests):

    def setUp(self):
        super(CreatePuppetRepositoryCommandTests, self).setUp()
        self.command = commands.CreatePuppetRepositoryCommand(self.context)

    def test_structure(self):
        # Ensure the required options
        expected_options = set([options.OPTION_REPO_ID, options.OPTION_DESCRIPTION,
                                options.OPTION_NAME, options.OPTION_NOTES,
                                commands.OPTION_FEED, commands.OPTION_HTTP,
                                commands.OPTION_HTTPS, commands.OPTION_QUERY])
        found_options = set(self.command.options)
        self.assertEqual(expected_options, found_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'create')
        self.assertEqual(self.command.description, cudl.DESC_CREATE)

    def test_run(self):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword : 'test-repo',
            options.OPTION_NAME.keyword : 'Test Name',
            options.OPTION_DESCRIPTION.keyword : 'Test Description',
            options.OPTION_NOTES.keyword : {'a' : 'a'},
            commands.OPTION_FEED.keyword : 'http://localhost',
            commands.OPTION_HTTP.keyword : 'true',
            commands.OPTION_HTTPS.keyword : 'true',
            commands.OPTION_QUERY.keyword : ['q1', 'q2']
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('POST', self.server_mock.request.call_args[0][0])
        self.assertTrue(self.server_mock.request.call_args[0][1].endswith('/v2/repositories/'))

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)
        self.assertEqual('test-repo', body['id'])
        self.assertEqual('Test Name', body['display_name'])
        self.assertEqual('Test Description', body['description'])

        expected_notes = {'a' : 'a', constants.REPO_NOTE_KEY : constants.REPO_NOTE_PUPPET}
        self.assertEqual(expected_notes, body['notes'])

        self.assertEqual(constants.IMPORTER_TYPE_ID, body['importer_type_id'])
        expected_config = {
            u'feed' : u'http://localhost',
            u'queries' : [u'q1', u'q2'],
        }
        self.assertEqual(expected_config, body['importer_config'])

        dist = body['distributors'][0]
        self.assertEqual(constants.DISTRIBUTOR_TYPE_ID, dist[0])
        self.assertEqual(True, dist[2])
        self.assertEqual(constants.DISTRIBUTOR_ID, dist[3])

        expected_config = {
            u'serve_http' : True,
            u'serve_https' : True,
        }
        self.assertEqual(expected_config, dist[1])

        self.assertEqual([TAG_SUCCESS], self.prompt.get_write_tags())


class UpdatePuppetRepositoryCommandTests(base_cli.ExtensionTests):

    def setUp(self):
        super(UpdatePuppetRepositoryCommandTests, self).setUp()
        self.command = commands.UpdatePuppetRepositoryCommand(self.context)

    def test_structure(self):
        # Ensure the required options
        expected_options = set([options.OPTION_REPO_ID, options.OPTION_DESCRIPTION,
                                options.OPTION_NAME, options.OPTION_NOTES,
                                commands.OPTION_FEED, commands.OPTION_HTTP,
                                commands.OPTION_HTTPS, commands.OPTION_QUERY])
        found_options = set(self.command.options)
        self.assertEqual(expected_options, found_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'update')
        self.assertEqual(self.command.description, cudl.DESC_UPDATE)

    def test_run(self):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword : 'test-repo',
            options.OPTION_NAME.keyword : 'Test Name',
            options.OPTION_DESCRIPTION.keyword : 'Test Description',
            options.OPTION_NOTES.keyword : {'a' : 'a'},
            commands.OPTION_FEED.keyword : 'http://localhost',
            commands.OPTION_HTTP.keyword : 'true',
            commands.OPTION_HTTPS.keyword : 'true',
            commands.OPTION_QUERY.keyword : ['q1', 'q2']
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        self.command.run(**data)

        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('PUT', self.server_mock.request.call_args[0][0])
        self.assertTrue(self.server_mock.request.call_args[0][1].endswith('/v2/repositories/test-repo/'))

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)
        self.assertEqual('Test Name', body['delta']['display_name'])
        self.assertEqual('Test Description', body['delta']['description'])

        expected_notes = {'a' : 'a'}
        self.assertEqual(expected_notes, body['delta']['notes'])

        expected_config = {
            u'feed' : u'http://localhost',
            u'queries' : [u'q1', u'q2'],
        }
        self.assertEqual(expected_config, body['importer_config'])

        expected_config = {
            u'serve_http' : True,
            u'serve_https' : True,
        }
        self.assertEqual(expected_config, body['distributor_configs']['puppet_distributor'])

        self.assertEqual([TAG_SUCCESS], self.prompt.get_write_tags())

    def test_run_postponed_and_skipped_change_values(self):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword : 'test-repo',
        }

        self.server_mock.request.return_value = 202, self.task()

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(['postponed', TAG_REASONS], self.prompt.get_write_tags())


class ListPuppetRepositoriesCommandTests(base_cli.ExtensionTests):

    def setUp(self):
        super(ListPuppetRepositoriesCommandTests, self).setUp()
        self.command = commands.ListPuppetRepositoriesCommand(self.context)

    def test_get_repositories(self):
        # Setup
        repos = [
            {'repo_id' : 'repo-1', 'notes' : {constants.REPO_NOTE_KEY : constants.REPO_NOTE_PUPPET}},
            {'repo_id' : 'repo-2', 'notes' : {constants.REPO_NOTE_KEY : constants.REPO_NOTE_PUPPET}},
            {'repo_id' : 'repo-3', 'notes' : {constants.REPO_NOTE_KEY : 'rpm'}},
            {'repo_id' : 'repo-4', 'notes' : {}},
        ]

        self.server_mock.request.return_value = 200, repos

        # Test
        repos = self.command.get_repositories({})

        # Verify
        self.assertEqual(2, len(repos))

        repo_ids = [r['repo_id'] for r in repos]
        self.assertTrue('repo-1' in repo_ids)
        self.assertTrue('repo-2' in repo_ids)


class SearchPuppetRepositoriesCommand(base_cli.ExtensionTests):

    def setUp(self):
        super(SearchPuppetRepositoriesCommand, self).setUp()
        self.command = commands.SearchPuppetRepositoriesCommand(self.context)

    def test_structure(self):
        self.assertTrue(isinstance(self.command, CriteriaCommand))
        self.assertEqual('search', self.command.name)
        self.assertEqual(commands.DESC_SEARCH, self.command.description)

    def test_run(self):
        # Setup
        repos = []
        for i in range(0, 4):
            r = {
                'repo_id' : 'repo_%s' % i,
                'display_name' : 'Repo %s' % i,
                'description' : 'Description',
            }
            repos.append(r)

        self.server_mock.request.return_value = 200, repos

        # Test
        self.command.run()

        # Verify
        expected_tags = [TAG_TITLE]
        expected_tags += map(lambda x : TAG_DOCUMENT, range(0, 12)) # 3 fields * 4 repos
        self.assertEqual(expected_tags, self.prompt.get_write_tags())
