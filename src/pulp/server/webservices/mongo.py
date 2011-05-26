#!/usr/bin/env python
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


def filters_to_re_spec(filters):
    """
    @type filters: dict of str: list
    @param filters: http request query parameters
    @return: dict of field: regex of possible str values
    """
    if not filters:
        return None
    return dict((k, re.compile('(%s)' % '|'.join(v))) for k,v in filters.items())