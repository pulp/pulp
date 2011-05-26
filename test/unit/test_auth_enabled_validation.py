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
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import mocks
from pulp.repo_auth import auth_enabled_validation
import testutil


# -- test cases ----------------------------------------------------------------------

class TestValidateCertBundle(unittest.TestCase):

    def setUp(self):
        mocks.install()
        override_file = os.path.abspath(os.path.dirname(__file__)) + '/../common/test-override-repoauth.conf'
        auth_enabled_validation.CONFIG_FILENAME = override_file

    def test_enabled(self):
        '''
        Tests that running the validation when repo auth is enabled indicates
        that the user is not yet authenticated.
        '''

        # Test
        result = auth_enabled_validation.authenticate(None)

        # Verify
        self.assertTrue(not result)
