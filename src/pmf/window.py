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
    @cvar FORMAT: The datetime format. ISO 8601
    @type FORMAT: str
    @ivar begin: The window beginning datetime
    @type begin: L{dt}
    @ivar end: The window ending datetime
    @type end: L{dt}
    """

    FORMAT = '%Y-%m-%dT%H:%M:%S'

    @classmethod
    def create(cls, begin=None, **duration):
        """
        Build a window based on a beginning datetime and a duration.
        @param begin: The window beginning datetime
        @type begin: L{dt}
        @keyword duration: The diration:
          One of:
            - days
            - seconds
            - minutes
            - hours
            - weeks
        """
        begin = ( begin or dt.utcnow() )
        end = begin+delta(**duration)
        begin = begin.strftime(cls.FORMAT)
        end = end.strftime(cls.FORMAT)
        return Window(begin=begin, end=end)

    def dates(self):
        """
        Convert to datetime objects.
        @return: (begin, end)
        @rtype: (datetime, datetime)
        """
        begin = dt.strptime(self.begin, self.FORMAT)
        end = dt.strptime(self.end, self.FORMAT)
        return (begin, end)

    def match(self):
        """
        Get whether the current datetime (UTC) falls
        within the window.
        @return: True when matched.
        @rtype: bool
        """
        if not self:
            return True
        now = dt.utcnow()
        begin, end = self.dates()
        return ( now >= begin and now <= end )

    def future(self):
        """
        Get whether window is in the future.
        @return: True if I{begin} > I{utcnow()}.
        @rtype: bool
        """
        if not self:
            return False
        now = dt.utcnow()
        begin, end = self.dates()
        return ( now < begin )

    def past(self):
        """
        Get whether window is in the past.
        @return: True if I{utcnow()} > I{end}.
        @rtype: bool
        """
        if not self:
            return False
        now = dt.utcnow()
        begin, end = self.dates()
        return ( now > end )


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