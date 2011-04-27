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
_iso8601_recurrences = re.compile(r'R(?P<num>\d+)')

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
    flag = time.localtime()[-1]
    if flag < 0:
        return None
    return bool(flag)


def local_dst_delta():
    now = datetime.datetime.now(local_tz())
    return now.dst()


def local_utcoffset_delta():
    now = datetime.datetime.now(local_tz())
    return now.utcoffset()


def to_local_datetime(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=local_tz())
    return dt.astimezone(local_tz())


def to_utc_datetime(dt):
    if dt.tzinfo is None:
        dt = to_local_datetime(dt)
    return dt.astimezone(utc_tz())

# is8601 functions -------------------------------------------------------------

def parse_iso8601_datetime(datetime_str):
    return isodate.parse_datetime(datetime_str)


def parse_iso8601_interval(interval_str):
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


def to_iso8601_datetime(dt):
    return isodate.strftime(dt, isodate.DATE_BAS_COMPLETE)


def to_iso8601_interval(interval, start_time=None, iterations=None):
    parts = []
    if iterations is not None:
        parts.append('R%d' % iterations)
    if start_time is not None:
        parts.append(to_iso8601_datetime(start_time))
    parts.append(isodate.strftime(interval, isodate.D_DEFAULT))
    return '/'.join(parts)