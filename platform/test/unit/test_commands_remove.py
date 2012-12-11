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

import unittest

import mock

from pulp.bindings.repository import RepositoryUnitAPI
from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.commands.unit import UnitRemoveCommand


class TestUnitRemoveCommand(unittest.TestCase):
    def setUp(self):
        self.context = mock.MagicMock()
        self.command = UnitRemoveCommand(self.context, 'file')
        self.kwargs = {OPTION_REPO_ID.keyword:'repo1', 'match':'stuff'}

    def test_default_to_remove_method(self):
        self.assertEqual(self.command.method, self.command.remove)

    @mock.patch.object(UnitRemoveCommand, 'add_display_criteria_options', autospec=True)
    def test_no_include_search(self, mock_add):
        # make sure this object does not add options like 'limit' and 'seek'
        command = UnitRemoveCommand(self.context, 'file')
        self.assertEqual(mock_add.call_count, 0)

    def test_remove_postponed(self):
        self.context.server.repo_unit.remove.return_value.response_body.is_postponed.return_value = True

        self.command.remove(**self.kwargs)

        message = self.context.prompt.render_paragraph.call_args[0][0]
        self.assertTrue(message.find('postponed') >= 0)

    def test_remove_not_postponed(self):
        self.context.server.repo_unit.remove.return_value.response_body.is_postponed.return_value = False

        self.command.remove(**self.kwargs)

        message = self.context.prompt.render_paragraph.call_args[0][0]
        self.assertEqual(message.find('postponed'), -1)

    def test_bindings_call(self):
        # mock the binding
        self.context.server.repo_unit.remove = mock.create_autospec(
                RepositoryUnitAPI(self.context).remove)

        # execute
        self.command.remove(**self.kwargs)

        # verify the correct args
        self.context.server.repo_unit.remove.assert_called_once_with(
            'repo1', type_ids=['file'], match='stuff')
