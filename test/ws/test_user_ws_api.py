#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import sys
import os

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../unit/'
sys.path.insert(0, commondir)

from pulp.client.connection import UserConnection
from test_users import TestUsers
import testutil

class RemoteTestUsers(TestUsers):
    """
    This class subclasses TestApi and overrides the API handlers to actually
    use the same classes the CLI uses.  This ensures we are using the API exactly
    like we are when we call the pulp python API directly.
    
    The overridden testcases in this class indicate tests that *dont* pass yet.
    """

    def setUp(self):
        d = dict(host='localhost', port=443, username="admin", password="admin")
        self.config = testutil.load_test_config()
        self.uapi = UserConnection(**d)

    def tearDown(self):
        testutil.common_cleanup()
