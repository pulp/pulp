# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Python
from datetime import timedelta
import logging
import sys
from gettext import gettext as _

# 3rd Party
import web

# Pulp
import pulp.server.exceptions as exceptions
import pulp.server.managers.factory as manager_factory
from pulp.common.tags import action_tag, resource_tag
from pulp.server import config as pulp_config
from pulp.server.auth.authorization import CREATE, READ, DELETE, EXECUTE, UPDATE
from pulp.server.db.model.repository import Repo
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.dispatch.call import CallRequest
from pulp.server.webservices import execution
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.controllers.search import SearchController
from pulp.server.webservices.serialization.unit_criteria import unit_association_criteria

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- functions ----------------------------------------------------------------

def _merge_related_objects(name, manager, repos):
    """
    Takes a list of Repo objects and adds their corresponding related objects
    in a list under the attribute given in 'name'. Uses the given manager to
    access the related objects by passing the list of IDs for the given repos.
    This is most commonly used for RepoImporter or RepoDistributor objects in
    lists under the 'importers' and 'distributors' attributes.

    @param name: name of the field, such as 'importers' or 'distributors'.
    @type  name: str

    @param manager: manager class for the object type. must implement a method
                    'find_by_repo_list' that takes a list of repo ids.

    @param repos: list of Repo instances that should have importers and
                  distributors added.
    @type  repos  list of Repo instances

    @return the same list that was passed in, just for convenience. The list
            itself is not modified- only its members are modified in-place.
    @rtype  list of Repo instances
    """
    repo_ids = tuple(repo['id'] for repo in repos)

    # make it cheap to access each repo by id
    repo_dict = dict((repo['id'], repo) for repo in repos)

    # guarantee that at least an empty list will be present
    for repo in repos:
        repo[name] = []

    for item in manager.find_by_repo_list(repo_ids):
        repo_dict[item['repo_id']][name].append(item)

    return repos


# -- repo controllers ---------------------------------------------------------
class RepoCollection(JSONController):

    # Scope: Collection
    # GET:   Retrieve all repositories in the system
    # POST:  Repository Create

    @staticmethod
    def _process_repos(repos, importers=False, distributors=False):
        """
        Apply standard processing to a collection of repositories being returned
        to a client.  Adds the object link and optionally adds related importers
        and distributors.

        @param repos: collection of repositories
        @type  repos: list, tuple

        @param importers:   iff True, adds related importers under the
                            attribute "importers".
        @type  importers:   bool

        @param distributors:    iff True, adds related distributors under the
                                attribute "distributors".
        @type  distributors:    bool

        @return the same list that was passed in, just for convenience. The list
                itself is not modified- only its members are modified in-place.
        @rtype  list of Repo instances
        """
        if importers:
            _merge_related_objects(
                'importers', manager_factory.repo_importer_manager(), repos)
        if distributors:
            _merge_related_objects(
                'distributors', manager_factory.repo_distributor_manager(), repos)

        for repo in repos:
            repo.update(serialization.link.child_link_obj(repo['id']))

        return repos

    @auth_required(READ)
    def GET(self):
        """
        Looks for query parameters 'importers' and 'distributors', and will add
        the corresponding fields to the each repository returned. Query
        parameter 'details' is equivalent to passing both 'importers' and
        'distributors'.
        """
        query_params = web.input()
        query_manager = manager_factory.repo_query_manager()
        all_repos = query_manager.find_all()

        if query_params.get('details', False):
            query_params['importers'] = True
            query_params['distributors'] = True

        self._process_repos(
            all_repos,
            query_params.get('importers', False),
            query_params.get('distributors', False)
        )

        # Return the repos or an empty list; either way it's a 200
        return self.ok(all_repos)

    @auth_required(CREATE)
    def POST(self):

        # Pull the repo data out of the request body (validation will occur
        # in the manager)
        repo_data = self.params()
        id = repo_data.get('id', None)
        display_name = repo_data.get('display_name', None)
        description = repo_data.get('description', None)
        notes = repo_data.get('notes', None)

        importer_type_id = repo_data.get('importer_type_id', None)
        importer_repo_plugin_config = repo_data.get('importer_config', None)

        distributors = repo_data.get('distributors', None)

        # Creation
        repo_manager = manager_factory.repo_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {id: dispatch_constants.RESOURCE_CREATE_OPERATION}}
        args = [id, display_name, description, notes, importer_type_id, importer_repo_plugin_config, distributors]
        weight = pulp_config.config.getint('tasks', 'create_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, id),
                action_tag('create')]

        call_request = CallRequest(repo_manager.create_and_configure_repo,
                                   args,
                                   resources=resources,
                                   weight=weight,
                                   tags=tags)
        repo = execution.execute_sync(call_request)
        repo.update(serialization.link.child_link_obj(id))
        return self.created(id, repo)


