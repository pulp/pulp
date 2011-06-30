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

# Python
import sys
import os

import dingus

sys.path.insert(0, "../common")
import testutil

from pulp.server.db.model import Role

class TestRoleApi(testutil.PulpTest):
    
    def test_create(self):
        role_name = "testrole"
        self.role_api.create(role_name)
        roles = self.role_api.collection.find()
        self.assertEquals(1, roles.count())
        self.assertEquals("testrole", roles[0]["name"])

    def test_create_mock_db(self):
        self.role_api._getcollection = dingus.Dingus()
        self.role_api.role = dingus.Dingus()
        self.role_api.role.return_value = None
        role_name = "testrole"
        self.role_api.create(role_name)
        self.assertTrue(1, len(self.role_api.collection.insert.calls))
        callArgs = self.role_api.collection.insert.calls[0][1]
        self.assertTrue(isinstance(callArgs[0], Role))
        self.assertTrue("testrole", callArgs[0]["name"])
