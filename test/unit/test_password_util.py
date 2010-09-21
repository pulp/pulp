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

import logging
import os
import sys
import unittest

srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src"
sys.path.insert(0, srcdir)

from pulp.server.auth.password_util import hash_password, check_password

class TestUtil(unittest.TestCase):

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
