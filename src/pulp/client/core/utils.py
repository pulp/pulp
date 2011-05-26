# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import sys
from gettext import gettext as _

import isodate

from pulp.common import dateutils

# output formatting ------------------------------------------------------------

_header_width = 45
_header_border = '+------------------------------------------+'

def print_header(*lines):
    """
    Print a fancy header to stdout.
    @type lines: list str's
    @param lines: headers, passed in as positional arguments, to be displayed
    """
    padding = 0
    print _header_border
    for line in lines:
        if len(line) < _header_width:
            padding = ((_header_width - len(line)) / 2) - 1
        print ' ' * padding, line
    print _header_border

# schedule option parsing ------------------------------------------------------

def parse_interval_schedule(interval, start, runs):
    """
    Parse an interval schedule, handling all the corner cases.
    Generally used for parsing recurring sync schedules.
    @type interval: str
    @param interval: time duration in iso8601 format
    @type start: str
    @param start: combined date time information in iso8601 format
    @type runs: str
    @param runs: integer number of runs as a string
    @rtype: None or str
    @return: None if no schedule was specified or an interval schedule in
             iso8601 interval format otherwise
    """
    if interval is None:
        if start is not None:
            system_exit(os.EX_USAGE, _('Interval required if start specified'))
        if runs is not None:
            system_exit(os.EX_USAGE, _('Interval required if runs specified'))
        return None
    try:
        if runs is not None:
            runs = int(runs)
    except ValueError:
        system_exit(os.EX_USAGE, _('Runs must me an integer'))
    try:
        interval = dateutils.parse_iso8601_duration(interval)
        if start is not None:
            start = dateutils.parse_iso8601_datetime(start)
        schedule = dateutils.format_iso8601_interval(interval, start, runs)
        return schedule
    except isodate.ISO8601Error, e:
        system_exit(os.EX_USAGE, e.args[0])


def parse_at_schedule(start):
    """
    Validate an "at" schedule, handling all the corner cases.
    Generally used for parsing install schedules.
    @type start: str
    @param start: combined date time information in iso8601 format
    @rtype: str
    @return: validated combined date time information in iso8601 format
    """
    if start is None:
        return None
    try:
        dateutils.parse_iso8601_datetime(start)
        return start
    except isodate.ISO8601Error, e:
        system_exit(os.EX_USAGE, e.args[0])

# system exit ------------------------------------------------------------------

def system_exit(code, msgs=None):
    """
    Exit with a code and optional message(s). Saves a few lines of code.
    @type code: int
    @param code: code to return
    @type msgs: str or list or tuple of str's
    @param msgs: messages to display
    """
    assert msgs is None or isinstance(msgs, (basestring, list, tuple))
    if msgs:
        if isinstance(msgs, basestring):
            msgs = (msgs,)
        if code == os.EX_OK:
            out = sys.stdout
        else:
            out = sys.stderr
        #out = sys.stdout if code == os.EX_OK else sys.stderr
        for msg in msgs:
            print >> out, msg
    sys.exit(code)

