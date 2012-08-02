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

from pulp.common.tags import action_tag, resource_tag
from pulp.server import config as pulp_config
from pulp.server import exceptions as pulp_exceptions
from pulp.server.auth import authorization
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.repo_group import RepoGroup
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.exceptions import MissingValue
from pulp.server.managers import factory as managers_factory
from pulp.server.webservices import execution, serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.controllers.search import SearchController

# repo group collection --------------------------------------------------------

class RepoGroupCollection(JSONController):

    @auth_required(authorization.READ)
    def GET(self):
        collection = RepoGroup.get_collection()
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
        repo_ids = group_data.pop('repo_ids', None)
        notes = group_data.pop('notes', None)
        if group_data:
            raise pulp_exceptions.InvalidValue(group_data.keys())
        manager = managers_factory.repo_group_manager()
        weight = pulp_config.config.getint('tasks', 'create_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, group_id)]
        call_request = CallRequest(manager.create_repo_group,
                                   [group_id, display_name, description, repo_ids, notes],
                                   weight=weight,
                                   tags=tags)
        call_request.creates_resource(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, group_id)
        group = execution.execute_sync(call_request)
        group.update(serialization.link.child_link_obj(group['id']))
        return self.created(group['_href'], group)


class RepoGroupSearch(SearchController):
    def __init__(self):
        super(RepoGroupSearch, self).__init__(
            managers_factory.repo_group_query_manager().find_by_criteria)

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

# repo group resource ----------------------------------------------------------

class RepoGroupResource(JSONController):

    @auth_required(authorization.READ)
    def GET(self, repo_group_id):
        collection = RepoGroup.get_collection()
        group = collection.find_one({'id': repo_group_id})
        if group is None:
            raise pulp_exceptions.MissingResource(repo_group=repo_group_id)
        group.update(serialization.link.current_link_obj())
        return self.ok(group)

    @auth_required(authorization.DELETE)
    def DELETE(self, repo_group_id):
        manager = managers_factory.repo_group_manager()
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id)]
        call_request = CallRequest(manager.delete_repo_group,
                                   [repo_group_id],
                                   tags=tags)
        call_request.deletes_resource(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id)
        return execution.execute_ok(self, call_request)

    @auth_required(authorization.UPDATE)
    def PUT(self, repo_group_id):
        update_data = self.params()
        manager = managers_factory.repo_group_manager()
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id)]
        call_request = CallRequest(manager.update_repo_group,
                                   args=[repo_group_id],
                                   kwargs=update_data,
                                   tags=tags)
        call_request.updates_resource(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id)
        group = execution.execute(call_request)
        group.update(serialization.link.current_link_obj())
        return self.ok(group)

# repo group membership -------------------------------------------------------

class RepoGroupAssociateAction(JSONController):

    @auth_required(authorization.EXECUTE)
    def POST(self, repo_group_id):
        criteria = Criteria.from_client_input(self.params().get('criteria', {}))
        manager = managers_factory.repo_group_manager()
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id),
                action_tag('repo_group_associate')]
        call_request = CallRequest(manager.associate,
                                   [repo_group_id, criteria],
                                   tags=tags)
        call_request.updates_resource(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id)
        execution.execute(call_request)
        collection = RepoGroup.get_collection()
        group = collection.find_one({'id': repo_group_id})
        return self.ok(group['repo_ids'])


class RepoGroupUnassociateAction(JSONController):

    @auth_required(authorization.EXECUTE)
    def POST(self, repo_group_id):
        criteria = Criteria.from_client_input(self.params().get('criteria', {}))
        manager = managers_factory.repo_group_manager()
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id),
                action_tag('repo_group_unassociate')]
        call_request = CallRequest(manager.unassociate,
                                   [repo_group_id, criteria],
                                   tags=tags)
        call_request.updates_resource(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id)
        execution.execute(call_request)
        collection = RepoGroup.get_collection()
        group = collection.find_one({'id': repo_group_id})
        return self.ok(group['repo_ids'])

# distributor controllers -----------------------------------------------------

class RepoGroupDistributors(JSONController):

    # Scope: Sub-collection
    # GET:   List Distributors
    # POST:  Add Distributor

    @auth_required(authorization.READ)
    def GET(self, repo_group_id):
        distributor_manager = managers_factory.repo_group_distributor_manager()

        distributor_list = distributor_manager.find_distributors(repo_group_id)
        for d in distributor_list:
            href = serialization.link.link_obj(d['id'])
            d.update(href)

        return self.ok(distributor_list)

    @auth_required(authorization.CREATE)
    def POST(self, repo_group_id):
        # Params (validation will occur in the manager)
        params = self.params()
        distributor_type_id = params.get('distributor_type_id', None)
        distributor_config = params.get('distributor_config', None)
        distributor_id = params.get('distributor_id', None)

        distributor_manager = managers_factory.repo_group_distributor_manager()

        resources = {dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE : {
            repo_group_id : dispatch_constants.RESOURCE_UPDATE_OPERATION
        }}
        weight = pulp_config.config.getint('tasks', 'create_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id),
                action_tag('add_distributor')]
        if distributor_id is not None:
            tags.append(resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_DISTRIBUTOR_TYPE, distributor_id))

        call_request = CallRequest(distributor_manager.add_distributor,
                                   [repo_group_id, distributor_type_id, distributor_config, distributor_id],
                                   resources=resources,
                                   weight=weight,
                                   tags=tags)
        created = execution.execute(call_request)

        href = serialization.link.child_link_obj(created['id'])
        created.update(href)

        return self.created(href['_href'], created)

