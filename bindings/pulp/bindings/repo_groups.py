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
from pulp.common.plugins import distributor_constants


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

    def create_and_configure(self, group_id, display_name, description, notes, distributors=None):
        """
        Calls the server-side aggregate method for creating a repository group and adding distributors
        in a single transaction. If an error occurs during the distributor step, all effects on the
        server from this call will be deleted.

        This call has the same effect as calling:
        * RepoGroupAPI.create
        * RepoGroupDistributorAPI.create (for each distributor passed in)

        The distributor list is optional in this call. If it is not included, this behaves like
        RepoGroupAPI.create

        :param group_id: The group id
        :type group_id: str
        :param display_name: The user-friendly name of the group
        :type display_name: str
        :param description: A user-friendly description of the group
        :type description: str
        :param notes: key-value pairs to programmatically tag the repository
        :type notes: dict
        :param distributors: list of dictionaries containing distributor_type_id, repo_plugin_config, and
                distributor_id
        :type distributors: list of dict
        :return: The server response. The response body contains the created repo group.
        :rtype: pulp.bindings.responses.Response
        """
        data = {
            'id': group_id,
            'display_name': display_name,
            'description': description,
            'notes': notes,
            'distributors': distributors,
        }
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


class RepoGroupDistributorAPI(PulpAPI):
    """
    This class is a collection of methods to interact with the group distributors on the pulp server
    """
    PATH = 'v2/repo_groups/%s/distributors/'

    def distributors(self, group_id):
        """
        Get a list of the distributors associated with a group id

        :param group_id: group id to retrieve the distributors for
        :type group_id: str
        :return: The server response. The response body contains a list of dictionaries, where each
            dictionary represents a distributor
        :rtype: pulp.bindings.responses.Response
        """
        path = self.PATH % group_id
        return self.server.GET(path)

    def create(self, group_id, distributor_type_id, distributor_config, distributor_id=None):
        """
        Create a repository group

        :param group_id: The group id to use for the new repository group
        :type group_id: str
        :param distributor_type_id: Type of distributor to add to the group. This must reference one
                of the installed group distributors
        :type distributor_type_id: str
        :param distributor_config: configuration to use for the distributor on this group
        :type distributor_config: dict
        :param distributor_id: if specified, the newly added distributor will be referenced by this
                value and the group id; if it is omitted one will be generated by the manager.
        :type distributor_id: str
        :return: The server response.
        :rtype: pulp.bindings.responses.Response
        """
        path = self.PATH % group_id
        data = {
            distributor_constants.DISTRIBUTOR_TYPE_ID_KEY: distributor_type_id,
            distributor_constants.DISTRIBUTOR_CONFIG_KEY: distributor_config,
            distributor_constants.DISTRIBUTOR_ID_KEY: distributor_id,
        }
        return self.server.POST(path, data)

    def distributor(self, group_id, distributor_id):
        """
        Retrieve a specific distributor that is associated with a group. If it does not exist, a
        MissingResource exception will be raised.

        :param group_id: The group id to retrieve the distributor for
        :type group_id: str
        :param distributor_id: The distributor id to retrieve
        :type distributor_id: str
        :return: The server response. The response body contains the distributor dict.
        :rtype: pulp.bindings.responses.Response
        """
        path = self.PATH % group_id + distributor_id + '/'
        return self.server.GET(path)

    def delete(self, group_id, distributor_id):
        """
        Delete the distributor with the given distributor id if it is associated with the given group id

        :param group_id: The group id to retrieve the distributor for
        :type group_id: str
        :param distributor_id: The distributor id to retrieve
        :type distributor_id: str
        :return: The server response with a null response body
        :rtype: pulp.bindings.responses.Response
        """
        path = self.PATH % group_id + distributor_id + '/'
        return self.server.DELETE(path)

    def update(self, group_id, distributor_id, distributor_config):
        """
        Update the the distributor associated with the given group with a new configuration dict

        :param group_id: The group id to retrieve the distributor for
        :type group_id: str
        :param distributor_id: The distributor id to retrieve
        :type distributor_id: str
        :param distributor_config: The new distributor configuration
        :type distributor_config: dict
        :return: The server response
        :rtype: pulp.bindings.responses.Response
        """
        path = self.PATH % group_id + distributor_id + '/'
        return self.server.PUT(path, distributor_config)


class RepoGroupSearchAPI(SearchAPI):
    PATH = 'v2/repo_groups/search/'


class RepoGroupActionAPI(SearchAPI):
    PATH = 'v2/repo_groups/%s/actions/'

    def associate(self, id, **kwargs):
        path = self.PATH % id + 'associate/'

        filters = self.compose_filters(**kwargs)
        if filters:
            kwargs['filters'] = filters
        self._strip_criteria_kwargs(kwargs)

        response = self.server.POST(path, {'criteria':kwargs})
        return response.response_body

    def unassociate(self, id, **kwargs):
        path = self.PATH % id + 'unassociate/'

        filters = self.compose_filters(**kwargs)
        if filters:
            kwargs['filters'] = filters
        self._strip_criteria_kwargs(kwargs)

        response = self.server.POST(path, {'criteria':kwargs})
        return response.response_body

    def publish(self, group_id, distributor_id, override_config):
        """
        Publish a repository group using the given distributor

        :param group_id: The group id to retrieve the distributor for
        :type group_id: str
        :param distributor_id: The distributor id to retrieve
        :type distributor_id: str
        :param override_config: An override configuration dictionary. This is used to override the saved
            configuration for the distributor and is not saved between calls.
        :return: The server response
        :rtype: pulp.bindings.responses.Response
        """
        path = self.PATH % group_id + 'publish/'
        data = {'id': distributor_id, 'override_config': override_config}
        return self.server.POST(path, data)
