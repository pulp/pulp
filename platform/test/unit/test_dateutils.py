#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import datetime
import unittest

from pulp.common import dateutils

# test timezones and timezone conversions --------------------------------------

_zero = datetime.timedelta(0)
_one_hour = datetime.timedelta(hours=1)


class _StdZone(datetime.tzinfo):

    def __init__(self, utc_offset=0):
        self.utc_offset = utc_offset

    def dst(self, dt):
        return _zero

    def fromutc(self, dt):
        return dt + self.utcoffset(dt)

    def tzname(self, dt):
        return 'UTC %d' % self.utc_offset

    def utcoffset(self, dt):
        return datetime.timedelta(minutes=(self.utc_offset * 60)) - self.dst(dt)


class _DayZone(datetime.tzinfo):

    def __init__(self, utc_offset=0):
        self.utc_offset = utc_offset

    def dst(self, dt):
        return _one_hour

    def fromutc(self, dt):
        return dt + self.utcoffset(dt)

    def tzname(self, dt):
        return 'UTC %d' % self.utc_offset

    def utcoffset(self, dt):
        return datetime.timedelta(minutes=(self.utc_offset * 60)) - self.dst(dt)


class TimezoneTester(unittest.TestCase):

    def test_utc_conversion(self):
        s = datetime.datetime.now(_StdZone())
        d = s.astimezone(_DayZone())
        su = s.astimezone(dateutils.utc_tz())
        du = d.astimezone(dateutils.utc_tz())
        self.assertTrue(su == du)

    def test_local_to_utz_tz_conversion(self):
        n1 = datetime.datetime.now(dateutils.local_tz())
        u = dateutils.to_utc_datetime(n1)
        n2 = dateutils.to_local_datetime(u)
        self.assertTrue(n1 == n2)

    def test_utc_offset(self):
        n1 = datetime.datetime.now(dateutils.local_tz())
        u1 = dateutils.to_utc_datetime(n1)
        n2 = n1.replace(tzinfo=None)
        u2 = u1.replace(tzinfo=None)
        self.assertTrue(n2 - u2 == dateutils.local_utcoffset_delta())

# test iso8601 support ---------------------------------------------------------

class ISO8601Tester(unittest.TestCase):

    def setUp(self):
        self.dt_fields = ('year', 'month', 'day', 'hour', 'minute', 'second')

    def test_datetime_sans_tz(self):
        n = datetime.datetime.now()
        s = dateutils.format_iso8601_datetime(n)
        b = dateutils.parse_iso8601_datetime(s)
        for f in self.dt_fields:
            self.assertTrue(getattr(n, f) == getattr(b, f), 'Field mismatch: %s' % f)

    def test_datetime_with_tz(self):
        n = datetime.datetime.now(dateutils.local_tz())
        s = dateutils.format_iso8601_datetime(n)
        b = dateutils.parse_iso8601_datetime(s)
        for f in self.dt_fields:
            self.assertTrue(getattr(n, f) == getattr(b, f), 'Field mismatch: %s' % f)

    def test_interval(self):
        d = datetime.timedelta(hours=1)
        s = dateutils.format_iso8601_interval(d)
        i, t, r = dateutils.parse_iso8601_interval(s)
        self.assertTrue(d == i)

    def test_interval_recurrences(self):
        d = datetime.timedelta(hours=4, minutes=2, seconds=59)
        c = 4
        s = dateutils.format_iso8601_interval(d, recurrences=c)
        i, t, r = dateutils.parse_iso8601_interval(s)
        self.assertEqual(d, i)
        self.assertEqual(c, r)

    def test_interval_start_time(self):
        d = datetime.timedelta(minutes=2)
        t = datetime.datetime(year=2014, month=11, day=5, hour=0, minute=23)
        s = dateutils.format_iso8601_interval(d, t)
        i, e, r = dateutils.parse_iso8601_interval(s)
        self.assertEqual(d, i)
        self.assertEqual(t, e)

    def test_interval_full(self):
        i1 = datetime.timedelta(hours=100)
        t1 = datetime.datetime(year=2, month=6, day=20, hour=2, minute=22, second=46)
        r1 = 5
        s = dateutils.format_iso8601_interval(i1, t1, r1)
        i2, t2, r2 = dateutils.parse_iso8601_interval(s)
        self.assertEqual(i1, i2)
        self.assertEqual(t1, t2)
        self.assertEqual(r1, r2)
