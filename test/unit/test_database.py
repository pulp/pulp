#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
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
