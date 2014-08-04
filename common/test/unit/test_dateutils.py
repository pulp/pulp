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

import datetime
import unittest
import isodate

from pulp.common import dateutils


# test timezones and timezone conversions
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

    def test_utc_no_tz_to_utz_tz_conversion(self):
        dt = datetime.datetime.utcnow()
        new_date = dateutils.to_utc_datetime(dt, no_tz_equals_local_tz=False)
        self.assertEquals(new_date.tzinfo, dateutils.utc_tz())

    def test_utc_offset(self):
        n1 = datetime.datetime.now(dateutils.local_tz())
        u1 = dateutils.to_utc_datetime(n1)
        n2 = n1.replace(tzinfo=None)
        u2 = u1.replace(tzinfo=None)
        self.assertTrue(n2 - u2 == dateutils.local_utcoffset_delta())


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


class TestParseDatetimeOrDate(unittest.TestCase):
    def test_value_error(self):
        # I know, this isn't actually a ValueError, but it should be!
        self.assertRaises(isodate.ISO8601Error, dateutils.parse_iso8601_datetime_or_date, 'abc')

    def test_type_error(self):
        self.assertRaises(TypeError, dateutils.parse_iso8601_datetime_or_date, 123)

    def test_invalid_date(self):
        self.assertRaises(isodate.ISO8601Error, dateutils.parse_iso8601_datetime_or_date, '2012-15-90')

    def test_date(self):
        ret = dateutils.parse_iso8601_datetime_or_date('2012-03-15')
        self.assertTrue(isinstance(ret, datetime.datetime))

    def test_datetime(self):
        ret = dateutils.parse_iso8601_datetime_or_date('2012-07-31T09:43:15')
        self.assertTrue(isinstance(ret, datetime.datetime))


class TestFormatting(unittest.TestCase):

    def test_formatting_utc_timestamp(self):
        dt = datetime.datetime(2012, 10, 24, 10, 20, tzinfo=dateutils.utc_tz())
        ts = dateutils.datetime_to_utc_timestamp(dt)
        formatted = dateutils.format_iso8601_utc_timestamp(ts)
        self.assertEqual(formatted, '2012-10-24T10:20:00Z')


class DatetimeMathTests(unittest.TestCase):

    def test_add_timedelta(self):
        dt = datetime.datetime(2012, 10, 24)
        td = datetime.timedelta(days=8)

        result_1 = dateutils.add_interval_to_datetime(td, dt)
        result_2 = dt + td
        self.assertEqual(result_1, result_2)

    def test_add_duration(self):
        dt = datetime.datetime(2012, 10, 31)
        dr = isodate.Duration(months=1)

        result = dateutils.add_interval_to_datetime(dr, dt)
        self.assertEqual(result.month, 11)
        self.assertEqual(result.day, 30)


class TestNowDateTimeWithTzInfo(unittest.TestCase):

    def test_create_datetime(self):

        comparator = datetime.datetime.now(tz=dateutils.utc_tz())
        result = dateutils.now_utc_datetime_with_tzinfo()
        self.assertTrue(hasattr(result, 'tzinfo'))
        self.assertEquals(result.tzinfo, dateutils.utc_tz())
        self.assertTrue(result >= comparator)
