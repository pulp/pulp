# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import copy
import re
import sys
from types import NoneType

import pymongo

from pulp.server import exceptions as pulp_exceptions
from pulp.server.db.model.base import Model

# criteria model ---------------------------------------------------------------

class Criteria(Model):

    #collection_name = 'criteria'

    def __init__(self, filters=None, sort=None, limit=None, skip=None, fields=None):
        super(Criteria, self).__init__()

        assert isinstance(filters, (dict, NoneType))
        assert isinstance(sort, (list, tuple, NoneType))
        assert isinstance(limit, (int, NoneType))
        assert isinstance(skip, (int, NoneType))
        assert isinstance(fields, (list, NoneType))

        self.filters = filters
        self.sort = sort
        self.limit = limit
        self.skip = skip
        self.fields = fields

    @classmethod
    def from_client_input(cls, doc):
        """
        Accept input provided by a client (such as through a GET or POST
        request), validate that the provided data is part of a Criteria
        definition, and ensure that no additional data is present.

        @param doc: a dict including only data that corresponds to attributes
                    of a Criteria object
        @type  doc: dict

        @return:    new Criteria instance based on provided data
        @rtype:     pulp.server.db.model.criteria.Criteria
        """
        doc = copy.copy(doc)
        filters = _validate_filters(doc.pop('filters', None))
        sort = _validate_sort(doc.pop('sort', None))
        limit = _validate_limit(doc.pop('limit', None))
        skip = _validate_skip(doc.pop('skip', None))
        fields = _validate_fields(doc.pop('fields', None))
        if doc:
            raise pulp_exceptions.InvalidValue(doc.keys())
        return cls(filters, sort, limit, skip, fields)

    @property
    def spec(self):
        if self.filters is None:
            return None

        def _compile_regexs_for_not(spec):
            if not isinstance(spec, (dict, list, tuple)):
                return
            if isinstance(spec, (list, tuple)):
                map(_compile_regexs_for_not, spec)
                return
            for key, value in spec.items():
                if key == '$not' and isinstance(value, basestring):
                    spec[key] = re.compile(value)
                _compile_regexs_for_not(value)

        spec = copy.copy(self.filters)
        _compile_regexs_for_not(spec)
        return spec

# validation helper functions --------------------------------------------------

def _validate_filters(filters):
    if filters is None:
        return None
    if not isinstance(filters, dict):
        raise pulp_exceptions.InvalidValue(['filters'])
    return filters


def _validate_sort(sort):
    if sort is None:
        return None
    try:
        valid_sort = []
        for entry in sort:
            if not isinstance(entry[0], basestring):
                raise TypeError()
            flag = str(entry[1]).lower()
            direction = None
            if flag in ('ascending', '1'):
                direction = pymongo.ASCENDING
            if flag in ('descending', '-1'):
                direction = pymongo.DESCENDING
            if direction is None:
                raise ValueError()
            valid_sort.append((entry[0], direction))
    except (TypeError, ValueError):
       raise pulp_exceptions.InvalidValue(['sort']), None, sys.exc_info()[2]
    else:
        return tuple(valid_sort)


def _validate_limit(limit):
    if limit is None:
        return None
    try:
        limit = int(limit)
        if limit < 1:
            raise TypeError()
    except TypeError:
        raise pulp_exceptions.InvalidValue(['limit']), None, sys.exc_info()[2]
    else:
        return limit


def _validate_skip(skip):
    if skip is None:
        return None
    try:
        skip = int(skip)
        if skip < 0:
            raise TypeError()
    except TypeError:
        raise pulp_exceptions.InvalidValue(['skip']), None, sys.exc_info()[2]
    else:
        return skip


def _validate_fields(fields):
    if fields is None:
        return None
    try:
        fields = list(fields)
        for f in fields:
            if not isinstance(f, basestring):
                raise TypeError()
    except TypeError:
        raise pulp_exceptions.InvalidValue(['fields']), None, sys.exc_info()[2]
    return fields

