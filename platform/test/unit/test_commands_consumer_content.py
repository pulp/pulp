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

from pulp.client.commands.consumer import content as consumer_content


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
            consumer_content.ConsumerContentSchedulesStrategy(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))

