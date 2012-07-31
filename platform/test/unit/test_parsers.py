#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest
import isodate
from pulp.client import parsers

import mock

class TestISO8601(unittest.TestCase):
    def test_type_error(self):
        self.assertRaises(TypeError, parsers.iso8601, 123)

    def test_date(self):
        ret = parsers.iso8601('2012-03-15')
        self.assertTrue(isinstance(ret, basestring))
        # make sure the returned value can be parsed
        isodate.parse_datetime(ret)

    def test_datetime(self):
        ret = parsers.iso8601('2012-03-15')
        self.assertTrue(isinstance(ret, basestring))
        # make sure the returned value can be parsed
        isodate.parse_datetime(ret)

    def test_value_error(self):
        self.assertRaises(ValueError, parsers.iso8601, 'abcde')
