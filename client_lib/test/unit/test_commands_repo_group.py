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

from pulp.client.commands.options import (OPTION_GROUP_ID, OPTION_REPO_ID,
    OPTION_DESCRIPTION, OPTION_NOTES, OPTION_NAME, FLAG_ALL)
from pulp.client.commands.repo import group
from pulp.client.extensions.core import TAG_SUCCESS, TAG_DOCUMENT, TAG_TITLE, TAG_FAILURE
from pulp.common.compat import json
from pulp.devel.unit import base


class CreateRepositoryGroupCommandTests(base.PulpClientTests):

    def setUp(self):
        super(CreateRepositoryGroupCommandTests, self).setUp()
        self.command = group.CreateRepositoryGroupCommand(self.context)

    def test_structure(self):
        # Ensure the proper options
        expected_options = set([OPTION_GROUP_ID, OPTION_NAME, OPTION_DESCRIPTION, OPTION_NOTES])
        non_repo_id_options = set([o for o in self.command.options if o.name != OPTION_REPO_ID.name])
        self.assertEqual(expected_options, non_repo_id_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'create')
        self.assertEqual(self.command.description, group.DESC_CREATE)

    def test_run(self):
        # Setup
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
            OPTION_NAME.keyword : 'Group',
            OPTION_DESCRIPTION.keyword : 'Description',
            OPTION_NOTES.keyword : {'a' : 'a', 'b' : 'b'},
        }

        self.server_mock.request.return_value = 201, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('POST', self.server_mock.request.call_args[0][0])

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)
        self.assertEqual(body['id'], 'test-group')
        self.assertEqual(body['display_name'], 'Group')
        self.assertEqual(body['description'], 'Description')
        self.assertEqual(body['notes'], {'a' : 'a', 'b' : 'b'})

        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_SUCCESS, self.prompt.get_write_tags()[0])


class DeleteRepositoryGroupCommandTests(base.PulpClientTests):

    def setUp(self):
        super(DeleteRepositoryGroupCommandTests, self).setUp()
        self.command = group.DeleteRepositoryGroupCommand(self.context)

    def test_structure(self):
        # Ensure the proper options
        expected_options = set([OPTION_GROUP_ID])
        found_options = set(self.command.options)
        self.assertEqual(expected_options, found_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'delete')
        self.assertEqual(self.command.description, group.DESC_DELETE)

    def test_run(self):
        # Setup
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('DELETE', self.server_mock.request.call_args[0][0])
        url = self.server_mock.request.call_args[0][1]
        self.assertTrue(url.endswith('/repo_groups/test-group/'))

        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_SUCCESS, self.prompt.get_write_tags()[0])

    def test_run_not_found(self):
        # Setup
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
        }

        self.server_mock.request.return_value = 404, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual('not-found', self.prompt.get_write_tags()[0])


class UpdateRepositoryGroupCommandTests(base.PulpClientTests):

    def setUp(self):
        super(UpdateRepositoryGroupCommandTests, self).setUp()
        self.command = group.UpdateRepositoryGroupCommand(self.context)

    def test_structure(self):
        # Ensure the proper options
        expected_options = set([OPTION_GROUP_ID, OPTION_NAME, OPTION_DESCRIPTION, OPTION_NOTES])
        found_options = set(self.command.options)
        self.assertEqual(expected_options, found_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'update')
        self.assertEqual(self.command.description, group.DESC_UPDATE)

    def test_run(self):
        # Setup
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
            OPTION_NAME.keyword : 'Group',
            OPTION_DESCRIPTION.keyword : 'Description',
            OPTION_NOTES.keyword : {'a' : 'a', 'b' : 'b'},
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('PUT', self.server_mock.request.call_args[0][0])

        url = self.server_mock.request.call_args[0][1]
        self.assertTrue(url.endswith('/repo_groups/test-group/'))

        body = self.server_mock.request.call_args[0][2]
        delta = json.loads(body)
        self.assertTrue('display-name' not in delta)
        self.assertEqual(delta['display_name'], 'Group')
        self.assertEqual(delta['description'], 'Description')
        self.assertEqual(delta['notes'], {'a' : 'a', 'b' : 'b'})

    def test_run_not_found(self):
        # Setup
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
        }

        self.server_mock.request.return_value = 404, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual('not-found', self.prompt.get_write_tags()[0])


class ListRepositoryGroupsCommandTests(base.PulpClientTests):

    def setUp(self):
        super(ListRepositoryGroupsCommandTests, self).setUp()
        self.command = group.ListRepositoryGroupsCommand(self.context)

    def test_structure(self):
        # Ensure the proper options
        expected_option_names = set(['--details', '--fields'])
        found_option_names = set([o.name for o in self.command.options])
        self.assertEqual(expected_option_names, found_option_names)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'list')
        self.assertEqual(self.command.description, group.DESC_LIST)

    def test_run(self):
        # Setup
        data = {
            'details' : True,
            'fields' : 'display_name'
        }

        self.server_mock.request.return_value = 200, [{'id' : 'a'}]

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('GET', self.server_mock.request.call_args[0][0])

        url = self.server_mock.request.call_args[0][1]
        self.assertTrue(url.endswith('/repo_groups/'))

        self.assertEqual(2, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_TITLE, self.prompt.get_write_tags()[0])
        self.assertEqual(TAG_DOCUMENT, self.prompt.get_write_tags()[1])

    def test_run_not_found(self):
        # Setup
        data = {
            'details' : True,
            'fields' : 'display_name'
        }

        self.server_mock.request.return_value = 200, []

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(2, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_TITLE, self.prompt.get_write_tags()[0])
        self.assertEqual('not-found', self.prompt.get_write_tags()[1])


