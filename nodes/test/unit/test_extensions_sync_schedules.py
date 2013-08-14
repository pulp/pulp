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

import unittest

import mock
from pulp.client.commands.schedule import CreateScheduleCommand, ListScheduleCommand, \
    DeleteScheduleCommand, UpdateScheduleCommand, NextRunCommand

from pulp_node import constants
from pulp_node.extensions.admin import sync_schedules
from pulp_node.extensions.admin.options import NODE_ID_OPTION, MAX_BANDWIDTH_OPTION, MAX_CONCURRENCY_OPTION


NODE_ID = 'node-1'
MAX_BANDWIDTH = 12345
MAX_CONCURRENCY = 321


class CommandTests(unittest.TestCase):

    def setUp(self):
        super(CommandTests, self).setUp()
        self.context = mock.MagicMock()

    def test_list_schedule_command(self):
        command = sync_schedules.NodeListScheduleCommand(self.context)
        self.assertTrue(isinstance(command, ListScheduleCommand))
        self.assertTrue(NODE_ID_OPTION in command.options)
        self.assertEqual(command.description, sync_schedules.DESC_LIST)
        self.assertTrue(isinstance(command.strategy, sync_schedules.NodeSyncScheduleStrategy))

    def test_create_schedule_command(self):
        command = sync_schedules.NodeCreateScheduleCommand(self.context)
        self.assertTrue(isinstance(command, CreateScheduleCommand))
        self.assertTrue(NODE_ID_OPTION in command.options)
        self.assertTrue(MAX_BANDWIDTH_OPTION in command.options)
        self.assertTrue(MAX_CONCURRENCY_OPTION in command.options)
        self.assertEqual(command.description, sync_schedules.DESC_CREATE)
        self.assertTrue(isinstance(command.strategy, sync_schedules.NodeSyncScheduleStrategy))

    def test_delete_schedule_command(self):
        command = sync_schedules.NodeDeleteScheduleCommand(self.context)
        self.assertTrue(isinstance(command, DeleteScheduleCommand))
        self.assertTrue(NODE_ID_OPTION in command.options)
        self.assertEqual(command.description, sync_schedules.DESC_DELETE)
        self.assertTrue(isinstance(command.strategy, sync_schedules.NodeSyncScheduleStrategy))

    def test_update_schedule_command(self):
        command = sync_schedules.NodeUpdateScheduleCommand(self.context)
        self.assertTrue(isinstance(command, UpdateScheduleCommand))
        self.assertTrue(NODE_ID_OPTION in command.options)
        self.assertEqual(command.description, sync_schedules.DESC_UPDATE)
        self.assertTrue(isinstance(command.strategy, sync_schedules.NodeSyncScheduleStrategy))

    def test_next_run_command(self):
        command = sync_schedules.NodeNextRunCommand(self.context)
        self.assertTrue(isinstance(command, NextRunCommand))
        self.assertTrue(NODE_ID_OPTION in command.options)
        self.assertEqual(command.description, sync_schedules.DESC_NEXT_RUN)
        self.assertTrue(isinstance(command.strategy, sync_schedules.NodeSyncScheduleStrategy))


class NodeSyncScheduleStrategyTests(unittest.TestCase):

    def setUp(self):
        super(NodeSyncScheduleStrategyTests, self).setUp()
        self.context = mock.MagicMock()
        self.api = mock.MagicMock()

        self.strategy = sync_schedules.NodeSyncScheduleStrategy(self.context)
        self.strategy.api = self.api

    def test_create(self):
        # Test
        schedule = '1900-01-01'
        failure_threshold = 5
        enabled = True
        kwargs = {
            NODE_ID_OPTION.keyword: NODE_ID,
            MAX_BANDWIDTH_OPTION.keyword: MAX_BANDWIDTH,
            MAX_CONCURRENCY_OPTION.keyword: MAX_CONCURRENCY
        }
        self.strategy.create_schedule(schedule, failure_threshold, enabled, kwargs)

        # Verify
        expected_units = [dict(type_id='node', unit_key=None)]
        options = {
            constants.MAX_DOWNLOAD_BANDWIDTH_KEYWORD: MAX_BANDWIDTH,
            constants.MAX_DOWNLOAD_CONCURRENCY_KEYWORD: MAX_CONCURRENCY,
        }
        self.api.add_schedule.assert_called_once_with(
            sync_schedules.SYNC_OPERATION,
            NODE_ID,
            schedule,
            expected_units,
            failure_threshold,
            enabled,
            options)

    def test_delete(self):
        # Test
        schedule_id = 'abcdef'
        kwargs = {sync_schedules.NODE_ID_OPTION.keyword : NODE_ID}
        self.strategy.delete_schedule(schedule_id, kwargs)

        # Verify
        self.api.delete_schedule.assert_called_once_with(sync_schedules.SYNC_OPERATION,
                                                         NODE_ID, schedule_id)

    def test_retrieve(self):
        # Test
        kwargs = {sync_schedules.NODE_ID_OPTION.keyword : NODE_ID}
        self.strategy.retrieve_schedules(kwargs)

        # Verify
        self.api.list_schedules.assert_called_once_with(sync_schedules.SYNC_OPERATION, NODE_ID)

    def test_update(self):
        # Test
        schedule_id = 'abcdef'
        kwargs = {sync_schedules.NODE_ID_OPTION.keyword : NODE_ID, 'extra' : 'e'}
        self.strategy.update_schedule(schedule_id, **kwargs)

        # Verify
        self.api.update_schedule.assert_called_once_with(sync_schedules.SYNC_OPERATION,
                                                         NODE_ID, schedule_id,
                                                         **{'extra' : 'e'})
