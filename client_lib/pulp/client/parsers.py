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

"""
Contains methods suitable for passing to the parse_func parameter of the
option and flag client classes.
"""

from gettext import gettext as _

import isodate
from okaara.parsers import *

from pulp.client import arg_utils
from pulp.common import dateutils


# Backward compatibility for Pulp parsers that existed before Okaara's implementations
parse_nonnegative_int = parse_non_negative_int
parse_optional_nonnegative_int = parse_optional_non_negative_int
csv = parse_csv_string


# -- pulp custom parsers ------------------------------------------------------
def pulp_parse_optional_positive_int(value):
    """
    Returns an int representation of the user entered value. This call does not raise an
    exception in the event the specified value is None.

    :param value: user entered value
    :type  value: str, None
    :return: integer if a value could be parsed or an empty string if no value was provided
    :rtype: int, str
    """
    return_value = parse_optional_positive_int(value)
    if return_value is None:
        return_value = ''
    return return_value


def pulp_parse_optional_boolean(value):
    """
    Returns an boolean representation of the user entered value. This call does not raise an
    exception in the event the specified value is None.

    :param value: user entered value
    :type  value: bool, None
    :return: bool if a value could be parsed or an empty string if no value was provided
    :rtype: bool, str
    """
    return_value = parse_optional_boolean(value)
    if return_value is None:
        return_value = ''
    return return_value


def pulp_parse_optional_nonnegative_int(value):
    """
    Returns a positive int representation of the user entered value. This call does not raise an
    exception in the event the specified value is None.

    :param value: user entered value
    :type  value: str, None
    :return: integer if a value could be parsed or an empty string if no value was provided
    :rtype: int, str
    """
    return_value = parse_optional_nonnegative_int(value)
    if return_value is None:
        return_value = ''
    return return_value


def parse_notes(value):
    """
    Returns a value suitable to send to the server for a notes value on a
    repository. The given value will actually be a list of values regardless
    of whether or not the user specified multiple notes.

    :param value: list of user entered values or empty list if unspecified
    :type  value: list
    :return: dictionary representation of all user entered notes
    :rtype: dict
    """

    if value is None:
        return None

    try:
        return arg_utils.args_to_notes_dict(value)
    except arg_utils.InvalidConfig, e:
        raise ValueError(e.args[0])


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
        raise ValueError(_('invalid ISO8601 string'))


def key_csv(input):
    """
    parse a key/value pair where the value is CSV

    :param input: string in form 'key=value' where value is CSV
    :type  input: basestring
    :return: 2-member tuple in the form (key, [value1, value2])
    :rtype:  tuple
    """
    key, value = input.split('=', 1)
    return (key, csv(value))


def key_csv_multiple(input):
    """
    parse a key/value pair where the value is CSV and the option may be
    specified multiple times.

    :param input: list of values that can be passed to function "key_csv"
    :type  input: list
    :return: list of values as returned by function "key_csv"
    :rtype:  list
    """
    if input:
        return [key_csv(x) for x in input]
    else:
        return []


def key_value_multiple(input):
    """
    parse a key/value pair where the option may be specified multiple times
    :param input: list of strings in the form 'key=value'
    :type  input: list
    :return: list of 2-member lists in the form [key, value]
    :rtype:  list
    """
    if input:
        ret = [x.split('=', 1) for x in input]
        for value in ret:
            if len(value) != 2:
                raise ValueError
        return ret
    else:
        return []
