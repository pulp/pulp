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

from pulp.bindings.search import SearchAPI
from pulp.bindings.base import PulpAPI

class RepoGroupAPI(PulpAPI):
    """
    Connection class to access consumer specific calls
    """
    PATH = 'v2/repo_groups/'

    def repo_groups(self):
        """
        retrieve all repository groups

        :return:    all repository groups
        :rtype:     list
        """
        return self.server.GET(self.PATH)

    def create(self, id, display_name, description, notes):
        """
        Create a repository group.

        :param id:  unique primary key
        :type  id:  basestring

        :param display_name:    Human-readable name
        :type  display_name:    basestring

        :param description: text description of the repo group
        :type  description: basestring

        :param notes:   key-value pairs to programmatically tag the repository
        :type  notes:   dict

        :return:    Response object
        :rtype:     pulp.bindings.responses.Response
        """
        data = {'id': id,
                'display_name': display_name,
                'description': description,
                'notes': notes,}
        return self.server.POST(self.PATH, data)

    def repo_group(self, id):
        """
        Retrieve a single repository group

        :param id:  primary key for a repository group
        :type  id:  basestring

        :return:    Response object
        :rtype:     pulp.bindings.responses.Response
        """
        path = self.PATH + ('%s/' % id)
        return self.server.GET(path)

    def delete(self, id):
        """
        Delete a single repository group

        :param id:  primary key for a repository group
        :type  id:  basestring

        :return:    Response object
        :rtype:     pulp.bindings.responses.Response
        """
        path = self.PATH + '%s/' % id
        return self.server.DELETE(path)

    def update(self, id, delta):
        """
        Update a repository

        :param id:  primary key for a repository group
        :type  id:  basestring

        :param delta:   map of new values with attribute names as keys.
        :type  delta:   dict

        :return:    Response object
        :rtype:     pulp.bindings.responses.Response
        """
        path = self.PATH + '%s/' % id
        return self.server.PUT(path, delta)


class RepoGroupSearchAPI(SearchAPI):
    PATH = 'v2/repo_groups/search/'


class RepoGroupActionAPI(SearchAPI):
    PATH = 'v2/repo_groups/%s/actions/'

    def associate(self, id, **kwargs):
        path = self.PATH % id + 'associate/'

        filters = self._compose_filters(**kwargs)
        if filters:
            kwargs['filters'] = filters
        self._strip_criteria_kwargs(kwargs)

        response = self.server.POST(path, {'criteria':kwargs})
        return response.response_body

    def unassociate(self, id, **kwargs):
        path = self.PATH % id + 'unassociate/'
        response = self.server.POST(path, {'criteria':kwargs})
        return response.response_body

