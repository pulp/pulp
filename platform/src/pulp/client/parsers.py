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
import isodate

from pulp.common import dateutils

def iso8601(value):
    """
    Makes sure that an incoming ISO8601 value is formatted in the standard way
    that datetime.isoformat() does, since when we do comparisons against dates
    in mongo, the comparison is actual alphabetical order.

    :param value: ISO8601 string
    :type  value: basestring
    :return: ISO 8601 string
    :rtype:  basestring
    """
    try:
        return dateutils.parse_iso8601_datetime_or_date(value).replace(microsecond=0).isoformat()
    except isodate.ISO8601Error:
        raise ValueError('invalid ISO8601 string')
