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

import os
import sys
import unittest

import mock

sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)),
    '../../extensions/admin/'))

from pulp_repo.pulp_cli import RepoGroupMemberSection

class TestRepoGroupMemberSection(unittest.TestCase):
    def setUp(self):
        self.section = RepoGroupMemberSection(mock.MagicMock())

    def test_command_presence(self):
        COMMAND_NAMES = ('add', 'remove', 'list')
        for name in COMMAND_NAMES:
            # Command instance has been added
            self.assertTrue(name in self.section.commands)
            # method exists to process the command
            self.assertTrue(hasattr(self.section, name))
            self.assertTrue(callable(getattr(self.section, name)))

    def test_add(self):
        params = {'group-id' :'rg1', 'filters' : {'id':'repo2'}}
        self.section.add(**params)
        self.section.context.server.repo_group_actions.associate.assert_called_once_with(
            'rg1', filters={'id':'repo2'})

    def test_remove(self):
        params = {'group-id' :'rg1', 'filters' : {'id':'repo2'}}
        self.section.remove(**params)
        self.section.context.server.repo_group_actions.unassociate.assert_called_once_with(
            'rg1', filters={'id':'repo2'})

    def test_list_not_found(self):
        # test behavior when the repo group is not found
        # setup
        self.section.context.server.repo_group_search.search.return_value = []
        params = {'group-id' :'rg1'}

        # call
        self.section.list(**params)

        # verify
        self.assertEqual(self.section.prompt.write.call_count, 1)
        output = self.section.prompt.write.call_args[0][0]
        self.assertTrue('does not exist' in output)

    def test_list(self):
        # setup
        self.section.context.server.repo_group_search.search.return_value =\
            [{'repo_ids':['repo1']}]
        self.section.context.server.repo_search.search.return_value = [{'id':'repo1'}]
        params = {'group-id' :'rg1'}

        # call
        self.section.list(**params)

        # verify
        self.assertEqual(self.section.context.server.repo_search.search.call_count, 1)
        self.assertEqual(self.section.prompt.render_document_list.call_count, 1)

