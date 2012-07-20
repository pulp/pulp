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

from ConfigParser import SafeConfigParser
import logging
import os
import mock
import okaara
import shutil
import unittest

from pulp.bindings.bindings import Bindings
from pulp.bindings.server import PulpConnection
from pulp.client.extensions.core import PulpCli, ClientContext, PulpPrompt
from pulp.client.extensions.exceptions import ExceptionHandler
from pulp.common.config import Config
from pulp.server import config
from pulp.server.db import connection
from pulp.server.logs import start_logging, stop_logging

class PulpRPMTests(unittest.TestCase):
    """
    Base unit test class for all rpm synchronization related unit tests.
    """

    @classmethod
    def setUpClass(cls):
        stop_logging()
        config_filename = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'test-override-pulp.conf')
        config.config.read(config_filename)
        start_logging()
        connection.initialize()

    def setUp(self):
        super(PulpRPMTests, self).setUp()

    def simulate_sync(self, repo, src):
        # Simulate a repo sync, copy the source contents to the repo.working_dir
        dst = os.path.join(repo.working_dir, repo.id)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

class PulpClientTests(unittest.TestCase):
    """
    Base unit test class for all extension unit tests.
    """

    def setUp(self):
        super(PulpClientTests, self).setUp()

        self.config = SafeConfigParser()
        config_filename = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'test-override-client.conf')
        self.config = Config(config_filename)

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
