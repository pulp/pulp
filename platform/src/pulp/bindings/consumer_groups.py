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

class ConsumerGroupAPI(PulpAPI):
    """
    Connection class to access consumer group specific calls
    """
    PATH = 'v2/consumer_groups/'

    def consumer_groups(self):
        """
        retrieve all consumer groups

        :return:    all consumer groups
        :rtype:     list
        """
        return self.server.GET(self.PATH)

    def create(self, consumer_group_id, display_name, description, notes):
        """
        Create a consumer group.

        :param consumer_group_id:  unique primary key
        :type  consumer_group_id:  basestring

        :param display_name:    Human-readable name
        :type  display_name:    basestring

        :param description: text description of the consumer group
        :type  description: basestring

        :param notes:   key-value pairs to programmatically tag the consumer
        :type  notes:   dict

        :return:    Response object
        :rtype:     pulp.bindings.responses.Response
        """
        data = {'id': consumer_group_id,
                'display_name': display_name,
                'description': description,
                'notes': notes,}
        return self.server.POST(self.PATH, data)

    def consumer_group(self, consumer_group_id):
        """
        Retrieve a single consumer group

        :param consumer_group_id:  primary key for a consumer group
        :type  consumer_group_id:  basestring

        :return:    Response object
        :rtype:     pulp.bindings.responses.Response
        """
        path = self.PATH + ('%s/' % consumer_group_id)
        return self.server.GET(path)

    def delete(self, consumer_group_id):
        """
        Delete a single consumer group

        :param consumer_group_id:  primary key for a consumer group
        :type  consumer_group_id:  basestring

        :return:    Response object
        :rtype:     pulp.bindings.responses.Response
        """
        path = self.PATH + '%s/' % consumer_group_id
        return self.server.DELETE(path)

    def update(self, consumer_group_id, delta):
        """
        Update a consumer group

        :param consumer_group_id:  primary key for a consumer group
        :type  consumer_group_id:  basestring

        :param delta:   map of new values with attribute names as keys.
        :type  delta:   dict

        :return:    Response object
        :rtype:     pulp.bindings.responses.Response
        """
        path = self.PATH + '%s/' % consumer_group_id
        return self.server.PUT(path, delta)


class ConsumerGroupSearchAPI(SearchAPI):
    """
    Consumer Group searching.
    """

    PATH = 'v2/consumer_groups/search/'

class ConsumerGroupActionAPI(SearchAPI):
    """
    Consumer Group Actions.
    """

    PATH = 'v2/consumer_groups/%s/actions/'

    def associate(self, consumer_group_id, **kwargs):
        """
        Associate a set of consumers with a consumer group.

        :param consumer_group_id:  primary key for a consumer group
        :type  consumer_group_id:  basestring

        :param kwargs: name based parameters that match the values accepted by
            pulp.server.db.model.criteria.Criteria.__init__
        :type kwargs: dict

        :return: Response body
        :rtype: basestring
        """
        path = self.PATH % (consumer_group_id) + 'associate/'

        filters = self._compose_filters(**kwargs)
        if filters:
            kwargs['filters'] = filters
        self._strip_criteria_kwargs(kwargs)

        response = self.server.POST(path, {'criteria':kwargs})
        return response.response_body

    def unassociate(self, consumer_group_id, **kwargs):
        """
        Unassociate a set of consumers with a consumer group.

        :param consumer_group_id:  primary key for a consumer group
        :type  consumer_group_id:  basestring

        :param kwargs: name based parameters that match the values accepted by
            pulp.server.db.model.criteria.Criteria.__init__
        :type kwargs: dict

        :return: Response body
        :rtype: basestring
        """
        path = self.PATH % (consumer_group_id) + 'unassociate/'

        filters = self._compose_filters(**kwargs)
        if filters:
            kwargs['filters'] = filters
        self._strip_criteria_kwargs(kwargs)

        response = self.server.POST(path, {'criteria':kwargs})
        return response.response_body

class ConsumerGroupBindAPI(PulpAPI):
    """
    Consumer Group bind operations
    """

    PATH = 'v2/consumer_groups/%s/bindings/'

    def bind(self, consumer_group_id, repo_id, distributor_id):
        """
        Bind a consumer group to a distributor associated with a repository.
        Each consumer in the consumer group will be bound.

        :param consumer_group_id:  primary key for a consumer group
        :type  consumer_group_id:  basestring

        :param repo_id: repository id
        :type repo_id: basestring

        :param distributor_id: distributor id
        :type distributor_id: basestring
        """
        path = self.PATH % (consumer_group_id)
        data = {'repo_id' : repo_id, 'distributor_id' : distributor_id}
        response = self.server.POST(path, data)
        return response

    def unbind(self, consumer_group_id, repo_id, distributor_id):
        """
        Unbind a consumer group to a distributor associated with a repository.
        Each consumer in the consumer group will be unbound.

        :param consumer_group_id:  primary key for a consumer group
        :type  consumer_group_id:  basestring

        :param repo_id: repository id
        :type repo_id: basestring

        :param distributor_id: distributor id
        :type distributor_id: basestring
        """
        path = self.PATH % (consumer_group_id) + '%s/%s/' % (repo_id, distributor_id)
        response = self.server.DELETE(path)
        return response


class ConsumerGroupContentAPI(PulpAPI):
    """
    Consumer Group content operations
    """

    PATH = 'v2/consumer_groups/%s/actions/content/'

    def install(self, consumer_group_id, units, options):
        path = self.PATH % consumer_group_id + 'install/'
        data = {"units": units,
                "options": options,}
        return self.server.POST(path, data)

    def update(self, consumer_group_id, units, options):
        path = self.PATH % consumer_group_id + 'update/'
        data = {"units": units,
                "options": options,}
        return self.server.POST(path, data)

    def uninstall(self, consumer_group_id, units, options):
        path = self.PATH % consumer_group_id + 'uninstall/'
        data = {"units": units,
                "options": options,}
        return self.server.POST(path, data)


