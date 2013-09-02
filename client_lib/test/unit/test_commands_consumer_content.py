# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import unittest

import mock

from pulp.bindings.responses import Task, STATE_FINISHED
from pulp.client.commands.consumer import content as consumer_content
from pulp.client.commands.options import OPTION_CONSUMER_ID
from pulp.client.commands.polling import PollingCommand
from pulp.devel.unit import base
from pulp.devel.unit.task_simulator import TaskSimulator
from pulp.server.compat import json


class InstantiationTests(unittest.TestCase):

    def setUp(self):
        self.mock_context = mock.MagicMock()
        self.action = 'action'

    def tearDown(self):
        self.mock_context = mock.MagicMock()

    def test_content_section(self):
        try:
            consumer_content.ConsumerContentSection(self.mock_context)
        except Exception, e:
            self.fail(str(e))

    def test_install_section(self):
        try:
            consumer_content.ConsumerContentInstallSection(self.mock_context)
        except Exception, e:
            self.fail(str(e))

    def test_install_command(self):
        try:
            consumer_content.ConsumerContentInstallCommand(self.mock_context)
        except Exception, e:
            self.fail(str(e))

    def test_update_section(self):
        try:
            consumer_content.ConsumerContentUpdateSection(self.mock_context)
        except Exception, e:
            self.fail(str(e))

    def test_update_command(self):
        try:
            consumer_content.ConsumerContentUpdateCommand(self.mock_context)
        except Exception, e:
            self.fail(str(e))

    def test_uninstall_section(self):
        try:
            consumer_content.ConsumerContentUninstallSection(self.mock_context)
        except Exception, e:
            self.fail(str(e))

    def test_uninstall_command(self):
        try:
            consumer_content.ConsumerContentUninstallCommand(self.mock_context)
        except Exception, e:
            self.fail(str(e))

    def test_progress_tracker(self):
        try:
            consumer_content.ConsumerContentProgressTracker(self.mock_context.prompt)
        except Exception, e:
            self.fail(str(e))

    def test_schedules_section(self):
        try:
            consumer_content.ConsumerContentSchedulesSection(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))

    def test_list_schedule(self):
        try:
            consumer_content.ConsumerContentListScheduleCommand(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))

    def test_create_schedule(self):
        try:
            consumer_content.ConsumerContentCreateScheduleCommand(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))

    def test_delete_schedule(self):
        try:
            consumer_content.ConsumerContentDeleteScheduleCommand(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))

    def test_update_schedule(self):
        try:
            consumer_content.ConsumerContentUpdateScheduleCommand(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))

    def test_next_run(self):
        try:
            consumer_content.ConsumerContentNextRunCommand(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))

    def test_schedules_strategy(self):
        try:
            consumer_content.ConsumerContentScheduleStrategy(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))


POSTPONED_TASK = Task({'call_request_id': '1',
                       'call_request_group_id': None,
                       'call_request_tags': [],
                       'start_time': None,
                       'finish_time': None,
                       'response': 'postponed',
                       'reasons': [],
                       'state': 'waiting',
                       'progress': {},
                       'result': None,
                       'exception': None,
                       'traceback': None})


class InstallCommandTests(base.PulpClientTests):

    def setUp(self):
        super(InstallCommandTests, self).setUp()
        self.command = consumer_content.ConsumerContentInstallCommand(self.context)

    def test_structure(self):
        self.assertTrue(isinstance(self.command, PollingCommand))

        self.assertTrue(OPTION_CONSUMER_ID in self.command.options)
        self.assertTrue(consumer_content.OPTION_CONTENT_TYPE_ID in self.command.options)
        self.assertTrue(consumer_content.OPTION_CONTENT_UNIT in self.command.options)

        self.assertEqual(self.command.method, self.command.run)
        self.assertEqual(self.command.name, 'run')

    def test_run(self):
        # Setup
        sim = TaskSimulator()
        sim.install(self.bindings)

        fake_progress_report = {'steps' : [('name', 'status')], 'details' : {}}

        sim.add_task_state('1', STATE_FINISHED, progress_report=fake_progress_report)

        self.server_mock.request.return_value = 201, POSTPONED_TASK

        kwargs = {OPTION_CONSUMER_ID.keyword: 'test-consumer',
                  consumer_content.OPTION_CONTENT_TYPE_ID.keyword: 'rpm',
                  consumer_content.OPTION_CONTENT_UNIT.keyword: ['test-unit']}

        self.command.run(**kwargs)

        self.assertEqual(self.server_mock.request.call_count, 1)
        self.assertEqual(self.server_mock.request.call_args[0][0], 'POST')

        url = self.server_mock.request.call_args[0][1]

        self.assertTrue(url.find('test-consumer') > 0)

        body = json.loads(self.server_mock.request.call_args[0][2])

        self.assertEqual(body['units'], [{'type_id': 'rpm', 'unit_key': {'name': 'test-unit'}}])