class SearchRepositoryGroupsCommandTests(base.PulpClientTests):

    def setUp(self):
        super(SearchRepositoryGroupsCommandTests, self).setUp()
        self.command = group.SearchRepositoryGroupsCommand(self.context)

    def test_structure(self):
        # The options are set by the base class; won't retest here

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'search')
        self.assertEqual(self.command.description, group.DESC_SEARCH)

    def test_run(self):
        # Setup
        self.server_mock.request.return_value = 200, [{'a' : 'a', 'b' : 'b'}]

        # Test
        self.command.run()

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('POST', self.server_mock.request.call_args[0][0])

        url = self.server_mock.request.call_args[0][1]
        self.assertTrue(url.endswith('/repo_groups/search/'))

        self.assertEqual(3, len(self.prompt.get_write_tags()))
        self.assertEqual(self.prompt.get_write_tags(), [TAG_TITLE, TAG_DOCUMENT, TAG_DOCUMENT])


class ListRepositoryGroupMembersCommandTests(base.PulpClientTests):

    def setUp(self):
        super(ListRepositoryGroupMembersCommandTests, self).setUp()
        self.command = group.ListRepositoryGroupMembersCommand(self.context)

    def test_structure(self):
        # Ensure the proper options
        expected_options = set([OPTION_GROUP_ID])
        found_options = set(self.command.options)
        self.assertEqual(expected_options, found_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'list')
        self.assertEqual(self.command.description, group.DESC_MEMBER_LIST)

    def test_run(self):
        # Setup
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
        }

        return_values = [
            (200, [{'repo_ids' : ['repo-1']}]), # return from search groups call
            (200, [{'id' : 'a'}]), # return from the repo search call
        ]

        self.server_mock.request.side_effect = return_values

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(2, self.server_mock.request.call_count)

        # Group lookup call
        call_args = self.server_mock.request.call_args_list[0]
        self.assertEqual('POST', call_args[0][0])

        url = call_args[0][1]
        self.assertTrue(url.endswith('/repo_groups/search/'))

        body = json.loads(call_args[0][2])
        self.assertEqual(body['criteria']['filters']['id'], 'test-group')

        # Repo lookup call
        call_args = self.server_mock.request.call_args_list[1]
        self.assertEqual('POST', call_args[0][0])
        url = call_args[0][1]
        self.assertTrue(url.endswith('/repositories/search/'))

        body = json.loads(call_args[0][2])
        self.assertEqual(body['criteria']['filters']['id'], {'$in' : ['repo-1']})

        # Output
        self.assertEqual(2, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_TITLE, self.prompt.get_write_tags()[0])
        self.assertEqual(TAG_DOCUMENT, self.prompt.get_write_tags()[1])

    def test_run_no_group(self):
        # Setup
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
        }

        self.server_mock.request.return_value = 200, []

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)

        # Group lookup call
        call_args = self.server_mock.request.call_args_list[0]
        self.assertEqual('POST', call_args[0][0])

        url = call_args[0][1]
        self.assertTrue(url.endswith('/repo_groups/search/'))

        body = json.loads(call_args[0][2])
        self.assertEqual(body['criteria']['filters']['id'], 'test-group')

        # Output
        self.assertEqual(2, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_TITLE, self.prompt.get_write_tags()[0])
        self.assertEqual('not-found', self.prompt.get_write_tags()[1])

    def test_run_no_members(self):
        # Setup
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
            }

        return_values = [
            (200, [{'repo_ids' : []}]), # return from search groups call
        ]

        self.server_mock.request.side_effect = return_values

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)

        # Output
        self.assertEqual(2, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_TITLE, self.prompt.get_write_tags()[0])
        self.assertEqual('no-members', self.prompt.get_write_tags()[1])


