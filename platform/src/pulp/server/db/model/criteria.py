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

    # XXX currently commented out so that we can get indexing right *before*
    # storing them in the db - jconnor (2012-07-23)
    #collection_name = 'criteria'

    def __init__(self, filters=None, sort=None, limit=None, skip=None, fields=None):
        super(Criteria, self).__init__()

        assert isinstance(filters, (dict, NoneType))
        assert isinstance(sort, (list, tuple, NoneType))
        assert isinstance(limit, (int, NoneType))
        assert isinstance(skip, (int, NoneType))
        assert isinstance(fields, (list, tuple, NoneType))

        self.filters = filters
        self.sort = sort
        self.limit = limit
        self.skip = skip
        self.fields = fields

    def as_dict(self):
        """
        @return:    the Criteria as a dict, suitable for serialization by
                    something like JSON, and compatible as input to the
                    from_client_input method.
        @rtype:     dict
        """
        return {
            'filters' : self.filters,
            'sort' : self.sort,
            'limit' : self.limit,
            'skip' : self.skip,
            'fields' : self.fields
        }

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
        if not isinstance(doc, dict):
            raise pulp_exceptions.InvalidValue(['criteria']), None, sys.exc_info()[2]

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
        spec = copy.copy(self.filters)
        _compile_regexs_for_not(spec)
        return spec


class UnitAssociationCriteria(Model):

    # Shadowed here for convenience
    SORT_ASCENDING = pymongo.ASCENDING
    SORT_DESCENDING = pymongo.DESCENDING

    def __init__(self, type_ids=None, association_filters=None, unit_filters=None,
                 association_sort=None, unit_sort=None, limit=None, skip=None,
                 association_fields=None, unit_fields=None, remove_duplicates=False):
        """
        There are a number of entry points into creating one of these instances:
        multiple REST interfaces, the plugins, etc. As such, this constructor
        does quite a bit of validation on the parameter values.

        @param type_ids: list of types to search
        @type  type_ids: [str]

        @param association_filters: mongo spec describing search parameters on
               association metadata
        @type  association_filters: dict

        @param unit_filters: mongo spec describing search parameters on unit
               metadata; only used when a single type ID is specified
        @type  unit_filters: dict

        @param association_sort: ordered list of fields and directions; may only
               contain association metadata
        @type  association_sort: [(str, <SORT_* constant>)]

        @param unit_sort: ordered list of fields and directions; only used when
               a single type ID is specified
        @type  unit_sort: [(str, <SORT_* constant>)]

        @param limit: maximum number of results to return
        @type  limit: int

        @param skip: number of results to skip
        @type  skip: int

        @param association_fields: if specified, only the given fields from the
               association's metadata will be included in returned units
        @type  association_fields: list of str

        @param unit_fields: if specified, only the given fields from the unit's
               metadata are returned; only applies when a single type ID is
               specified
        @type  unit_fields: list of str

        @param remove_duplicates: if True, units with multiple associations will
               only return a single association; defaults to False
        @type  remove_duplicates: bool
        """
        super(UnitAssociationCriteria, self).__init__()

        # A default instance will be used in the case where no criteria is
        # passed in, so use sane defaults here.

        if type_ids is not None and  not isinstance(type_ids, (list, tuple)):
            type_ids = [type_ids]
        self.type_ids = type_ids

        self.association_filters = association_filters or {}
        self.unit_filters = unit_filters or {}

        self.association_sort = association_sort
        self.unit_sort = unit_sort

        self.limit = limit
        self.skip = skip

        # The unit_id and unit_type_id are required as association returned data;
        # frankly it doesn't make sense without them but it's also a technical
        # requirement for the algorithm to run. Make sure they are there.
        if association_fields is not None:
            if 'unit_id' not in association_fields: association_fields.append('unit_id')
            if 'unit_type_id' not in association_fields: association_fields.append('unit_type_id')

        self.association_fields = association_fields
        self.unit_fields = unit_fields

        self.remove_duplicates = remove_duplicates

    @classmethod
    def from_client_input(cls, query):
        """
        Parses a unit association query document and assembles a corresponding
        internal criteria object.

        Example:
        {
          "type_ids" : ["rpm"],
          "filters" : {
            "unit" : <mongo spec syntax>,
            "association" : <mongo spec syntax>
          },
          "sort" : {
            "unit" : [ ["name", "ascending"], ["version", "descending"] ],
            "association" : [ ["created", "descending"] ]
          },
          "limit" : 100,
          "skip" : 200,
          "fields" : {
            "unit" : ["name", "version", "arch"],
            "association" : ["created"]
          },
          "remove_duplicates" : True
        }

        @param query: user-provided query details
        @type  query: dict

        @return: criteria object for the unit association query
        @rtype:  L{UnitAssociationCriteria}

        @raises ValueError: on an invalid value in the query
        """
        query = copy.copy(query)

        type_ids = query.pop('type_ids', None)

        filters = query.pop('filters', None)
        if filters is None:
            association_filters = None
            unit_filters = None
        else:
            association_filters = _validate_filters(filters.pop('association', None))
            unit_filters = _validate_filters(filters.pop('unit', None))

        sort = query.pop('sort', None)
        if sort is None:
            association_sort = None
            unit_sort = None
        else:
            association_sort = _validate_sort(sort.pop('association', None))
            unit_sort = _validate_sort(sort.pop('unit', None))

        limit = _validate_limit(query.pop('limit', None))
        skip = _validate_skip(query.pop('skip', None))

        fields = query.pop('fields', None)
        if fields is None:
            association_fields = None
            unit_fields = None
        else:
            association_fields = _validate_fields(fields.pop('association', None))
            unit_fields = _validate_fields(fields.pop('unit', None))

        remove_duplicates = bool(query.pop('remove_duplicates', False))

        # report any superfluous doc key, value pairs as errors
        for d in (query, filters, sort, fields):
            if not d:
                continue
            raise pulp_exceptions.InvalidValue(d.keys())

        # XXX these are here for "backward compatibility", in the future, these
        # should be removed and the corresponding association_spec and unit_spec
        # properties should be used
        if association_filters:
            _compile_regexs_for_not(association_filters)
        if unit_filters:
            _compile_regexs_for_not(unit_filters)

        return cls(type_ids, association_filters, unit_filters, association_sort,
                   unit_sort, limit, skip, association_fields, unit_fields, remove_duplicates)

    @property
    def association_spec(self):
        if self.association_filters is None:
            return None
        association_spec = copy.copy(self.association_filters)
        _compile_regexs_for_not(association_spec)
        return association_spec

    @property
    def unit_spec(self):
        if self.unit_filters is None:
            return None
        unit_spec = copy.copy(self.unit_filters)
        _compile_regexs_for_not(unit_spec)
        return unit_spec

    def __str__(self):
        s = ''
        if self.type_ids: s += 'Type IDs [%s] ' % self.type_ids
        if self.association_filters: s += 'Assoc Filters [%s] ' % self.association_filters
        if self.unit_filters is not None: s += 'Unit Filters [%s] ' % self.unit_filters
        if self.association_sort is not None: s += 'Assoc Sort [%s] ' % self.association_sort
        if self.unit_sort is not None: s += 'Unit Sort [%s] ' % self.unit_sort
        if self.limit: s += 'Limit [%s] ' % self.limit
        if self.skip: s += 'Skip [%s] ' % self.skip
        if self.association_fields: s += 'Assoc Fields [%s] ' % self.association_fields
        if self.unit_fields: s += 'Unit Fields [%s] ' % self.unit_fields
        s += 'Remove Duplicates [%s]' % self.remove_duplicates
        return s