class RepoSearch(SearchController):
    def __init__(self):
        super(RepoSearch, self).__init__(
            manager_factory.repo_query_manager().find_by_criteria)

    @auth_required(READ)
    def GET(self):
        query_params = web.input()
        if query_params.pop('details', False):
            query_params['importers'] = True
            query_params['distributors'] = True
        items = self._get_query_results_from_get(
            ('details', 'importers', 'distributors'))

        RepoCollection._process_repos(
            items,
            query_params.pop('importers', False),
            query_params.pop('distributors', False)
        )
        return self.ok(items)

    @auth_required(READ)
    def POST(self):
        """
        Searches based on a Criteria object. Requires a posted parameter
        'criteria' which has a data structure that can be turned into a
        Criteria instance.

        @param criteria:    Required. data structure that can be turned into
                            an instance of the Criteria model.
        @type  criteria:    dict

        @param importers:   Optional. iff evaluates to True, will include
                            each repo's related importers on the 'importers'
                            attribute.
        @type  imports:     bool

        @param distributors:    Optional. iff evaluates to True, will include
                                each repo's related distributors on the
                                'importers' attribute.
        @type  distributors:    bool

        @return:    list of matching repositories
        @rtype:     list
        """
        items = self._get_query_results_from_post()

        RepoCollection._process_repos(
            items,
            self.params().get('importers', False),
            self.params().get('distributors', False)
        )
        return self.ok(items)


class RepoResource(JSONController):

    # Scope:   Resource
    # GET:     Repository Retrieval
    # DELETE:  Repository Delete
    # PUT:     Repository Update

    @auth_required(READ)
    def GET(self, id):
        """
        Looks for query parameters 'importers' and 'distributors', and will add
        the corresponding fields to the repository returned. Query parameter
        'details' is equivalent to passing both 'importers' and 'distributors'.
        """
        query_params = web.input()
        query_manager = manager_factory.repo_query_manager()
        repo = query_manager.find_by_id(id)

        if repo is None:
            raise exceptions.MissingResource(id)

        repo.update(serialization.link.current_link_obj())

        if query_params.get('details', False):
            query_params['importers'] = True
            query_params['distributors'] = True

        if query_params.get('importers', False):
            repo = _merge_related_objects('importers', manager_factory.repo_importer_manager(), (repo,))[0]
        if query_params.get('distributors', False):
            repo = _merge_related_objects('distributors', manager_factory.repo_distributor_manager(), (repo,))[0]

        return self.ok(repo)

    @auth_required(DELETE)
    def DELETE(self, id):
        repo_manager = manager_factory.repo_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {id: dispatch_constants.RESOURCE_DELETE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, id),
                action_tag('delete')]

        call_request = CallRequest(repo_manager.delete_repo,
                                   [id],
                                   resources=resources,
                                   tags=tags,
                                   archive=True)
        return execution.execute_ok(self, call_request)

    @auth_required(UPDATE)
    def PUT(self, id):
        parameters = self.params()
        delta = parameters.get('delta', None)
        importer_config = parameters.get('importer_config', None)
        distributor_configs = parameters.get('distributor_configs', None)

        repo_manager = manager_factory.repo_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, id),
                action_tag('update')]

        call_request = CallRequest(repo_manager.update_repo_and_plugins,
                                   [id, delta, importer_config, distributor_configs],
                                   resources=resources,
                                   tags=tags,
                                   archive=True)
        repo = execution.execute(call_request)
        repo.update(serialization.link.current_link_obj())
        return self.ok(repo)

# -- importer controllers -----------------------------------------------------

