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

import logging
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.auth.password_util import hash_password, check_password

class TestUtil(testutil.PulpAsyncTest):

    def test_unicode_password(self):
        password = u"some password"
        hashed = hash_password(password)
        self.assertNotEqual(hashed, password)

    def test_hash_password(self):
        password = "some password"
        hashed = hash_password(password)
        self.assertNotEqual(hashed, password)
        
    def test_check_password(self):
        password = "some password"
        hashed = hash_password(password)
        self.assertTrue(check_password(hashed, password))
        
if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.INFO)
    unittest.main()
