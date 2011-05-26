#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import os
import sys
import unittest
import logging

srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src"
sys.path.append(srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import pulp.server.util
from pulp.server.db import connection
from pulp.server.pexceptions import PulpException

import testutil

logging.root.setLevel(logging.ERROR)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

log = logging.getLogger('pulp.test.testdatabase')

class TestDatabase(unittest.TestCase):

    def clean(self):
        testutil.common_cleanup()

    def setUp(self):
        self.config = testutil.load_test_config()

        self.data_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
        logging.root.setLevel(logging.ERROR)
        self.clean()

    def tearDown(self):
        self.clean()

    def test_database_name(self):
        self.assertEquals(connection._database.name, self.config.get("database", "name"))
