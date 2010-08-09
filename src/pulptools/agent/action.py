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
Action slass for pulp agent.
"""

from datetime import datetime as dt
from datetime import timedelta
from logging import getLogger

log = getLogger(__name__)



def action(**interval):
    def decorator(cls):
        Action.actions.append((cls, interval))
        return cls
    return decorator


class Action:
    """
    Abstract recurring action (base).
    @keyword interval: The run interval.
      One of:
        - days
        - seconds
        - minutes
        - hours
        - weeks
    @ivar last: The last run timestamp.
    @type last: datetime
    """
    
    actions = []

    def __init__(self, **interval):
        """
        @param interval: The run interval (minutes).
        @type interval: timedelta
        """
        for k,v in interval.items():
            interval[k] = int(v)
        self.interval = timedelta(**interval)
        self.last = dt(1900, 1, 1)

    def perform(self):
        """
        Perform action.
        This MUST be overridden by subclasses.
        """
        pass # override

    def name(self):
        """
        Get action name.  Default to class name.
        @return: The action name.
        @rtype: str
        """
        return self.__class__.__name__

    def __call__(self):
        try:
            next = self.last+self.interval
            now = dt.utcnow()
            if next < now:
                self.last = now
                log.info('perform "%s"', self.name())
                self.perform()
        except Exception, e:
            log.exception(e)
