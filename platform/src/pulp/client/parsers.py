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

import csv as csv_module

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

def csv(input):
    return csv_module.reader((input,)).next()

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
