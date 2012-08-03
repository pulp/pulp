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

import csv

from okaara.cli import CommandUsage

from pulp.bindings.base import PulpAPI

class Operator(object):
    def __init__(self, mongo_name):
        """

        :param mongo_name: name of this operator in mongo syntax, such as "$in"
        :type  mongo_name: basestring
        """
        self.mongo_name = mongo_name

    @staticmethod
    def _split_arg(arg):
        """
        Split an argument into field name and value components

        :param arg: argument value passed on the command line
        :type  arg: basestring

        :return:    2-member list of field name and value
        :rtype:     list
        """
        ret = arg.split('=', 1)
        if len(ret) != 2:
            raise CommandUsage()
        return ret

    def compose_filters(self, args):
        """
        Compose a filter clause that will be used to create a mongo spec

        :param args:    list of raw values passed by the user on the command
                        line, which should be in the form "name=value"
        :type  args:    list of basestring

        :return:    list of clauses that can be combined with a "$and" operator
                    to create a mongo spec.
        """
        clauses = []
        for arg in args or []:
            try:
                field_name, value = self._split_arg(arg)
            except (TypeError, ValueError):
                raise CommandUsage
            if self.mongo_name:
                clauses.append({field_name: {self.mongo_name: value}})
            else:
                # assume a straight "equals" comparison where mongo doesn't
                # require an explicit operator
                clauses.append({field_name: value})
        return clauses


class IntOperator(Operator):
    @staticmethod
    def _split_arg(arg):
        """
        In addition to what Operator._split_arg does, this will cast the value
        to be an int
        """
        field_name, value = Operator._split_arg(arg)
        return (field_name, int(value))


class CSVOperator(Operator):
    @staticmethod
    def _split_arg(arg):
        """
        In addition to what Operator._split_arg does, this will parse the value
        portion from CSV into a list of values.
        """
        field_name, value = Operator._split_arg(arg)
        return (field_name, csv.reader((value,)).next())


class SearchAPI(PulpAPI):
    # PATH should normally be defined by a subclass
    PATH = None
    _OPERATORS = {
        'int-eq' : IntOperator(None),
        'str-eq' : Operator(None),
        'not' : Operator('$not'),
        'gt' : IntOperator('$gt'),
        'lt' : IntOperator('$lt'),
        'gte' : Operator('$gte'),
        'lte' : Operator('$lte'),
        'match' : Operator('$regex'),
        'in' : CSVOperator('$in')
    }
    _CRITERIA_ARGS = set(('filters', 'sort', 'limit', 'skip', 'fields'))
    _FILTER_ARGS = set(_OPERATORS.keys())
    _ALL_ARGS = _CRITERIA_ARGS | _FILTER_ARGS

    def search(self, **kwargs):
        """
        Performs a search against the server-side REST API. This depends on
        self.PATH being set to something valid, generally by having a subclass
        override it.

        Pass in name-based parameters only that match the values accepted by
        pulp.server.db.model.criteria.Criteria.__init__

        @return:    response body from the server
        """
        if not set(kwargs.keys()) <= self._ALL_ARGS:
            raise CommandUsage()
        filters = self._compose_filters(**kwargs)
        if filters:
            kwargs['filters'] = filters
        self._strip_criteria_kwargs(kwargs)
        response = self.server.POST(self.PATH, {'criteria':kwargs})
        return response.response_body

    def _strip_criteria_kwargs(self, kwargs):
        for field_name in kwargs.keys():
            if field_name not in self._CRITERIA_ARGS:
                del kwargs[field_name]

    @classmethod
    def _compose_filters(cls, **kwargs):
        """
        Parse all of the arguments supplied on the command line, generating a
        spec suitable for passing to mongo.

        :param kwargs:  all arguments passed on the command line as provided
                        by okaara.

        :return:    dict that is a mongo spec
        :rtype:     dict
        """
        # 'filters' overrides anything else that was supplied.
        if kwargs.get('filters', None):
            return kwargs['filters']

        clauses = []

        for operator_name in set(cls._OPERATORS.keys()) & set(kwargs.keys()):
            operator = cls._OPERATORS[operator_name]
            raw_values = kwargs[operator_name]
            clauses.extend(operator.compose_filters(raw_values))

        if len(clauses) > 1:
            return {'$and': clauses}
        elif clauses:
            return clauses[0]
        else:
            return {}
