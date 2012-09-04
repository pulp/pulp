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
import logging
import unittest

import mock
import okaara

from pulp.bindings.bindings import Bindings
from pulp.bindings.server import PulpConnection
from pulp.client.extensions.core import PulpPrompt, ClientContext, PulpCli
from pulp.client.extensions.exceptions import ExceptionHandler
from pulp.common.config import Config

# Can be used by tests to simulate a task response. Be sure to copy this before
# making any changes, or better yet, use the method in ExtensionsTests.
TASK_TEMPLATE = {
    "exception": None,
    "task_group_id": 'default-group',
    "task_id": 'default-id',
    "tags": [],
    "reasons": [],
    "start_time": None,
    "traceback": None,
    "state": None,
    "finish_time": None,
    "schedule_id": None,
    "result": None,
    "progress": {},
    "response": None,
}


class ExtensionTests(unittest.TestCase):
    """
    Base unit test class for all extension unit tests.
    """

    def setUp(self):
        super(ExtensionTests, self).setUp()

        self.config = Config()

        self.server_mock = mock.Mock()
        self.pulp_connection = PulpConnection('', server_wrapper=self.server_mock)
        self.bindings = Bindings(self.pulp_connection)

        # Disabling color makes it easier to grep results since the character codes aren't there
        self.recorder = okaara.prompt.Recorder()
        self.prompt = PulpPrompt(enable_color=False, output=self.recorder, record_tags=True)

        self.logger = logging.getLogger('pulp')
        self.exception_handler = ExceptionHandler(self.prompt, self.config)

        self.context = ClientContext(self.bindings, self.config, self.logger, self.prompt, self.exception_handler)

        self.cli = PulpCli(self.context)
        self.context.cli = self.cli

    def task(self):
        """
        :return: dict that contains all of the values needed to simulate a task
                 coming back from the server
        :rtype:  dict
        """
        return copy.copy(TASK_TEMPLATE)