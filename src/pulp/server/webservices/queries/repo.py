# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
Repo module containing repo queries based on HTTP query parameters.
"""

import re

from pulp.server.db.model.resource import Repo
from pulp.server.managers.repo.unit_association_query import Criteria
from pulp.server.webservices import http
from pulp.server.webservices.queries.common import OPERATION_FILTERS

def collection():
    """
    Get all of the repos in our Repo db collection, filtered by the query
    parameters.
    @return: list of repo objects
    @rtype: list [SON, ...]
    """
    # XXX implement for v2 of the api, not v1
    valid_filters = []
    valid_filters.extend(OPERATION_FILTERS)
    query_params = http.query_parameters(valid_filters)
    db_collection = Repo.get_collection()
    spec = {}
    fields = []
    db_cursor = db_collection.find(spec, fields=fields or None)


def resource(repo_id):
    """
    Get the repo object specified by the id, with fields filtered by the query
    parameters.
    @param repo_id: unique identifier for the repo
    @type repo_id: str
    @return: repo object if found, otherwise None
    @rtype: SON or None
    """
    valid_filters = ['field']
    query_param = http.query_parameters(valid_filters)
    fields = query_param.get('field', None)
    db_collection = Repo.get_collection()
    repo = db_collection.find_one({'_id': repo_id}, fields=fields)
    return repo


def subcollection_content(repo_id):
    # XXX idea placeholder
    pass


def unit_association_criteria(query):
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
    @rtype:  L{Criteria}

    @raises ValueError: on an invalid value in the query
    """

    # This is a temporary solution. We have larger needs to validate
    # the syntax and semantics of advanced queries but I don't have the time
    # to design/write it now. This is a simplified version that should
    # probably be gutted later and fed into the JSON validator when it exists.
    # jdob, Dec 19, 2011

    type_ids = query.get('type_ids', None)
    association_filters = query.get('filters', {}).get('association', None)
    unit_filters = query.get('filters', {}).get('unit', None)
    association_sort = query.get('sort', {}).get('association', None)
    unit_sort = query.get('sort', {}).get('unit', None)
    limit = query.get('limit', None)
    skip = query.get('skip', None)
    association_fields = query.get('fields', {}).get('association', None)
    unit_fields = query.get('fields', {}).get('unit', None)
    remove_duplicates = query.get('remove_duplicates', None)

    # The criteria object wants a list of tuples, so convert them and the
    # passed in value for direction to the internal representation
    def parse_sort_direction(sort_list):
        if sort_list is None:
            return None

        parsed_list = []
        for t in sort_list:
            if t[1] in ['ascending', 1, '1']:
                t[1] = Criteria.SORT_ASCENDING
            elif t[1] in ['descending', -1, '-1']:
                t[1] = Criteria.SORT_DESCENDING
            else:
                raise ValueError('Invalid sort direction [%s]' % t[1])

            parsed_list.append((t[0], t[1]))
        return parsed_list

    association_sort = parse_sort_direction(association_sort)
    unit_sort = parse_sort_direction(unit_sort)

    # Parse ints and bools
    if limit: limit = int(limit)
    if skip: skip = int(skip)
    if remove_duplicates: remove_duplicates = bool(remove_duplicates)

    # $not is not supported for regular expressions specified using the
    # {$regex: ...} syntax, so check for all $not entries and if the value
    # is a string, compile it into a native pattern and pass that in.

    if unit_filters:
        _recursive_check_not(unit_filters)

    if association_filters:
        _recursive_check_not(association_filters)

    c = Criteria(type_ids=type_ids, association_filters=association_filters, unit_filters=unit_filters,
                 association_sort=association_sort, unit_sort=unit_sort, limit=limit, skip=skip,
                 association_fields=association_fields, unit_fields=unit_fields, remove_duplicates=remove_duplicates)
    return c

def _recursive_check_not(root_dict):
    """
    Recursively checks through a nested dictionary structure looking for all
    keys that are the $not operator. If it is found and the value is a string,
    compile the string to a native regular expression and replace it in the
    dictionary.

    @param root_dict: base dictionary to strat checking
    """

    for key, value in root_dict.items():
        # Check for $not
        if key == '$not' and isinstance(value, str):
            root_dict[key] = re.compile(value)

        # Recurse if necessary
        if isinstance(value, dict):
            _recursive_check_not(value)

        if isinstance(value, (list, tuple)):
            for v in value:
                if isinstance(v, dict):
                    _recursive_check_not(v)