class RepoImporters(JSONController):

    # Scope:  Sub-collection
    # GET:    List Importers
    # POST:   Set Importer

    @auth_required(READ)
    def GET(self, repo_id):
        importer_manager = manager_factory.repo_importer_manager()

        importers = importer_manager.get_importers(repo_id)
        return self.ok(importers)

    @auth_required(CREATE)
    def POST(self, repo_id):

        # Params (validation will occur in the manager)
        params = self.params()
        importer_type = params.get('importer_type_id', None)
        importer_config = params.get('importer_config', None)

        if importer_type is None:
            _LOG.exception('Missing importer type adding importer to repository [%s]' % repo_id)
            raise exceptions.MissingValue(['importer_type'])

        # Note: If an importer exists, it's removed, so no need to handle 409s.
        # Note: If the plugin raises an exception during initialization, let it
        #  bubble up and be handled like any other 500.

        importer_manager = manager_factory.repo_importer_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        weight = pulp_config.config.getint('tasks', 'create_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                action_tag('add_importer')]

        call_request = CallRequest(importer_manager.set_importer,
                                   [repo_id, importer_type, importer_config],
                                   resources=resources,
                                   weight=weight,
                                   tags=tags)
        return execution.execute_sync_created(self, call_request, 'importer')


class RepoImporter(JSONController):

    # Scope:  Exclusive Sub-resource
    # GET:    Get Importer
    # DELETE: Remove Importer
    # PUT:    Update Importer Config

    @auth_required(READ)
    def GET(self, repo_id, importer_id):

        # importer_id is there to meet the REST requirement, so leave it there
        # despite it not being used in this method.

        importer_manager = manager_factory.repo_importer_manager()

        importer = importer_manager.get_importer(repo_id)
        return self.ok(importer)

    @auth_required(UPDATE)
    def DELETE(self, repo_id, importer_id):

        importer_manager = manager_factory.repo_importer_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE: {importer_id: dispatch_constants.RESOURCE_DELETE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE, importer_id),
                action_tag('delete_importer')]
        call_request = CallRequest(importer_manager.remove_importer,
                                   [repo_id],
                                   resources=resources,
                                   tags=tags,
                                   archive=True)
        return execution.execute_ok(self, call_request)

    @auth_required(UPDATE)
    def PUT(self, repo_id, importer_id):

        # Params (validation will occur in the manager)
        params = self.params()
        importer_config = params.get('importer_config', None)

        if importer_config is None:
            _LOG.exception('Missing configuration updating importer for repository [%s]' % repo_id)
            raise exceptions.MissingValue(['importer_config'])

        importer_manager = manager_factory.repo_importer_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE: {importer_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE, importer_id),
                action_tag('update_importer')]
        call_request = CallRequest(importer_manager.update_importer_config,
                                   [repo_id, importer_config],
                                   resources=resources,
                                   tags=tags,
                                   archive=True)
        return execution.execute_ok(self, call_request)


