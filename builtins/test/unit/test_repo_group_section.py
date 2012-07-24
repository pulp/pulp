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

import copy
import os
import sys
import unittest

import mock

from pulp.bindings.exceptions import NotFoundException

sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)),
    '../../extensions/admin/'))

from pulp_repo.pulp_cli import RepoGroupSection

class TestRepoGroupSection(unittest.TestCase):
    def setUp(self):
        self.section = RepoGroupSection(mock.MagicMock())

    def test_command_presence(self):
        # CUDLS
        COMMAND_NAMES = ('create', 'update', 'delete', 'list', 'search')
        for name in COMMAND_NAMES:
            # Command instance has been added
            self.assertTrue(name in self.section.commands)
            # method exists to process the command
            self.assertTrue(hasattr(self.section, name))
            self.assertTrue(callable(getattr(self.section, name)))

    def test_create(self):
        ARGS = {
            'group-id' : 'rg1',
            # note the '-' is intentional for CLI convenient instead of '_'
            'display-name' : 'repo group 1',
            'description' : 'a great group',
            'note' : ['x=1', 'y=2']
        }
        self.section.create(**ARGS)

        self.section.context.server.repo_group.create.assert_called_once_with(
            ARGS['group-id'], ARGS['display-name'], ARGS['description'],
            {'x':'1', 'y':'2'})
        self.assertEqual(self.section.prompt.render_success_message.call_count, 1)

    def test_update_success(self):
        DELTA = {'display_name' : 'foo'}
        PARAMS = copy.copy(DELTA)
        PARAMS['group-id'] = 'rg1'
        self.section.update(**PARAMS)

        self.section.context.server.repo_group.update.assert_called_once_with(
            'rg1', DELTA)
        self.assertEqual(self.section.prompt.render_success_message.call_count, 1)

    def test_update_not_found(self):
        self.section.context.server.repo_group.update.side_effect = self._raise_not_found

        self.section.update(**{'group-id':'rg1'})
        self.assertEqual(self.section.prompt.write.call_count, 1)
        self.assertTrue(self.section.prompt.write.call_args[0][0].find(
            'does not exist') >= 0)

    def test_update_notes(self):
        DELTA = {'note' : ['x=1', 'y=2']}
        PARAMS = copy.copy(DELTA)
        PARAMS['group-id'] = 'rg1'
        self.section.update(**PARAMS)
        self.section.context.server.repo_group.update.assert_called_once_with(
            'rg1', {'notes':{'x':'1', 'y':'2'}})

    def test_delete_success(self):
        self.section.delete(**{'group-id':'rg1'})

        self.section.context.server.repo_group.delete.assert_called_once_with(
            'rg1')
        self.assertEqual(self.section.prompt.render_success_message.call_count, 1)

    def test_delete_not_found(self):
        self.section.context.server.repo_group.delete.side_effect = self._raise_not_found
        self.section.delete(**{'group-id':'rg1'})

        self.assertEqual(self.section.prompt.write.call_count, 1)
        self.assertTrue(self.section.prompt.write.call_args[0][0].find(
            'does not exist') >= 0)

    def test_list(self):
        self.section.context.server.repo_group.repo_groups.return_value.response_body =\
        [1,2,3]

        # normally okaara would pass in fields=None when it isn't specified on
        # the command line
        self.section.list(fields=None)

        self.section.context.server.repo_group.repo_groups.assert_called_once_with()
        self.assertEqual(self.section.prompt.render_document.call_count, 3)

    def test_search(self):
        self.section.context.server.repo_group_search.search.return_value = [1,2,3]
        self.section.search(limit=3)
        self.assertEqual(self.section.context.server.repo_group_search.search.call_count, 1)
        self.assertEqual(self.section.prompt.render_document.call_count, 3)

    @staticmethod
    def _raise_not_found(*args, **kwargs):
        raise NotFoundException({})
