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

from gettext import gettext as _

from pulp.common import dateutils

def positive_int_validator(x):
    """
    Validates that the input is a positive integer. This call will raise
    an exception to be passed to the CLI framework if it is invalid; there is
    no return otherwise.

    :param x: input value to be validated
    :type  x: int
    """
    if int(x) <= 0:
        raise ValueError(_('value must be greater than 0'))


def non_negative_int_validator(x):
    """
    Validates that the input is a non-negative integer. This call will raise
    an exception to be passed to the CLI framework if it is invalid; there is
    no return otherwise.

    :param x: input value to be validated
    :type  x: int
    """
    if int(x) < 0:
        raise ValueError(_('value must not be negative'))


def interval_iso6801_validator(x):
    """
    Validates that a user-entered value is a correct iso8601 date with
    an interval. This call will raise an exception to be passed to the CLI
    framework if it is invalid; there is no return otherwise.

    :param x: input value to be validated
    :type  x: str
    """

    # These are meant to be used with okaara which expects either ValueError or
    # TypeError for a graceful failure, so catch any parsing errors and raise
    # the appropriate new error.
    try:
        dateutils.parse_iso8601_interval(x)
    except Exception:
        raise ValueError(_('value must be a valid iso8601 string with an interval'))
