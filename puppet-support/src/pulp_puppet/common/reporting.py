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
Contains methods related to formatting the progress reports sent back to Pulp
by all of the puppet plugins.
"""

import traceback


def strip_none(report):
    """
    Removes all keys whose values are None. Returns a new report; does not
    edit the existing report.

    :return: new dictionary without any keys whose value was None
    :rtype:  dict
    """
    clean = dict([(k, v) for k, v in report.items() if v is not None])
    return clean


def format_exception(e):
    """
    Formats the given exception to be included in the report.

    :return: string representtion of the exception
    :rtype:  str
    """
    return str(e)


def format_traceback(tb):
    """
    Formats the given traceback to be included in the report.

    :return: string representation of the traceback
    :rtype:  str
    """
    if tb:
        return traceback.extract_tb(tb)
    else:
        return None
