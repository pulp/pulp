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

import base

from pulp.server.managers import factory as manager_factory

class PasswordManagerTests(base.PulpServerTests):
    def setUp(self):
        super(PasswordManagerTests, self).setUp()
        self.password_manager = manager_factory.password_manager()

    def test_unicode_password(self):
        password = u"some password"
        hashed = self.password_manager.hash_password(password)
        self.assertNotEqual(hashed, password)

    def test_hash_password(self):
        password = "some password"
        hashed = self.password_manager.hash_password(password)
        self.assertNotEqual(hashed, password)
        
    def test_check_password(self):
        password = "some password"
        hashed = self.password_manager.hash_password(password)
        self.assertTrue(self.password_manager.check_password(hashed, password))
