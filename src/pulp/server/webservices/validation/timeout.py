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

from gettext import gettext as _

from isodate import Duration

from pulp.common.dateutils import parse_iso8601_duration
from pulp.server.exceptions import PulpDataException


class UnsupportedTimeoutInterval(PulpDataException):
    """
    Raised when a timeout has months or years specified in it.
    """
    # TODO override __unicode__
    pass


def iso8601_duration_to_timeout(duration_str):
    """
    Convert an iso8601 duration string into a datetime.timedelta instance.
    @param duration_str: iso8601 duration string
    @type duration_str: str
    @return: timedelta corresponding to the duration string
    @rtype: datetime.timedelta instance
    @raise UnsupportedTimeoutInterval: if the duration string contains months or years
    """
    timeout = parse_iso8601_duration(duration_str)
    if isinstance(timeout, Duration):
        msg = _('Timeouts specifying months or years are not supported %(d)s')
        raise UnsupportedTimeoutInterval(msg % {'d': duration_str})
    return timeout