class SyncScheduleCollection(JSONController):

    # Scope: sub-sub-collection
    # GET:   list all scheduled syncs
    # POST:  create new scheduled sync

    @auth_required(READ)
    def GET(self, repo_id, importer_id):
        importer_manager = manager_factory.repo_importer_manager()
        importer = importer_manager.get_importer(repo_id)
        if importer_id != importer['id']:
            raise exceptions.MissingResource(importer=importer_id)
        scheduler = dispatch_factory.scheduler()
        schedule_objs = []
        for schedule_id in importer_manager.list_sync_schedules(repo_id):
            try:
                schedule = scheduler.get(schedule_id)
            except exceptions.MissingResource:
                msg = _('Repository %(r)s; Importer %(i)s: scheduled sync does not exist: %(s)s')
                _LOG.warn(msg % {'r': repo_id, 'i': importer_id, 's': schedule_id})
            else:
                obj = serialization.dispatch.scheduled_sync_obj(schedule)
                obj.update(serialization.link.child_link_obj(schedule_id))
                schedule_objs.append(obj)
        return self.ok(schedule_objs)

    @auth_required(CREATE)
    def POST(self, repo_id, importer_id):
        importer_manager = manager_factory.repo_importer_manager()
        importer = importer_manager.get_importer(repo_id)
        if importer_id != importer['id']:
            raise exceptions.MissingResource(importer=importer_id)

        schedule_options = self.params()
        sync_options = {'override_config': schedule_options.pop('override_config', {})}

        schedule_manager = manager_factory.schedule_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE: {importer_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        weight = pulp_config.config.getint('tasks', 'create_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE, importer_id),
                action_tag('create_sync_schedule')]
        call_request = CallRequest(schedule_manager.create_sync_schedule,
                                   [repo_id, importer_id, sync_options, schedule_options],
                                   resources=resources,
                                   weight=weight,
                                   tags=tags,
                                   archive=True)
        schedule_id = execution.execute_sync(call_request)

        scheduler = dispatch_factory.scheduler()
        schedule = scheduler.get(schedule_id)
        obj = serialization.dispatch.scheduled_sync_obj(schedule)
        obj.update(serialization.link.child_link_obj(schedule_id))
        return self.created(obj['_href'], obj)


class SyncScheduleResource(JSONController):

    # Scope:  exclusive sub-sub-resource
    # DELETE: remove a scheduled sync
    # GET:    get a representation of the scheduled sync
    # PUT:    change a scheduled sync

    @auth_required(DELETE)
    def DELETE(self, repo_id, importer_id, schedule_id):
        importer_manager = manager_factory.repo_importer_manager()
        schedule_list = importer_manager.list_sync_schedules(repo_id)
        if schedule_id not in schedule_list:
            raise exceptions.MissingResource(repo=repo_id, importer=importer_id, publish_schedule=schedule_id)

        schedule_manager = manager_factory.schedule_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE: {importer_id: dispatch_constants.RESOURCE_UPDATE_OPERATION},
                     dispatch_constants.RESOURCE_SCHEDULE_TYPE: {schedule_id: dispatch_constants.RESOURCE_DELETE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE, importer_id),
                resource_tag(dispatch_constants.RESOURCE_SCHEDULE_TYPE, schedule_id),
                action_tag('delete_sync_schedule')]
        call_request = CallRequest(schedule_manager.delete_sync_schedule,
                                   [repo_id, importer_id, schedule_id],
                                   resources=resources,
                                   tags=tags,
                                   archive=True)
        return execution.execute_ok(self, call_request)

    @auth_required(READ)
    def GET(self, repo_id, importer_id, schedule_id):
        importer_manager = manager_factory.repo_importer_manager()
        schedule_list = importer_manager.list_sync_schedules(repo_id)
        if schedule_id not in schedule_list:
            raise exceptions.MissingResource(repo=repo_id, importer=importer_id, publish_schedule=schedule_id)
        scheduler = dispatch_factory.scheduler()
        schedule = scheduler.get(schedule_id)
        obj = serialization.dispatch.scheduled_sync_obj(schedule)
        obj.update(serialization.link.current_link_obj())
        return self.ok(obj)

    @auth_required(UPDATE)
    def PUT(self, repo_id, importer_id, schedule_id):
        importer_manager = manager_factory.repo_importer_manager()
        schedule_list = importer_manager.list_sync_schedules(repo_id)
        if schedule_id not in schedule_list:
            raise exceptions.MissingResource(repo=repo_id, importer=importer_id, publish_schedule=schedule_id)

        sync_updates = {}
        schedule_updates = self.params()
        if 'override_config' in schedule_updates:
            sync_updates['override_config'] = schedule_updates.pop('override_config')

        schedule_manager = manager_factory.schedule_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE: {importer_id: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_SCHEDULE_TYPE: {schedule_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE, importer_id),
                resource_tag(dispatch_constants.RESOURCE_SCHEDULE_TYPE, schedule_id),
                action_tag('update_sync_schedule')]
        call_request = CallRequest(schedule_manager.update_sync_schedule,
                                   [repo_id, importer_id, schedule_id, sync_updates, schedule_updates],
                                   resources=resources,
                                   tags=tags,
                                   archive=True)
        execution.execute(call_request)

        scheduler = dispatch_factory.scheduler()
        schedule = scheduler.get(schedule_id)
        obj = serialization.dispatch.scheduled_sync_obj(schedule)
        obj.update(serialization.link.current_link_obj())
        return self.ok(obj)

# -- distributor controllers --------------------------------------------------

