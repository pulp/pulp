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

import web

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
    def GET(self):
        """
        Searches based on a Criteria object. Pass in each Criteria field as a
        query parameter.  For the 'fields' parameter, pass multiple fields as
        separate key-value pairs as is normal with query parameters in URLs. For
        example, '/v2/sometype/search/?fields=id&fields=display_name' will
        return the fields 'id' and 'display_name'.
        """
        return self.ok(self._get_query_results_from_get())

    @auth_required(READ)
    def POST(self):
        """
        Searches based on a Criteria object. Requires a posted parameter
        'criteria' which has a data structure that can be turned into a
        Criteria instance.

        @param criteria:    Required. data structure that can be turned into
                            an instance of the Criteria model.
        @type  criteria:    dict

        @return:    list of matching items
        @rtype:     list
        """

        return self.ok(self._get_query_results_from_post())

    def _get_query_results_from_get(self, ignore_fields=None):
        """
        Looks for query parameters that define a Criteria, and returns the
        results of a search based on that Criteria.

        @param ignore_fields:   Field names to ignore. All other fields will be
                                used in an attempt to generate a Criteria
                                instance, which will fail if unexpected field
                                names are present.
        @type  ignore_fields:   list

        @return:    list of documents from the DB that match the given criteria
                    for the collection associated with this controller
        @rtype:     list
        """
        input = web.input(field=[])
        if ignore_fields:
            for field in ignore_fields:
                input.pop(field, None)

        # rename this to 'fields' within the dict, and omit it if empty so we
        # default to getting all fields
        fields = input.pop('field')
        if fields:
            input['fields'] = fields
        criteria = Criteria.from_client_input(input)
        return list(self.query_method(criteria))

    def _get_query_results_from_post(self):
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
        criteria = Criteria.from_client_input(criteria_param)
        return list(self.query_method(criteria))