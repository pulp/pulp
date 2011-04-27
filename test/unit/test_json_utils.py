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

# Python
from datetime import datetime
import sys
import os
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.client import json_utils


class JsonUtilsTest(unittest.TestCase):

    def test_parse_iso_date(self):
        '''
        Parses an ISO formatted date.
        BZ: 700122
        '''

        # Setup
        iso_date_string = '2011-04-27T13:34:56'

        # Test
        parsed = json_utils.parse_iso_date(iso_date_string)

        # Verify
        self.assertTrue(parsed is not None)
        self.assertTrue(isinstance(parsed, datetime))

        self.assertEqual(2011, parsed.year)
        self.assertEqual(4, parsed.month)
        self.assertEqual(27, parsed.day)
        self.assertEqual(13, parsed.hour)
        self.assertEqual(34, parsed.minute)
        self.assertEqual(56, parsed.second)
