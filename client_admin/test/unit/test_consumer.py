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

from pulp.client.commands.consumer.manage import ConsumerUnregisterCommand, ConsumerUpdateCommand
from pulp.client.commands.consumer.query import ConsumerListCommand,\
    ConsumerSearchCommand, ConsumerHistoryCommand

import base_builtins

from pulp.client.admin import consumer


class TestStructure(base_builtins.PulpClientTests):

    def setUp(self):
        super(TestStructure, self).setUp()
        consumer.initialize(self.context)
        self.consumer_section = self.context.cli.find_section(consumer.SECTION_ROOT)

    def test_structure(self):
        self.assertTrue(self.consumer_section is not None)
        self.assertTrue(ConsumerListCommand(self.context).name in self.consumer_section.commands)
        self.assertTrue(ConsumerSearchCommand(self.context).name in self.consumer_section.commands)
        self.assertTrue(ConsumerHistoryCommand(self.context).name in self.consumer_section.commands)
        self.assertTrue(ConsumerUpdateCommand(self.context).name in self.consumer_section.commands)
        self.assertTrue(ConsumerUnregisterCommand(self.context).name in \
                        self.consumer_section.commands)