class RepoGroupDistributor(JSONController):

    # Scope:  Exclusive Sub-resource
    # GET:    Get Distributor
    # DELETE: Remove Distributor
    # PUT:    Update Distributor Config

    @auth_required(authorization.READ)
    def GET(self, repo_group_id, distributor_id):
        distributor_manager = managers_factory.repo_group_distributor_manager()
        dist = distributor_manager.get_distributor(repo_group_id, distributor_id)

        href = serialization.link.current_link_obj()
        dist.update(href)

        return self.ok(dist)

    @auth_required(authorization.DELETE)
    def DELETE(self, repo_group_id, distributor_id):
        params = self.params()
        force = params.get('force', False)

        distributor_manager = managers_factory.repo_group_distributor_manager()

        resources = {
            dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE :
                    {repo_group_id : dispatch_constants.RESOURCE_UPDATE_OPERATION},
            dispatch_constants.RESOURCE_REPOSITORY_GROUP_DISTRIBUTOR_TYPE :
                    {distributor_id : dispatch_constants.RESOURCE_DELETE_OPERATION},
                     }
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_DISTRIBUTOR_TYPE, distributor_id),
                action_tag('remove_distributor')
               ]
        call_request = CallRequest(distributor_manager.remove_distributor,
                                   args=[repo_group_id, distributor_id],
                                   kwargs={'force' : force},
                                   resources=resources,
                                   tags=tags,
                                   archive=True)

        execution.execute(call_request)
        return self.ok(None)

    @auth_required(authorization.UPDATE)
    def PUT(self, repo_group_id, distributor_id):
        params = self.params()

        distributor_config = params.get('distributor_config', None)

        if distributor_config is None:
            raise pulp_exceptions.MissingValue(['distributor_config'])

        distributor_manager = managers_factory.repo_group_distributor_manager()

        resources = {
            dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE :
                    {repo_group_id : dispatch_constants.RESOURCE_UPDATE_OPERATION},
            dispatch_constants.RESOURCE_REPOSITORY_GROUP_DISTRIBUTOR_TYPE :
                    {distributor_id : dispatch_constants.RESOURCE_UPDATE_OPERATION},
            }
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_DISTRIBUTOR_TYPE, distributor_id),
                action_tag('update_distributor')
        ]

        call_request = CallRequest(distributor_manager.update_distributor_config,
                                   args=[repo_group_id, distributor_id, distributor_config],
                                   resources=resources,
                                   tags=tags,
                                   archive=True)

        result = execution.execute(call_request)

        href = serialization.link.current_link_obj()
        result.update(href)

        return self.ok(result)

# publish ---------------------------------------------------------------------

class PublishAction(JSONController):

    # Scope: Action
    # POST: Trigger a group publish

    def POST(self, repo_group_id):
        params = self.params()
        distributor_id = params.get('id', None)
        overrides = params.get('override_config', None)

        if distributor_id is None:
            raise MissingValue(['id'])

        publish_manager = managers_factory.repo_group_publish_manager()

        resources = {
            dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE :
                    {repo_group_id : dispatch_constants.RESOURCE_UPDATE_OPERATION},
            dispatch_constants.RESOURCE_REPOSITORY_GROUP_DISTRIBUTOR_TYPE :
                    {distributor_id : dispatch_constants.RESOURCE_UPDATE_OPERATION},
            }
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_DISTRIBUTOR_TYPE, distributor_id),
                action_tag('publish')
        ]
        weight = pulp_config.config.getint('tasks', 'publish_weight')

        call_request = CallRequest(publish_manager.publish,
                                   args=[repo_group_id, distributor_id],
                                   kwargs={'publish_config_override' : overrides},
                                   resources=resources,
                                   tags=tags,
                                   weight=weight,
                                   archive=True)

        return execution.execute_async(self, call_request)

# web.py application -----------------------------------------------------------

_URLS = ('/$', RepoGroupCollection,
         '/search/$', RepoGroupSearch, # resource search
         '/([^/]+)/$', RepoGroupResource,

         '/([^/]+)/distributors/$', RepoGroupDistributors,
         '/([^/]+)/distributors/([^/]+)/$', RepoGroupDistributor,

         '/([^/]+)/actions/associate/$', RepoGroupAssociateAction,
         '/([^/]+)/actions/unassociate/$', RepoGroupUnassociateAction,
         '/([^/]+)/actions/publish/$', PublishAction,
        )

application = web.application(_URLS, globals())
