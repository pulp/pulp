# Copyright (C) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.client.extensions.loader import DEFAULT_PRIORITY, PRIORITY_VAR

def priority(value=DEFAULT_PRIORITY):
    """
    Use this to put a decorator on an "initialize" method for an extension, which
    will set that extension's priority level.

    :param value: priority value, which defaults to 5
    :type  value: int
    :return: decorator
    """
    def decorator(f):
        setattr(f, PRIORITY_VAR, value)
        return f
    return decorator
