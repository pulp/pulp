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
from pulp.server.db.model.repository import RepoGroup
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.managers import factory as managers_factory
from pulp.server.webservices import execution, serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required

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
                                   [repo_group_id, update_data],
                                   tags=tags)
        call_request.updates_resource(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id)
        group = execution.execute(call_request)
        group.update(serialization.link.current_link_obj())
        return self.ok(group)

# repo group actions -----------------------------------------------------------

class RepoGroupAssociateAction(JSONController):

    @auth_required(authorization.EXECUTE)
    def POST(self, repo_group_id):
        criteria = Criteria.from_json_doc(self.params())
        manager = managers_factory.repo_group_manager()
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id),
                action_tag('repo_group_associate')]
        call_request = CallRequest(manager.associate,
                                   [repo_group_id, criteria],
                                   tags=tags)
        call_request.updates_resource(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id)
        group = execution.execute(call_request)
        return self.ok(group['repo_ids'])


class RepoGroupUnassociateAction(JSONController):

    @auth_required(authorization.EXECUTE)
    def POST(self, repo_group_id):
        criteria = Criteria.from_json_doc(self.params())
        manager = managers_factory.repo_group_manager()
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id),
                action_tag('repo_group_unassociate')]
        call_request = CallRequest(manager.unassociate,
                                   [repo_group_id, criteria],
                                   tags=tags)
        call_request.updates_resource(dispatch_constants.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id)
        group = execution.execute(call_request)
        return self.ok(group['repo_ids'])

# web.py application -----------------------------------------------------------

_URLS = ('/$', RepoGroupCollection,
         '/([!/]+)/$', RepoGroupResource,
         '/([!/]+)/actions/associate/$', RepoGroupAssociateAction,
         '/([!/]+)/actions/unassociate/$', RepoGroupUnassociateAction)

application = web.application(_URLS, globals())
