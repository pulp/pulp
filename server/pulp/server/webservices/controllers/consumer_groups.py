# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import web

from pulp.server import exceptions as pulp_exceptions
from pulp.server.auth import authorization
from pulp.server.db.model.consumer import ConsumerGroup
from pulp.server.exceptions import MissingResource
from pulp.server.managers import factory as managers_factory
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.controllers.search import SearchController


# consumer group collection ----------------------------------------------------

class ConsumerGroupCollection(JSONController):

    @auth_required(authorization.READ)
    def GET(self):
        collection = ConsumerGroup.get_collection()
        cursor = collection.find({})
        groups = []
        for group in cursor:
            group.update(serialization.link.child_link_obj(group['id']))
            groups.append(group)
        return self.ok(groups)

    @auth_required(authorization.CREATE)
    def POST(self):
        group_data = self.params()
        group_id = group_data.pop('id', None)
        if group_id is None:
            raise pulp_exceptions.MissingValue(['id'])
        display_name = group_data.pop('display_name', None)
        description = group_data.pop('description', None)
        consumer_ids = group_data.pop('consumer_ids', None)
        notes = group_data.pop('notes', None)
        if group_data:
            raise pulp_exceptions.InvalidValue(group_data.keys())
        manager = managers_factory.consumer_group_manager()

        group = manager.create_consumer_group(group_id, display_name, description, consumer_ids,
                                              notes)
        group.update(serialization.link.child_link_obj(group['id']))
        return self.created(group['_href'], group)


class ConsumerGroupSearch(SearchController):
    def __init__(self):
        super(ConsumerGroupSearch, self).__init__(
            managers_factory.consumer_group_query_manager().find_by_criteria)

    def GET(self):
        items = self._get_query_results_from_get()
        for item in items:
            item.update(serialization.link.search_safe_link_obj(item['id']))
        return self.ok(items)

    def POST(self):
        items = self._get_query_results_from_post()
        for item in items:
            item.update(serialization.link.search_safe_link_obj(item['id']))
        return self.ok(items)


def verify_group_resources(group_id, repo_id, distributor_id):
    """
    Confirm the group, repository, and distributor exist

    :param group_id:        The consumer group id to verify the existence of
    :type  group_id:        str
    :param repo_id:         The repository id to confirm the existence of
    :type  repo_id:         str
    :param distributor_id:  The distributor id to confirm the existence of on the repository
    :type  distributor_id:  str

    :return: A dictionary of the missing resources
    :rtype:  dict
    """
    missing_resources = {}

    group_manager = managers_factory.consumer_group_query_manager()
    repo_manager = managers_factory.repo_query_manager()
    distributor_manager = managers_factory.repo_distributor_manager()
    try:
        group_manager.get_group(group_id)
    except MissingResource:
        missing_resources['group_id'] = group_id
    repo = repo_manager.find_by_id(repo_id)
    if repo is None:
        missing_resources['repo_id'] = repo_id
    try:
        distributor_manager.get_distributor(repo_id, distributor_id)
    except MissingResource:
        missing_resources['distributor_id'] = distributor_id

    return missing_resources


_URLS = (
    '/$', ConsumerGroupCollection,
    '/search/$', ConsumerGroupSearch,  # resource search
)

application = web.application(_URLS, globals())
