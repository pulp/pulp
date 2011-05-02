#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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

import datetime
import os
import sys
import time
import types
import unittest

srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import testutil

testutil.load_test_config()

from pulp.common import dateutils

# test timezones and timezone conversions --------------------------------------

_zero = datetime.timedelta(0)
_one_hour = datetime.timedelta(hour=1)


class _StdZone(datetime.tzinfo):

    def __init__(self, utc_offset=0):
        self.utc_offset = utc_offset

    def dst(self, dt):
        return _zero

    def fromutc(self, dt):
        return dt + self.utcoffset()

    def tzname(self, dt):
        return 'UTC %d' % self.utc_offset

    def utcoffset(self, dt):
        return datetime.timedelta(minutes=(self.utc_offset * 60)) - self.dst()


class _DayZone(datetime.tzinfo):

    def __init__(self, utc_offset=0):
        self.utc_offset = utc_offset

    def dst(self, dt):
        return _one_hour

    def fromutc(self, dt):
        return dt + self.utcoffset()

    def tzname(self, dt):
        return 'UTC %d' % self.utc_offset

    def utcoffset(self, dt):
        return datetime.timedelta(minutes=(self.utc_offset * 60)) - self.dst()


class TimezoneTester(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

# test iso8601 support ---------------------------------------------------------

class ISO8601Tester(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

# ------------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()