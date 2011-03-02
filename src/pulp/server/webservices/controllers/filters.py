# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import logging

import web

from pulp.server.api.filter import FilterApi
from pulp.server.auth.authorization import (
    grant_automatic_permissions_for_created_resource, CREATE, READ, DELETE)
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.http import extend_uri_path, resource_path

# filters api ---------------------------------------------------------------

api = FilterApi()
_log = logging.getLogger('pulp')

# controllers -----------------------------------------------------------------

class Filters(JSONController):

    @JSONController.error_handler
    @JSONController.auth_required(READ)
    def GET(self):
        """
        List all available filters
        @return: a list of all filters
        """
        return self.ok(api.filters())

    @JSONController.error_handler
    @JSONController.auth_required(CREATE)
    def POST(self):
        """
        Create a new filter
        @return: filter that was created
        """
        data = self.params()

        id = data['id']
        if api.filter(id) is not None:
            return self.conflict('A filter with the id, %s, already exists' % id)

        filter = api.create(id, data['type'], description = data.get('description', None),
                                  package_list = data.get('package_list', None))
        resource = resource_path(extend_uri_path(filter['id']))
        grant_automatic_permissions_for_created_resource(resource)
        return self.created(filter['id'], filter)


    @JSONController.error_handler
    @JSONController.auth_required(DELETE)
    def DELETE(self):
        """
        @return: True on successful deletion of all filters
        """
        api.clean()
        return self.ok(True)


class filter(JSONController):

    @JSONController.error_handler
    @JSONController.auth_required(READ)
    def GET(self, id):
        """
        Get a filter's information
        @param id: filter id
        @return: filter details
        """
        return self.ok(api.filter(id))


    @JSONController.error_handler
    @JSONController.auth_required(DELETE)
    def DELETE(self, id):
        """
        Delete a filter
        @param id: id of filter to delete
        @return: True on successful deletion of filter
        """
        filter = api.filter(id)
        if filter is None:
            return self.not_found('No such filter: %s' % id)

        api.delete(id=id)
        return self.ok(True)



# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Filters',
    '/([^/]+)/$', 'Filter',
)

application = web.application(URLS, globals())
