#
# Copyright (c) 2010 Red Hat, Inc.
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

"""
Contains maintenance window classes.
"""

from pmf import *
from datetime import datetime as dt
from datetime import timedelta as delta



class Window(Envelope):
    """
    Represents a maintenance (time) window.
    An empty L{Window} defines an unbounded window.
    A I{begin} of 'None' = UTC now.
    An I{end} of 'None' = begin plus 1 hour.
    @cvar FORMAT: The datetime format. ISO 8601
    @type FORMAT: str
    @cvar DURATION: The duration keywords.
    @type DURATION: [str,..]
    """

    FORMAT = '%Y-%m-%dT%H:%M:%S'
    DURATION = ('days', 'seconds', 'minutes', 'hours', 'weeks')

    def __init__(self, *D, **window):
        """
        @param D: A (optional) dictionary.
        @type D: [dict,..]
        @note: An empty I{window} indicates an unbounded window.
        @keyword window: The window specification:
            - begin
          One of:
            - end
            - days
            - seconds
            - minutes
            - hours
            - weeks
        """
        if D:
            dict.__init__(self, *D)
            return
        if window:
            self.__setbegin(window)
            self.__setend(window)
        dict.__init__(self, **window)

    def match(self):
        """
        Get whether the current datetime (UTC) falls
        within the window.
        @note: Empty = match ALL.
        @return: True when matched.
        @rtype: bool
        """
        if self:
            now = dt.utcnow()
            begin, end = self.__dates()
            return ( now >= begin and now <= end )
        else:
            return True

    def future(self):
        """
        Get whether window is in the future.
        @note: Empty = match ALL.
        @return: True if I{begin} > I{utcnow()}.
        @rtype: bool
        """
        if self:
            now = dt.utcnow()
            begin, end = self.__dates()
            return ( now < begin )
        else:
            return False

    def past(self):
        """
        Get whether window is in the past.
        @note: Empty = match ALL.
        @return: True if I{utcnow()} > I{end}.
        @rtype: bool
        """
        if self:
            now = dt.utcnow()
            begin, end = self.__dates()
            return ( now > end )
        else:
            return False

    def __setbegin(self, window):
        """
        Set the proper window beginning.
        Performs:
          - Convert to string if L{dt} object.
          - Default to UTC (now) when value is (None).
        @param window: The window specification.
        @type window: dict
        @return: The updated I{window}.
        @rtype: dict
        """
        BEGIN = 'begin'
        if BEGIN in window:
            v = window[BEGIN]
            if not v:
                v = dt.utcnow()
            if isinstance(v, dt):
                v = v.strftime(self.FORMAT)
            window[BEGIN] = v
        else:
            raise Exception, 'Window() must specify "begin"'
        return window

    def __setend(self, window):
        """
        Set the proper window ending.
        Performs:
          - Convert to string if L{dt} object.
          - Default begin plus 1 hour when value is (None).
        @param window: The window specification.
        @type window: dict
        @return: The updated I{window}.
        @rtype: dict
        """
        END = 'end'
        if END in window:
            v = window[END]
            if not v:
                v = dt.utcnow()+delta(hours=1)
            if isinstance(v, dt):
                v = v.strftime(self.FORMAT)
            window[END] = v
        else:
            if not self.__hasduration(window):
                raise Exception,\
                    'Window() must have "end" or one of: %s' % \
                    str(self.DURATION)
        return window

    def __hasduration(self, window):
        """
        Get whether one of the duration keywords are specified
        in the I{window} definition.
        @param window: The window specification.
        @type window: dict
        @return: True if found.
        @rtype: bool
        """
        for k in self.DURATION:
            if k in window:
                return True
        return False

    def __dates(self):
        """
        Convert to datetime objects.
        @return: (begin, end)
        @rtype: (datetime, datetime)
        """
        DURATION = ('days', 'seconds', 'minutes', 'hours', 'weeks')
        if self.begin:
            begin = dt.strptime(self.begin, self.FORMAT)
        else:
            begin = dt.utcnow()
        if self.end:
            end = dt.strptime(self.begin, self.FORMAT)
        else:
            end = begin
        for k,v in self.items():
            if k in DURATION:
                end = end+delta(**{k:v})
        return (begin, end)

    def __str__(self):
        if self:
            return str(self.__dates())
        else:
            return 'Empty'


class WindowMissed(Exception):
    """
    Request window missed.
    """

    def __init__(self, sn):
        Exception.__init__(self, sn)


class WindowPending(Exception):
    """
    Request window pending.
    """

    def __init__(self, sn):
        Exception.__init__(self, sn)