class AddRepositoryGroupMembersCommandTests(base.PulpClientTests):

    def setUp(self):
        super(AddRepositoryGroupMembersCommandTests, self).setUp()
        self.command = group.AddRepositoryGroupMembersCommand(self.context)

    def test_structure(self):
        # Don't verify all of the criteria options but make sure group ID is there
        self.assertTrue(OPTION_GROUP_ID in self.command.options)
        self.assertTrue(not self.command.include_search)

        # Ensure the repo ID option is a copy of the original and has the
        # desired changes
        repo_id_option = [o for o in self.command.options if o.name == OPTION_REPO_ID.name][0]
        self.assertTrue(repo_id_option is not OPTION_REPO_ID)
        self.assertTrue(not repo_id_option.required)
        self.assertTrue(repo_id_option.allow_multiple)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'add')
        self.assertEqual(self.command.description, group.DESC_MEMBER_ADD)

    def test_requires_criteria_arg(self):
        # make sure it requires at least one matching arg
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
        }
        self.command.run(**data)

        self.assertTrue(TAG_FAILURE in self.prompt.get_write_tags())

    def test_adds_repo_to_search(self):
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
            FLAG_ALL.keyword : False,
            OPTION_REPO_ID.keyword : ['repo1']
        }
        self.server_mock.request.return_value = 200, {}

        self.command.run(**data)

        criteria = json.loads(self.server_mock.request.call_args[0][2])['criteria']

        self.assertEqual(criteria['filters']['id']['$in'], ['repo1'])

    def test_repo_id_and_all(self):
        # --all should not prevent other filters from being added.
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
            FLAG_ALL.keyword : True,
            OPTION_REPO_ID.keyword : ['repo1']
        }
        self.server_mock.request.return_value = 200, {}

        self.command.run(**data)

        criteria = json.loads(self.server_mock.request.call_args[0][2])['criteria']

        self.assertEqual(criteria['filters']['id']['$in'], ['repo1'])

    def test_repo_id_and_match(self):
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
            FLAG_ALL.keyword : False,
            OPTION_REPO_ID.keyword : ['repo1'],
            'match' : [('id', 'repo.+')]
        }
        self.server_mock.request.return_value = 200, {}

        self.command.run(**data)

        criteria = json.loads(self.server_mock.request.call_args[0][2])['criteria']

        self.assertEqual(len(criteria['filters']['$and']), 2)
        # make sure each of these filter types shows up in the criteria
        self.assertEqual(
            len(set(['$in', '$regex']) & set(criteria['filters']['$and'][0]['id'])), 1)
        self.assertEqual(
            len(set(['$in', '$regex']) & set(criteria['filters']['$and'][1]['id'])), 1)

    def test_run(self):
        # Setup
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
            FLAG_ALL.keyword : True,
            OPTION_REPO_ID.keyword : None
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('POST', self.server_mock.request.call_args[0][0])

        url = self.server_mock.request.call_args[0][1]
        self.assertTrue(url.endswith('/repo_groups/test-group/actions/associate/'))

        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_SUCCESS, self.prompt.get_write_tags()[0])


class RemoveRepositoryGroupMembersCommandTests(base.PulpClientTests):

    def setUp(self):
        super(RemoveRepositoryGroupMembersCommandTests, self).setUp()
        self.command = group.RemoveRepositoryGroupMembersCommand(self.context)

    def test_structure(self):
        # Don't verify all of the criteria options but make sure group ID is there
        self.assertTrue(OPTION_GROUP_ID in self.command.options)
        self.assertTrue(not self.command.include_search)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'remove')
        self.assertEqual(self.command.description, group.DESC_MEMBER_REMOVE)

    def test_requires_criteria_arg(self):
        # make sure it requires at least one matching arg
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
        }
        self.command.run(**data)

        self.assertTrue(TAG_FAILURE in self.prompt.get_write_tags())

    def test_adds_repo_to_search(self):
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
            FLAG_ALL.keyword : False,
            OPTION_REPO_ID.keyword : ['repo1']
        }
        self.server_mock.request.return_value = 200, {}

        self.command.run(**data)

        criteria = json.loads(self.server_mock.request.call_args[0][2])['criteria']

        self.assertEqual(criteria['filters']['id']['$in'], ['repo1'])

    def test_repo_id_and_all(self):
        # --all should not prevent other filters from being added.
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
            FLAG_ALL.keyword : False,
            OPTION_REPO_ID.keyword : ['repo1']
        }
        self.server_mock.request.return_value = 200, {}

        self.command.run(**data)

        criteria = json.loads(self.server_mock.request.call_args[0][2])['criteria']

        self.assertEqual(criteria['filters']['id']['$in'], ['repo1'])

    def test_repo_id_and_match(self):
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
            FLAG_ALL.keyword : False,
            OPTION_REPO_ID.keyword : ['repo1'],
            'match' : [('id', 'repo.+')]
        }
        self.server_mock.request.return_value = 200, {}

        self.command.run(**data)

        criteria = json.loads(self.server_mock.request.call_args[0][2])['criteria']

        self.assertEqual(len(criteria['filters']['$and']), 2)
        # make sure each of these filter types shows up in the criteria
        self.assertEqual(
            len(set(['$in', '$regex']) & set(criteria['filters']['$and'][0]['id'])), 1)
        self.assertEqual(
            len(set(['$in', '$regex']) & set(criteria['filters']['$and'][1]['id'])), 1)

    def test_run(self):
        # Setup
        data = {
            OPTION_GROUP_ID.keyword : 'test-group',
            FLAG_ALL.keyword : True,
            OPTION_REPO_ID.keyword : None
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('POST', self.server_mock.request.call_args[0][0])

        url = self.server_mock.request.call_args[0][1]
        self.assertTrue(url.endswith('/repo_groups/test-group/actions/unassociate/'))

        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_SUCCESS, self.prompt.get_write_tags()[0])
