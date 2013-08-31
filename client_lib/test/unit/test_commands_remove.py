# -*- coding: utf-8 -*-
#
# Copyright © 2012-2013 Red Hat, Inc.
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

from pulp.client.commands.criteria import UnitAssociationCriteriaCommand
from pulp.client.commands.polling import PollingCommand
from pulp.client.commands.unit import UnitRemoveCommand, DESC_REMOVE
from pulp.devel.unit import base, task_simulator


class TestUnitRemoveCommand(base.PulpClientTests):

    def setUp(self):
        super(TestUnitRemoveCommand, self).setUp()

        self.command = UnitRemoveCommand(self.context)

        self.mock_poll = mock.MagicMock().poll
        self.command.poll = self.mock_poll

        self.mock_remove_binding = mock.MagicMock().remove
        self.mock_remove_binding.return_value = task_simulator.create_fake_task_response()
        self.bindings.repo_unit.remove = self.mock_remove_binding

    def test_inherited_functionality(self):
        self.assertTrue(isinstance(self.command, UnitAssociationCriteriaCommand))
        self.assertTrue(isinstance(self.command, PollingCommand))

    def test_structure(self):
        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'remove')
        self.assertEqual(self.command.description, DESC_REMOVE)

    def test_run(self):
        # Setup
        self.cli.add_command(self.command)

        # Test
        self.cli.run('remove --repo-id edit-me --str-eq name=foo'.split())

        # Verify
        #   Call to the binding with the data collected by the command
        self.assertEqual(1, self.mock_remove_binding.call_count)
        args = self.mock_remove_binding.call_args[0]
        self.assertEqual(args[0], 'edit-me')
        kwargs = self.mock_remove_binding.call_args[1]
        self.assertEqual(kwargs['str-eq'], [['name', 'foo']])
        self.assertTrue('type_ids' not in kwargs)

        #   Poll call made with the correct value
        self.assertEqual(1, self.mock_poll.call_count)
        self.assertEqual(self.mock_poll.call_args[0][0],
                         [self.mock_remove_binding.return_value.response_body])

    def test_run_with_type_id(self):
        # Setup
        self.command.type_id = 'fake-type'
        self.cli.add_command(self.command)

        # Test
        self.cli.run('remove --repo-id edit-me --str-eq name=foo'.split())

        # Verify
        kwargs = self.mock_remove_binding.call_args[1]
        self.assertTrue(kwargs['type_ids'], ['fake-type'])
