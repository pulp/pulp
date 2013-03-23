# -*- coding: utf-8 -*-
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

import base

from pulp.bindings.exceptions import BadRequestException
from pulp.client.commands.criteria import UnitAssociationCriteriaCommand
from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.commands.polling import PollingCommand
import pulp.client.commands.unit as unit_commands
from pulp.devel.unit import task_simulator


class UnitCopyCommandTests(base.PulpClientTests):

    def setUp(self):
        super(UnitCopyCommandTests, self).setUp()

        self.command = unit_commands.UnitCopyCommand(self.context)

        self.mock_poll = mock.MagicMock().poll
        self.command.poll = self.mock_poll

        self.mock_copy_binding = mock.MagicMock().copy
        self.mock_copy_binding.return_value = task_simulator.create_fake_task_response()
        self.bindings.repo_unit.copy = self.mock_copy_binding

    def test_inherited_functionality(self):
        self.assertTrue(isinstance(self.command, UnitAssociationCriteriaCommand))
        self.assertTrue(isinstance(self.command, PollingCommand))

    def test_structure(self):
        # Ensure all of the expected options are there
        repo_id_options = [o for o in self.command.options if o.keyword == 'repo-id']
        self.assertEqual(0, len(repo_id_options))
        self.assertTrue(unit_commands.OPTION_FROM_REPO in self.command.options)
        self.assertTrue(unit_commands.OPTION_TO_REPO in self.command.options)

        # Ensure the options are configured correctly
        self.assertTrue(unit_commands.OPTION_FROM_REPO.required)
        self.assertTrue(unit_commands.OPTION_TO_REPO.required)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'copy')
        self.assertEqual(self.command.description, unit_commands.DESC_COPY)

    def test_run(self):
        # Setup
        self.cli.add_command(self.command)

        # Test
        self.cli.run('copy --from-repo-id from --to-repo-id to --str-eq name=foo'.split())

        # Verify
        #   Call to the binding with the data collected by the command
        self.assertEqual(1, self.mock_copy_binding.call_count)
        args = self.mock_copy_binding.call_args[0]
        self.assertEqual(args[0], 'from')
        self.assertEqual(args[1], 'to')
        kwargs = self.mock_copy_binding.call_args[1]
        self.assertEqual(kwargs['override_config'], {})  # default for generate_override_config
        self.assertEqual(kwargs['str-eq'], [['name', 'foo']])
        self.assertTrue('type_ids' not in kwargs)

        #   Poll call made with the correct value
        self.assertEqual(1, self.mock_poll.call_count)
        self.assertEqual(self.mock_poll.call_args[0][0], [self.mock_copy_binding.return_value.response_body])

    def test_run_with_type_id(self):
        # Setup
        self.command.type_id = 'fake-type'
        self.cli.add_command(self.command)

        # Test
        self.cli.run('copy --from-repo-id from --to-repo-id to'.split())

        # Verify
        kwargs = self.mock_copy_binding.call_args[1]
        self.assertTrue(kwargs['type_ids'], ['fake-type'])

    def test_run_bad_request(self):
        """
        Tests the property name translation from the REST API keys to the CLI keys.
        """
        # Setup
        self.cli.add_command(self.command)
        self.mock_copy_binding.side_effect = BadRequestException({'property_names' : ['source_repo_id']})

        # Test
        try:
            self.cli.run('copy --from-repo-id from --to-repo-id to'.split())
        except BadRequestException, e:
            self.assertEqual(e.extra_data['property_names'], ['from-repo-id'])

