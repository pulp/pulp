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

import mock

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
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
        self.mock(self.role_api, "_getcollection")
        self.mock(self.role_api, "role")
        self.role_api.role.return_value = None
        role_name = "testrole"
        self.role_api.create(role_name)
        self.assertTrue(1, self.role_api.collection.insert.call_count)
        call_args = self.role_api.collection.insert.call_args[0]
        self.assertTrue(isinstance(call_args[0], Role))
        self.assertTrue("testrole", call_args[0]["name"])
