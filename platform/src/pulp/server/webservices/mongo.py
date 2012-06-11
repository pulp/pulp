# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
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
Mongo utility module to help pulp web services deal with the mongo db.
"""

import re

from pulp.server.exceptions import PulpException


class MalformedFilters(PulpException):
    pass


def filters_to_re_spec(filters):
    """
    @type filters: dict of str: list
    @param filters: http request query parameters
    @return: dict of field: regex of possible str values
    """
    if not filters:
        return None
    return dict((k, re.compile('(%s)' % '|'.join(v))) for k,v in filters.items())


def filters_to_set_spec(filters, intersect=(), union=()):
    """
    Build a find spec document based on the filters and intersect and union
    operation specifiers passed in.
    @type filters: dict
    @param filters: dictionary of query paramaters and associated list of values
    @type intersect: tuple or list
    @param intersect: list of parameters that are using the intersection operation
    @type union: tuple or list
    @param union: list of parameters that are usiong the union operation
    @rtype: dict
    @return: mongo spec document
    """
    spec = {}
    for param, values in filters.items():
        if len(values) == 1:
            spec[param] = values[0]
        else:
            if param in intersect:
                spec[param] = {'$all': values}
            elif param in union:
                spec[param] = {'$in': values}
            else:
                raise MalformedFilters('Multiple values specified for %s, but _intersect or _union operation not specified' % param)
    return spec