class RepoDistributors(JSONController):

    # Scope:  Sub-collection
    # GET:    List Distributors
    # POST:   Add Distributor

    @auth_required(READ)
    def GET(self, repo_id):
        distributor_manager = manager_factory.repo_distributor_manager()

        distributor_list = distributor_manager.get_distributors(repo_id)
        return self.ok(distributor_list)

    @auth_required(CREATE)
    def POST(self, repo_id):

        # Distributor ID is optional and thus isn't part of the URL

        # Params (validation will occur in the manager)
        params = self.params()
        distributor_type = params.get('distributor_type_id', None)
        distributor_config = params.get('distributor_config', None)
        distributor_id = params.get('distributor_id', None)
        auto_publish = params.get('auto_publish', False)

        # Update the repo
        distributor_manager = manager_factory.repo_distributor_manager()

        # Note: The manager will automatically replace a distributor with the
        # same ID, so there is no need to return a 409.

        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        weight = pulp_config.config.getint('tasks', 'create_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                action_tag('add_distributor')]
        if distributor_id is not None:
            resources.update({dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE: {distributor_id: dispatch_constants.RESOURCE_CREATE_OPERATION}})
            tags.append(distributor_id)
        call_request = CallRequest(distributor_manager.add_distributor,
                                   [repo_id, distributor_type, distributor_config, auto_publish, distributor_id],
                                   resources=resources,
                                   weight=weight,
                                   tags=tags)
        return execution.execute_sync_created(self, call_request, distributor_id)


class RepoDistributor(JSONController):

    # Scope:  Exclusive Sub-resource
    # GET:    Get Distributor
    # DELETE: Remove Distributor
    # PUT:    Update Distributor Config

    @auth_required(READ)
    def GET(self, repo_id, distributor_id):
        distributor_manager = manager_factory.repo_distributor_manager()

        distributor = distributor_manager.get_distributor(repo_id, distributor_id)
        return self.ok(distributor)

    @auth_required(UPDATE)
    def DELETE(self, repo_id, distributor_id):
        distributor_manager = manager_factory.repo_distributor_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE: {distributor_id: dispatch_constants.RESOURCE_DELETE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
                action_tag('remove_distributor')]
        call_request = CallRequest(distributor_manager.remove_distributor,
                                   [repo_id, distributor_id],
                                   resources=resources,
                                   tags=tags,
                                   archive=True)
        return execution.execute_ok(self, call_request)

    @auth_required(UPDATE)
    def PUT(self, repo_id, distributor_id):

        # Params (validation will occur in the manager)
        params = self.params()
        distributor_config = params.get('distributor_config', None)

        if distributor_config is None:
            _LOG.exception('Missing configuration when updating distributor [%s] on repository [%s]' % (distributor_id, repo_id))
            raise exceptions.MissingValue(['distributor_config'])

        distributor_manager = manager_factory.repo_distributor_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE: {distributor_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
                action_tag('update_distributor')]
        call_request = CallRequest(distributor_manager.update_distributor_config,
                                   [repo_id, distributor_id, distributor_config],
                                   resources=resources,
                                   tags=tags,
                                   archive=True)
        return execution.execute_ok(self, call_request)


class PublishScheduleCollection(JSONController):

    # Scope: sub-sub-collection
    # GET:   list all scheduled publishes
    # POST:  create new scheduled publish

    @auth_required(READ)
    def GET(self, repo_id, distributor_id):
        scheduler = dispatch_factory.scheduler()
        distributor_manager = manager_factory.repo_distributor_manager()
        schedule_list = distributor_manager.list_publish_schedules(repo_id, distributor_id)
        schedule_objs = []
        for schedule_id in schedule_list:
            try:
                scheduled_call = scheduler.get(schedule_id)
            except exceptions.MissingResource:
                msg = _('Repository %(r)s; Distributor %(d)s: scheduled publish does not exist: %(s)s')
                _LOG.warn(msg % {'r': repo_id, 'd': distributor_id, 's': schedule_id})
            else:
                obj = serialization.dispatch.scheduled_publish_obj(scheduled_call)
                obj.update(serialization.link.child_link_obj(schedule_id))
                schedule_objs.append(obj)
        return self.ok(schedule_objs)

    @auth_required(CREATE)
    def POST(self, repo_id, distributor_id):
        distributor_manager = manager_factory.repo_distributor_manager()
        distributor_manager.get_distributor(repo_id, distributor_id)

        schedule_options = self.params()
        publish_options = {'override_config': schedule_options.pop('override_config', {})}

        schedule_manager = manager_factory.schedule_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE: {distributor_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        weight = pulp_config.config.getint('tasks', 'create_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
                action_tag('create_publish_schedule')]
        call_request = CallRequest(schedule_manager.create_publish_schedule,
                                   [repo_id, distributor_id, publish_options, schedule_options],
                                   resources=resources,
                                   weight=weight,
                                   tags=tags,
                                   archive=True)
        schedule_id = execution.execute_sync(call_request)

        scheduler = dispatch_factory.scheduler()
        schedule = scheduler.get(schedule_id)
        obj = serialization.dispatch.scheduled_publish_obj(schedule)
        obj.update(serialization.link.child_link_obj(schedule_id))
        return self.created(obj['_href'], obj)


class PublishScheduleResource(JSONController):

    # Scope:  exclusive sub-sub-resource
    # DELETE: remove a scheduled publish
    # GET:    get a representation of the scheduled publish
    # PUT:    change a scheduled publish

    @auth_required(DELETE)
    def DELETE(self, repo_id, distributor_id, schedule_id):
        distributor_manager = manager_factory.repo_distributor_manager()
        schedule_list = distributor_manager.list_publish_schedules(repo_id, distributor_id)
        if schedule_id not in schedule_list:
            raise exceptions.MissingResource(repo=repo_id, distributor=distributor_id, publish_schedule=schedule_id)

        schedule_manager = manager_factory.schedule_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE: {distributor_id: dispatch_constants.RESOURCE_UPDATE_OPERATION},
                     dispatch_constants.RESOURCE_SCHEDULE_TYPE: {schedule_id: dispatch_constants.RESOURCE_DELETE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
                resource_tag(dispatch_constants.RESOURCE_SCHEDULE_TYPE, schedule_id),
                action_tag('delete_publish_schedule')]
        call_request = CallRequest(schedule_manager.delete_publish_schedule,
                                   [repo_id, distributor_id, schedule_id],
                                   resources=resources,
                                   tags=tags,
                                   archive=True)
        return execution.execute_ok(self, call_request)

    @auth_required(READ)
    def GET(self, repo_id, distributor_id, schedule_id):
        distributor_manager = manager_factory.repo_distributor_manager()
        schedule_list = distributor_manager.list_publish_schedules(repo_id, distributor_id)
        if schedule_id not in schedule_list:
            raise exceptions.MissingResource(repo=repo_id, distributor=distributor_id, publish_schedule=schedule_id)

        scheduler = dispatch_factory.scheduler()
        schedule = scheduler.get(schedule_id)
        obj = serialization.dispatch.scheduled_publish_obj(schedule)
        obj.update(serialization.link.current_link_obj())
        return self.ok(obj)

    @auth_required(UPDATE)
    def PUT(self, repo_id, distributor_id, schedule_id):
        distributor_manager = manager_factory.repo_distributor_manager()
        schedule_list = distributor_manager.list_publish_schedules(repo_id, distributor_id)
        if schedule_id not in schedule_list:
            raise exceptions.MissingResource(repo=repo_id, distributor=distributor_id, publish_schedule=schedule_id)

        publish_update = {}
        schedule_update = self.params()
        if 'override_config' in schedule_update:
            publish_update['override_config'] = schedule_update.pop('override_config')

        schedule_manager = manager_factory.schedule_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE: {distributor_id: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_SCHEDULE_TYPE: {schedule_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
                resource_tag(dispatch_constants.RESOURCE_SCHEDULE_TYPE, schedule_id),
                action_tag('update_publish_schedule')]
        call_request = CallRequest(schedule_manager.update_publish_schedule,
                                   [repo_id, distributor_id, schedule_id, publish_update, schedule_update],
                                   resources=resources,
                                   tags=tags,
                                   archive=True)
        execution.execute(call_request)

        scheduler = dispatch_factory.scheduler()
        schedule = scheduler.get(schedule_id)
        obj = serialization.dispatch.scheduled_publish_obj(schedule)
        obj.update(serialization.link.current_link_obj())
        return self.ok(obj)

# -- history controllers ------------------------------------------------------

class RepoSyncHistory(JSONController):

    # Scope: Resource
    # GET:   Get history entries for the given repo

    @auth_required(READ)
    def GET(self, repo_id):
        # Params
        filters = self.filters(['limit'])
        limit = filters.get('limit', None)

        if limit is not None:
            try:
                limit = int(limit[0])
            except ValueError:
                _LOG.exception('Invalid limit specified [%s]' % limit)
                raise exceptions.InvalidValue(['limit'])

        sync_manager = manager_factory.repo_sync_manager()
        entries = sync_manager.sync_history(repo_id, limit=limit)
        return self.ok(entries)


class RepoPublishHistory(JSONController):

    # Scope: Resource
    # GET:   Get history entries for the given repo

    @auth_required(READ)
    def GET(self, repo_id, distributor_id):
        # Params
        filters = self.filters(['limit'])
        limit = filters.get('limit', None)

        if limit is not None:
            try:
                limit = int(limit[0])
            except ValueError:
                _LOG.exception('Invalid limit specified [%s]' % limit)
                raise exceptions.InvalidValue(['limit'])

        publish_manager = manager_factory.repo_publish_manager()
        entries = publish_manager.publish_history(repo_id, distributor_id, limit=limit)
        return self.ok(entries)

# -- action controllers -------------------------------------------------------

class RepoSync(JSONController):

    # Scope: Action
    # POST:  Trigger a repo sync

    @auth_required(EXECUTE)
    def POST(self, repo_id):

        # TODO: Add timeout support

        # Params
        params = self.params()
        overrides = params.get('override_config', None)

        # Execute the sync asynchronously
        repo_sync_manager = manager_factory.repo_sync_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        weight = pulp_config.config.getint('tasks', 'sync_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                action_tag('sync')]
        call_request = CallRequest(repo_sync_manager.sync,
                                   [repo_id],
                                   {'sync_config_override': overrides},
                                   resources=resources,
                                   weight=weight,
                                   tags=tags,
                                   archive=True)
        return execution.execute_async(self, call_request)


class RepoPublish(JSONController):

    # Scope: Action
    # POST:  Trigger a repo publish

    @auth_required(EXECUTE)
    def POST(self, repo_id):

        # TODO: Add timeout support

        # Params
        params = self.params()
        distributor_id = params.get('id', None)
        overrides = params.get('override_config', None)

        # Execute the publish asynchronously
        repo_publish_manager = manager_factory.repo_publish_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        weight = pulp_config.config.getint('tasks', 'publish_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                action_tag('publish')]
        call_request = CallRequest(repo_publish_manager.publish,
                                   [repo_id, distributor_id, overrides],
                                   resources=resources,
                                   weight=weight,
                                   tags=tags,
                                   archive=True)
        return execution.execute_async(self, call_request)


class RepoAssociate(JSONController):

    # Scope: Action
    # POST:  Associate units from a repository into the given repository

    @auth_required(UPDATE)
    def POST(self, dest_repo_id):

        # Params
        params = self.params()
        source_repo_id = params.get('source_repo_id', None)

        if source_repo_id is None:
            raise exceptions.MissingValue(['source_repo_id'])

        criteria = params.get('criteria', None)
        if criteria is not None:
            try:
                criteria = unit_association_criteria(criteria)
            except:
                _LOG.exception('Error parsing association criteria [%s]' % criteria)
                raise exceptions.PulpDataException(), None, sys.exc_info()[2]

        association_manager = manager_factory.repo_unit_association_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {source_repo_id: dispatch_constants.RESOURCE_READ_OPERATION,
                                                                   dest_repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, dest_repo_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, source_repo_id),
                action_tag('associate')]
        call_request = CallRequest(association_manager.associate_from_repo,
                                   [source_repo_id, dest_repo_id],
                                   {'criteria': criteria},
                                   resources=resources,
                                   tags=tags,
                                   archive=True)
        return execution.execute_async(self, call_request)

class RepoImportUpload(JSONController):

    @auth_required(UPDATE)
    def POST(self, repo_id):

        # Collect user input
        params = self.params()
        upload_id = params['upload_id']
        unit_type_id = params['unit_type_id']
        unit_key = params['unit_key']
        unit_metadata = params.pop('unit_metadata', None)

        # Coordinator configuration
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE:
                        {repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                action_tag('import_upload')]

        upload_manager = manager_factory.content_upload_manager()
        call_request = CallRequest(upload_manager.import_uploaded_unit,
            [repo_id, unit_type_id, unit_key, unit_metadata, upload_id],
            resources=resources, tags=tags, archive=True)

        return execution.execute_ok(self, call_request)

class RepoResolveDependencies(JSONController):

    # Scope: Actions
    # POST:  Resolve and return dependencies for one or more units

    def POST(self, repo_id):
        # Params
        params = self.params()
        query = params.get('criteria', {})
        options = params.get('options', {})
        timeout = params.get('timeout', 60)

        try:
            criteria = unit_association_criteria(query)
        except:
            _LOG.exception('Error parsing association criteria [%s]' % query)
            raise exceptions.PulpDataException(), None, sys.exc_info()[2]

        try:
            timeout = int(timeout)
        except ValueError:
            raise exceptions.InvalidValue(['timeout']), None, sys.exc_info()[2]

        # Coordinator configuration
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_READ_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                action_tag('resolve_dependencies')]

        dependency_manager = manager_factory.dependency_manager()
        call_request = CallRequest(dependency_manager.resolve_dependencies_by_criteria,
                                   [repo_id, criteria, options],
                                   resources=resources, tags=tags, archive=True)

        return execution.execute_sync_ok(self, call_request, timeout=timedelta(seconds=timeout))

class RepoUnitAdvancedSearch(JSONController):

    # Scope: Search
    # POST:  Advanced search for repo unit associations

    @auth_required(READ)
    def POST(self, repo_id):
        # Params
        params = self.params()
        query = params.get('query', None)

        repo_query_manager = manager_factory.repo_query_manager()
        repo = repo_query_manager.find_by_id(repo_id)
        if repo is None:
            raise exceptions.MissingResource(repo_id=repo_id)

        if query is None:
            raise exceptions.MissingValue(['query'])

        try:
            criteria = unit_association_criteria(query)
        except:
            _LOG.exception('Error parsing association criteria [%s]' % query)
            raise exceptions.PulpDataException(), None, sys.exc_info()[2]

        # Data lookup
        manager = manager_factory.repo_unit_association_query_manager()
        if criteria.type_ids is not None and len(criteria.type_ids) == 1:
            type_id = criteria.type_ids[0]
            units = manager.get_units_by_type(repo_id, type_id, criteria=criteria)
        else:
            units = manager.get_units_across_types(repo_id, criteria=criteria)

        return self.ok(units)

# -- web.py application -------------------------------------------------------

# These are defined under /v2/repositories/ (see application.py to double-check)
urls = (
    '/', 'RepoCollection', # collection
    '/search/$', 'RepoSearch', # resource search
    '/([^/]+)/$', 'RepoResource', # resource

    '/([^/]+)/importers/$', 'RepoImporters', # sub-collection
    '/([^/]+)/importers/([^/]+)/$', 'RepoImporter', # exclusive sub-resource
    '/([^/]+)/importers/([^/]+)/sync_schedules/$', 'SyncScheduleCollection',
    '/([^/]+)/importers/([^/]+)/sync_schedules/([^/]+)/$', 'SyncScheduleResource',

    '/([^/]+)/distributors/$', 'RepoDistributors', # sub-collection
    '/([^/]+)/distributors/([^/]+)/$', 'RepoDistributor', # exclusive sub-resource
    '/([^/]+)/distributors/([^/]+)/publish_schedules/$', 'PublishScheduleCollection',
    '/([^/]+)/distributors/([^/]+)/publish_schedules/([^/]+)/$', 'PublishScheduleResource',

    '/([^/]+)/history/sync/$', 'RepoSyncHistory', # sub-collection
    '/([^/]+)/history/publish/([^/]+)/$', 'RepoPublishHistory', # sub-collection

    '/([^/]+)/actions/sync/$', 'RepoSync', # resource action
    '/([^/]+)/actions/publish/$', 'RepoPublish', # resource action
    '/([^/]+)/actions/associate/$', 'RepoAssociate', # resource action
    '/([^/]+)/actions/import_upload/$', 'RepoImportUpload', # resource action
    '/([^/]+)/actions/resolve_dependencies/$', 'RepoResolveDependencies', # resource action

    '/([^/]+)/search/units/$', 'RepoUnitAdvancedSearch', # resource search
)

application = web.application(urls, globals())
