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

import logging

import web

from pulp.server.api.filter import FilterApi
from pulp.server.auth.authorization import (
    grant_automatic_permissions_for_created_resource, CREATE, READ, DELETE, EXECUTE)
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler)
from pulp.server.webservices.http import extend_uri_path, resource_path

# filters api ---------------------------------------------------------------

api = FilterApi()
_log = logging.getLogger('pulp')

# controllers -----------------------------------------------------------------

class Filters(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self):
        """
        List all available filters
        @return: a list of all filters
        """
        return self.ok(api.filters())

    @error_handler
    @auth_required(CREATE)
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


    @error_handler
    @auth_required(DELETE)
    def DELETE(self):
        """
        @return: True on successful deletion of all filters
        """
        api.clean()
        return self.ok(True)


class Filter(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self, id):
        """
        Get a filter's information
        @param id: filter id
        @return: filter details
        """
        if api.filter(id) is None:
            return self.not_found('A filter with the id, %s, does not exist'% id)
        return self.ok(api.filter(id))

    @error_handler
    @auth_required(DELETE)
    def DELETE(self, id):
        """
        Delete a filter and remove it's associations with repositories, if any
        @param id: filter id
        @return: True on successful deletion of filter
        """
        if api.filter(id) is None:
            return self.not_found('A filter with the id, %s, does not exist'% id)
        api.delete(id)
        return self.ok(True)

class FilterActions(JSONController):

    exposed_actions = (
        'add_packages',
        'remove_packages',
    )

    def add_packages(self, id):
        """
        @param id: filter id
        @return: True on successful addition of packages to filter
        """
        data = self.params()
        api.add_packages(id, data['packages'])
        return self.ok(True)

    def remove_packages(self, id):
        """
        @param id: filter id
        @return: True on successful removal of packages from filter
        """
        data = self.params()
        api.remove_packages(id, data['packages'])
        return self.ok(True)

    @error_handler
    @auth_required(EXECUTE)
    def POST(self, id, action_name):
        """
        Action dispatcher. This method checks to see if the action is exposed,
        and if so, implemented. It then calls the corresponding method (named
        the same as the action) to handle the request.
        @type id: str
        @param id: filter id
        @type action_name: str
        @param action_name: name of the action
        @return: http response
        """
        filter = api.filter(id, fields=['id'])
        if not filter:
            return self.not_found('No filter with id %s found' % id)
        action = getattr(self, action_name, None)
        if action is None:
            return self.internal_server_error('No implementation for %s found' % action_name)
        return action(id)


# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Filters',
    '/([^/]+)/$', 'Filter',

    '/([^/]+)/(%s)/$' % '|'.join(FilterActions.exposed_actions),
    'FilterActions',
)

application = web.application(URLS, globals())
