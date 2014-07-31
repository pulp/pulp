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

from web.webapi import BadRequest

from pulp.server import exceptions as pulp_exceptions
from pulp.server.auth import authorization
from pulp.server.db.model.consumer import ConsumerGroup
from pulp.server.db.model.criteria import Criteria
from pulp.server.exceptions import MissingResource, InvalidValue
from pulp.server.managers import factory as managers_factory
from pulp.server.managers.consumer.group.cud import bind, unbind
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


class ConsumerGroupResource(JSONController):

    @auth_required(authorization.READ)
    def GET(self, consumer_group_id):
        collection = ConsumerGroup.get_collection()
        group = collection.find_one({'id': consumer_group_id})
        if group is None:
            raise pulp_exceptions.MissingResource(consumer_group=consumer_group_id)
        group.update(serialization.link.current_link_obj())
        return self.ok(group)

    @auth_required(authorization.DELETE)
    def DELETE(self, consumer_group_id):
        manager = managers_factory.consumer_group_manager()
        result = manager.delete_consumer_group(consumer_group_id)
        return self.ok(result)

    @auth_required(authorization.UPDATE)
    def PUT(self, consumer_group_id):
        update_data = self.params()
        manager = managers_factory.consumer_group_manager()
        group = manager.update_consumer_group(consumer_group_id, **update_data)
        group.update(serialization.link.current_link_obj())
        return self.ok(group)


class ConsumerGroupAssociateAction(JSONController):

    @auth_required(authorization.EXECUTE)
    def POST(self, consumer_group_id):
        criteria = Criteria.from_client_input(self.params().get('criteria', {}))
        manager = managers_factory.consumer_group_manager()
        manager.associate(consumer_group_id, criteria)
        query_manager = managers_factory.consumer_group_query_manager()
        group = query_manager.get_group(consumer_group_id)
        return self.ok(group['consumer_ids'])


class ConsumerGroupUnassociateAction(JSONController):

    @auth_required(authorization.EXECUTE)
    def POST(self, consumer_group_id):
        criteria = Criteria.from_client_input(self.params().get('criteria', {}))
        manager = managers_factory.consumer_group_manager()
        manager.unassociate(consumer_group_id, criteria)
        query_manager = managers_factory.consumer_group_query_manager()
        group = query_manager.get_group(consumer_group_id)
        return self.ok(group['consumer_ids'])


class ConsumerGroupContentAction(JSONController):

    @auth_required(authorization.CREATE)
    def POST(self, consumer_group_id, action):
        """
        Content actions.
        """
        method = getattr(self, action, None)
        if method:
            return method(consumer_group_id)
        else:
            raise BadRequest()

    def install(self, consumer_group_id):
        """
        Install content (units) on the consumers in a consumer group.
        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of install options.
        @param consumer_group_id: A consumer group ID.
        @type consumer_group_id: str
        @return: list of call requests
        @rtype: list
        """
        body = self.params()
        units = body.get('units')
        options = body.get('options')
        task = managers_factory.consumer_group_manager().install_content(consumer_group_id,
                                                                         units, options)
        raise pulp_exceptions.OperationPostponed(task)

    def update(self, consumer_group_id):
        """
        Update content (units) on the consumer in a consumer group.
        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of update options.
        @param consumer_group_id: A consumer group ID.
        @type consumer_group_id: str
        @return: list of call requests
        @rtype: list
        """
        body = self.params()
        units = body.get('units')
        options = body.get('options')
        task = managers_factory.consumer_group_manager().update_content(consumer_group_id,
                                                                        units, options)
        raise pulp_exceptions.OperationPostponed(task)

    def uninstall(self, consumer_group_id):
        """
        Uninstall content (units) from the consumers in a consumer group.
        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of uninstall options.
        @param consumer_group_id: A consumer group ID.
        @type consumer_group_id: str
        @return: list of call requests
        @rtype: list
        """
        body = self.params()
        units = body.get('units')
        options = body.get('options')
        task = managers_factory.consumer_group_manager().uninstall_content(consumer_group_id,
                                                                           units, options)
        raise pulp_exceptions.OperationPostponed(task)


class ConsumerGroupBindings(JSONController):

    @auth_required(authorization.CREATE)
    def POST(self, group_id):
        """
        Create a bind association between the consumers belonging to the given
        consumer group by id included in the URL path and a repo-distributor
        specified in the POST body: {repo_id:<str>, distributor_id:<str>}.
        Designed to be idempotent so only MissingResource is expected to
        be raised by manager.

        :param group_id: The consumer group to bind.
        :type group_id: str
        :return: list of call requests
        :rtype: list
        """
        body = self.params()
        repo_id = body.get('repo_id')
        distributor_id = body.get('distributor_id')
        binding_config = body.get('binding_config', None)
        options = body.get('options', {})
        notify_agent = body.get('notify_agent', True)

        missing_resources = verify_group_resources(group_id, repo_id, distributor_id)
        if missing_resources:
            if 'group_id' in missing_resources:
                raise MissingResource(**missing_resources)
            else:
                raise InvalidValue(list(missing_resources))

        bind_args_tuple = (group_id, repo_id, distributor_id, notify_agent, binding_config,
                           options)
        async_task = bind.apply_async(bind_args_tuple)
        raise pulp_exceptions.OperationPostponed(async_task)


class ConsumerGroupBinding(JSONController):
    """
    Represents a specific consumer group binding.
    """

    @auth_required(authorization.DELETE)
    def DELETE(self, group_id, repo_id, distributor_id):
        """
        Delete a bind association between the consumers belonging to the specified
        consumer group and repo-distributor. Designed to be idempotent.

        :param group_id: A consumer group ID.
        :type group_id: str
        :param repo_id: A repo ID.
        :type repo_id: str
        :param distributor_id: A distributor ID.
        :type distributor_id: str
        :return: list of call requests
        :rtype: list
        """
        missing_resources = verify_group_resources(group_id, repo_id, distributor_id)
        if missing_resources:
            raise MissingResource(**missing_resources)

        unbind_args_tuple = (group_id, repo_id, distributor_id, {})
        async_task = unbind.apply_async(unbind_args_tuple)
        raise pulp_exceptions.OperationPostponed(async_task)


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

# web.py application -----------------------------------------------------------

_URLS = ('/$', ConsumerGroupCollection,
         '/search/$', ConsumerGroupSearch, # resource search
         '/([^/]+)/$', ConsumerGroupResource,

        '/([^/]+)/bindings/$', ConsumerGroupBindings,
        '/([^/]+)/bindings/([^/]+)/([^/]+)/$', ConsumerGroupBinding,

         '/([^/]+)/actions/associate/$', ConsumerGroupAssociateAction,
         '/([^/]+)/actions/unassociate/$', ConsumerGroupUnassociateAction,
         '/([^/]+)/actions/content/(install|update|uninstall)/$',
            ConsumerGroupContentAction,
        )

application = web.application(_URLS, globals())
