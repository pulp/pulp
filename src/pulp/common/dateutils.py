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

"""
Common utilities for date and time representation for Pulp.
"""

import datetime
import re
import time

#import dateutil.tz
import isodate

# common globals ---------------------------------------------------------------

_one_hour = datetime.timedelta(hour=1)

_iso8601_delim = re.compile(r'(--|/)')
_iso8601_recurrences = re.compile(r'^R(?P<num>\d+)$')

# timezone functions -----------------------------------------------------------

def local_tz():
    """
    Get the local timezone.
    @rtype: datetime.tzinfo instance
    @return: a tzinfo instance representing the local timezone
    """
    return isodate.LOCAL
    #return dateutil.tz.gettz()


def utc_tz():
    """
    Get the UTC timezone.
    @rtype: datetime.tzinfo instance
    @return: a tzinfo instance representing the utc timezone
    """
    return isodate.UTC
    #return dateutil.tz.tzutc()


def is_local_dst():
    """
    Figure it's daylight savings time.
    @rtype: bool or None
    @return: True if it's daylight savings time, False if it's not,
             or None if it can't be figured
    """
    flag = time.localtime()[-1]
    if flag < 0:
        return None
    return bool(flag)


def local_dst_delta():
    """
    Return the difference in time for daylight savings time.
    @rtype: datetime.timedelta instance
    @return: a timedelta instance reprenting the difference between the local
             standard time and the current time
    """
    now = datetime.datetime.now(local_tz())
    return now.dst()


def local_utcoffset_delta():
    """
    Return the difference in time between the local time and utc time.
    @rtype: datetime.timedelta instance
    @return: a timedelta instance representing the difference between the local
             time and the utc time
    """
    now = datetime.datetime.now(local_tz())
    return now.utcoffset()


def to_local_datetime(dt):
    """
    Convert the passed in time to the local timezone.
    If the passed in time has no timezone information associated with it, it is
    assumed to be in the local timezone.
    @type dt: datetime.datetime instance
    @param dt: datetime instance representing the time to be converted
    @rtype: datetime.datetime instance
    @return: datetime instance reprenting the passed in time, converted to the
             local timezone
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=local_tz())
    return dt.astimezone(local_tz())


def to_utc_datetime(dt):
    """
    Convert the passed in time to the utc timezone.
    If the passed in time has no timezone information associated with it, it is
    assumed to be in the local timezone.
    @type dt: datetime.datetime instance
    @param dt: datetime instance representing the time to be converted
    @rtype: datetime.datetime instance
    @return: datetime instance reprenting the passed in time, converted to the
             utc timezone
    """
    if dt.tzinfo is None:
        dt = to_local_datetime(dt)
    return dt.astimezone(utc_tz())

# is8601 functions -------------------------------------------------------------

def parse_iso8601_datetime(datetime_str):
    """
    Parse an iso8601 datetime string.
    @type datetime_str: str
    @param datetime_str: iso8601 datetime string to parse
    @rtype: datetime.datetime instance
    """
    return isodate.parse_datetime(datetime_str)


def parse_iso8601_interval(interval_str):
    """
    Parse an iso8601 time interval string.
    @type interval_str: str
    @param interval_str: iso8601 time interval string to parse
    @rtype: tuple of (int or None, datetime.datetime or None, datetime.timedelta)
    @return: a tuple of the number of recurrences of the interval or None if not
             present, the starting time of the interval or None if not present,
             and the length of the interval
    """
    parts = _iso8601_delim.split(interval_str)
    interval = None
    start_time = None
    iterations = None
    for p in parts:
        match = _iso8601_recurrences.match(p)
        if match is not None:
            iterations = int(match.group('num'))
        elif p.startswith('P'):
            interval = isodate.parse_duration(p)
        else:
            start_time = parse_iso8601_datetime(p)
    if isinstance(iterations, isodate.Duration):
        if start_time is None:
            raise Exception('NO!')
        iterations = iterations.todatetime(start=start_time)
    return (interval, start_time, iterations)


def format_iso8601_datetime(dt):
    """
    Format a datetime instance as an iso8601 string.
    @type dt: datetime.datetime instance
    @param dt: datetime instance to format
    @rtype: str
    @return: iso8601 representation of the passed in datetime instance
    """
    return isodate.strftime(dt, isodate.DATE_BAS_COMPLETE)


def format_iso8601_interval(interval, start_time=None, recurrences=None):
    """
    Format a time interval as an iso8601 string.
    @type interval: datetime.timedelta instance
    @param interval: length of the interval
    @type start_time: datetime.datetime instance or None
    @param start_time: (optional) start time of the interval
    @type recurrences: int
    @param recurrences: (optional) number of times intercal recures
    @rtype: str
    @return: iso8601 representaion of the passed in time interval
    """
    parts = []
    if recurrences is not None:
        parts.append('R%d' % recurrences)
    if start_time is not None:
        parts.append(to_iso8601_datetime(start_time))
    parts.append(isodate.strftime(interval, isodate.D_DEFAULT))
    return '/'.join(parts)