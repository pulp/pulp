# Copyright (c) 2012 Red Hat, Inc.
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
from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.commands.schedule import (
    DeleteScheduleCommand, ListScheduleCommand, CreateScheduleCommand,
    UpdateScheduleCommand, NextRunCommand)

import base_cli
from pulp_puppet.common.constants import IMPORTER_ID
from pulp_puppet.extension.admin import sync_schedules


class StructureTests(base_cli.ExtensionTests):

    def test_puppet_list_schedule_command(self):
        command = sync_schedules.PuppetListScheduleCommand(self.context)

        self.assertTrue(isinstance(command, ListScheduleCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'list')
        self.assertEqual(command.description, sync_schedules.DESC_LIST)

    def test_puppet_create_schedule_command(self):
        command = sync_schedules.PuppetCreateScheduleCommand(self.context)

        self.assertTrue(isinstance(command, CreateScheduleCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'create')
        self.assertEqual(command.description, sync_schedules.DESC_CREATE)

    def test_puppet_delete_schedule_command(self):
        command = sync_schedules.PuppetDeleteScheduleCommand(self.context)

        self.assertTrue(isinstance(command, DeleteScheduleCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'delete')
        self.assertEqual(command.description, sync_schedules.DESC_DELETE)

    def test_puppet_update_schedule_command(self):
        command = sync_schedules.PuppetUpdateScheduleCommand(self.context)

        self.assertTrue(isinstance(command, UpdateScheduleCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'update')
        self.assertEqual(command.description, sync_schedules.DESC_UPDATE)

    def test_puppet_next_run_command(self):
        command = sync_schedules.PuppetNextRunCommand(self.context)

        self.assertTrue(isinstance(command, NextRunCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'next')
        self.assertEqual(command.description, sync_schedules.DESC_NEXT_RUN)


class RepoSyncSchedulingStrategyTests(base_cli.ExtensionTests):

    def setUp(self):
        super(RepoSyncSchedulingStrategyTests, self).setUp()
        self.strategy = sync_schedules.RepoSyncScheduleStrategy(self.context)

    @mock.patch('pulp.bindings.repository.RepositorySyncSchedulesAPI.add_schedule')
    def test_create_schedule(self, mock_add):
        # Setup
        schedule = '2012-09-18'
        failure_threshold = 3
        enabled = True
        kwargs = {OPTION_REPO_ID.keyword : 'test-repo'}

        # Test
        self.strategy.create_schedule(schedule, failure_threshold, enabled, kwargs)

        # Verify
        self.assertEqual(1, mock_add.call_count)
        call_args = mock_add.call_args[0]
        self.assertEqual('test-repo', call_args[0])
        self.assertEqual(IMPORTER_ID, call_args[1])
        self.assertEqual(schedule, call_args[2])
        self.assertEqual({}, call_args[3])
        self.assertEqual(failure_threshold, call_args[4])
        self.assertEqual(enabled, call_args[5])

    @mock.patch('pulp.bindings.repository.RepositorySyncSchedulesAPI.delete_schedule')
    def test_delete_schedule(self, mock_delete):
        # Setup
        schedule_id = 'fake-schedule'
        kwargs = {OPTION_REPO_ID.keyword : 'fake-repo'}

        # Test
        self.strategy.delete_schedule(schedule_id, kwargs)

        # Verify
        self.assertEqual(1, mock_delete.call_count)
        call_args = mock_delete.call_args[0]
        self.assertEqual('fake-repo', call_args[0])
        self.assertEqual(IMPORTER_ID, call_args[1])
        self.assertEqual(schedule_id, call_args[2])

    @mock.patch('pulp.bindings.repository.RepositorySyncSchedulesAPI.list_schedules')
    def test_retrieve_schedules(self, mock_retrieve):
        # Setup
        kwargs = {OPTION_REPO_ID.keyword : 'retrieve-repo'}

        # Test
        self.strategy.retrieve_schedules(kwargs)

        # Verify
        self.assertEqual(1, mock_retrieve.call_count)
        call_args = mock_retrieve.call_args[0]
        self.assertEqual('retrieve-repo', call_args[0])
        self.assertEqual(IMPORTER_ID, call_args[1])

    @mock.patch('pulp.bindings.repository.RepositorySyncSchedulesAPI.update_schedule')
    def test_update_schedule(self, mock_update):
        # Setup
        kwargs = {OPTION_REPO_ID.keyword : 'fake-repo', 'a' : 'a'}
        schedule_id = 'schedule-id'

        # Test
        self.strategy.update_schedule(schedule_id, **kwargs)

        # Verify
        self.assertEqual(1, mock_update.call_count)
        call_args = mock_update.call_args[0]
        self.assertEqual('fake-repo', call_args[0])
        self.assertEqual(IMPORTER_ID, call_args[1])
        self.assertEqual(schedule_id, call_args[2])
        call_kwargs = mock_update.call_args[1]
        self.assertEqual({'a' : 'a'}, call_kwargs)