# validation helper functions --------------------------------------------------

def _validate_filters(filters):
    if filters is None:
        return None
    if not isinstance(filters, dict):
        raise pulp_exceptions.InvalidValue(['filters'])
    return filters


def _validate_sort(sort):
    """
    @type  sort:    list, tuple

    @rtype: tuple
    """
    if sort is None:
        return None
    if not isinstance(sort, (list, tuple)):
        raise pulp_exceptions.InvalidValue(['sort']), None, sys.exc_info()[2]
    try:
        valid_sort = []
        for entry in sort:
            if not isinstance(entry[0], basestring):
                raise TypeError('Invalid field name [%s]' % str(entry[0]))
            flag = str(entry[1]).lower()
            direction = None
            if flag in ('ascending', '1'):
                direction = pymongo.ASCENDING
            if flag in ('descending', '-1'):
                direction = pymongo.DESCENDING
            if direction is None:
                raise ValueError('Invalid sort direction [%s]' % flag)
            valid_sort.append((entry[0], direction))
    except (TypeError, ValueError):
       raise pulp_exceptions.InvalidValue(['sort']), None, sys.exc_info()[2]
    else:
        return valid_sort


def _validate_limit(limit):
    if isinstance(limit, bool):
        raise pulp_exceptions.InvalidValue(['limit']), None, sys.exc_info()[2]
    if limit is None:
        return None
    try:
        limit = int(limit)
        if limit < 1:
            raise TypeError()
    except (TypeError, ValueError):
        raise pulp_exceptions.InvalidValue(['limit']), None, sys.exc_info()[2]
    else:
        return limit


def _validate_skip(skip):
    if isinstance(skip, bool):
        raise pulp_exceptions.InvalidValue(['skip']), None, sys.exc_info()[2]
    if skip is None:
        return None
    try:
        skip = int(skip)
        if skip < 0:
            raise TypeError()
    except (TypeError, ValueError):
        raise pulp_exceptions.InvalidValue(['skip']), None, sys.exc_info()[2]
    else:
        return skip


def _validate_fields(fields):
    if fields is None:
        return None
    try:
        if isinstance(fields, (basestring, dict)):
            raise TypeError
        fields = list(fields)
        for f in fields:
            if not isinstance(f, basestring):
                raise TypeError()
    except TypeError:
        raise pulp_exceptions.InvalidValue(['fields']), None, sys.exc_info()[2]
    return fields


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

