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

from pulp.bindings.base import PulpAPI

class SearchAPI(PulpAPI):
    PATH = None

    def search(self, criteria):
        """
        Performs a search against the server-side REST API. This depends on
        self.PATH being set to something valid, generally by having a subclass
        override it.

        @param criteria:    Criteria to search with
        @type  criteria:    pulp.server.db.model.criteria.Criteria

        @return:    response body from the server
        """
        response = self.server.POST(self.PATH, {'criteria':criteria.as_dict()})
        return response.response_body