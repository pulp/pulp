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

from pulp.server.auth.authorization import READ
from pulp.server.db.model.criteria import Criteria
import pulp.server.exceptions as exceptions
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required


class SearchController(JSONController):
    def __init__(self, query_method):
        """
        @param query_method:    method that will be used for the search
        @type  query_method:    any method that takes one argument of type
                                Criteria
        """
        super(SearchController, self).__init__()
        self.query_method = query_method

    @auth_required(READ)
    def POST(self):
        """
        Searches based on a Criteria object. Requires a posted parameter
        'criteria' which has a data structure that can be turned into a
        Criteria instance.

        @param criteria:    Required. data structure that can be turned into
                            an instance of the Criteria model.
        @type  criteria:    dict

        @param importers:   Optional. iff evaluates to True, will include
                            each repo's related importers on the 'importers'
                            attribute.
        @type  imports:     bool

        @param distributors:    Optional. iff evaluates to True, will include
                                each repo's related distributors on the
                                'importers' attribute.
        @type  distributors:    bool

        @return:    list of matching repositories
        @rtype:     list
        """

        return self.ok(self._get_query_results())

    def _get_query_results(self):
        """
        Looks for a Criteria passed as a POST parameter on ket 'criteria', and
        returns the results of a search based on that Criteria.

        @return:    list of documents from the DB that match the given criteria
                    for the collection associated with this controller
        @rtype:     list
        """
        try:
            criteria_param = self.params()['criteria']
        except KeyError:
            raise exceptions.MissingValue(['criteria'])
        criteria = Criteria.from_json_doc(criteria_param)
        return list(self.query_method(criteria))