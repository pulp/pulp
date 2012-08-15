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

"""
Utilities for testing downloader implementations.
"""

import mock
import os
import shutil
import tempfile
import unittest

from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository

from pulp_puppet.common import model

class BaseDownloaderTests(unittest.TestCase):

    def setUp(self):
        self.working_dir = tempfile.mkdtemp(prefix='downloader-tests')
        self.repo = Repository('test-repo', working_dir=self.working_dir)

        self.config = PluginCallConfiguration({}, {})

        self.mock_cancelled_callback = mock.MagicMock().is_cancelled
        self.mock_cancelled_callback.return_value = False

        self.mock_progress_report = mock.MagicMock()

        self.author = 'jdob'
        self.name = 'valid'
        self.version = '1.1.0'
        self.module = model.Module(self.name, self.version, self.author)

    def tearDown(self):
        if os.path.exists(self.working_dir):
            shutil.rmtree(self.working_dir)