class UpdateCommandTests(base.PulpClientTests):

    def setUp(self):
        super(UpdateCommandTests, self).setUp()
        self.command = consumer_content.ConsumerContentUpdateCommand(self.context)

    def test_structure(self):
        self.assertTrue(isinstance(self.command, PollingCommand))

        self.assertTrue(OPTION_CONSUMER_ID in self.command.options)
        self.assertTrue(consumer_content.OPTION_CONTENT_TYPE_ID in self.command.options)
        self.assertTrue(consumer_content.OPTION_CONTENT_UNIT in self.command.options)

        self.assertEqual(self.command.method, self.command.run)
        self.assertEqual(self.command.name, 'run')

    def test_run(self):
        # Setup
        sim = TaskSimulator()
        sim.install(self.bindings)

        fake_progress_report = {'steps' : [('name', 'status')], 'details' : {}}

        sim.add_task_state('1', STATE_FINISHED, progress_report=fake_progress_report)
        self.server_mock.request.return_value = 201, POSTPONED_TASK

        kwargs = {OPTION_CONSUMER_ID.keyword: 'test-consumer',
                  consumer_content.OPTION_CONTENT_TYPE_ID.keyword: 'rpm',
                  consumer_content.OPTION_CONTENT_UNIT.keyword: ['test-unit']}

        self.command.run(**kwargs)

        self.assertEqual(self.server_mock.request.call_count, 1)
        self.assertEqual(self.server_mock.request.call_args[0][0], 'POST')

        url = self.server_mock.request.call_args[0][1]

        self.assertTrue(url.find('test-consumer') > 0)

        body = json.loads(self.server_mock.request.call_args[0][2])

        self.assertEqual(body['units'], [{'type_id': 'rpm', 'unit_key': {'name': 'test-unit'}}])



class UnistallCommandTests(base.PulpClientTests):

    def setUp(self):
        super(UnistallCommandTests, self).setUp()
        self.command = consumer_content.ConsumerContentUninstallCommand(self.context)

    def test_structure(self):
        self.assertTrue(isinstance(self.command, PollingCommand))

        self.assertTrue(OPTION_CONSUMER_ID in self.command.options)
        self.assertTrue(consumer_content.OPTION_CONTENT_TYPE_ID in self.command.options)
        self.assertTrue(consumer_content.OPTION_CONTENT_UNIT in self.command.options)

        self.assertEqual(self.command.method, self.command.run)
        self.assertEqual(self.command.name, 'run')

    def test_run(self):
        # Setup
        sim = TaskSimulator()
        sim.install(self.bindings)

        fake_progress_report = {'steps' : [('name', 'status')], 'details' : {}}

        sim.add_task_state('1', STATE_FINISHED, progress_report=fake_progress_report)

        self.server_mock.request.return_value = 201, POSTPONED_TASK

        kwargs = {OPTION_CONSUMER_ID.keyword: 'test-consumer',
                  consumer_content.OPTION_CONTENT_TYPE_ID.keyword: 'rpm',
                  consumer_content.OPTION_CONTENT_UNIT.keyword: []}

        self.command.run(**kwargs)

        self.assertEqual(self.server_mock.request.call_count, 1)
        self.assertEqual(self.server_mock.request.call_args[0][0], 'POST')

        url = self.server_mock.request.call_args[0][1]

        self.assertTrue(url.find('test-consumer') > 0)

        body = json.loads(self.server_mock.request.call_args[0][2])

        self.assertEqual(body['units'], [])


