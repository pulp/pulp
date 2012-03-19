# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
import logging

# 3rd Party
import web

# Pulp
import pulp.server.exceptions as exceptions
import pulp.server.managers.repo._exceptions as repo_exceptions
import pulp.server.managers.factory as manager_factory
from pulp.server.auth.authorization import CREATE, READ, DELETE, EXECUTE, UPDATE
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.managers.repo.unit_association_query import Criteria
from pulp.server.webservices import execution
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.queries.repo import unit_association_criteria
from pulp.server.webservices.serialization.error import http_error_obj

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- repo controllers ---------------------------------------------------------

class RepoCollection(JSONController):

    # Scope: Collection
    # GET:   Retrieve all repositories in the system
    # POST:  Repository Create

    @auth_required(READ)
    def GET(self):
        repo_query_manager = manager_factory.repo_query_manager()
        all_repos = repo_query_manager.find_all()

        # Load the importer/distributor information into each repository
        importer_manager = manager_factory.repo_importer_manager()
        distributor_manager = manager_factory.repo_distributor_manager()
        unit_query_manager = manager_factory.repo_unit_association_query_manager()

        for r in all_repos:
            importers = importer_manager.get_importers(r['id'])
            r['importers'] = importers

            distributors = distributor_manager.get_distributors(r['id'])
            r['distributors'] = distributors

            criteria = Criteria(unit_fields=[], association_fields=[], remove_duplicates=True)
            units = unit_query_manager.get_units_across_types(r['id'], criteria)
            r['content_unit_count'] = len(units)

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

        # Creation
        repo_manager = manager_factory.repo_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {id: dispatch_constants.RESOURCE_CREATE_OPERATION}}
        call_request = CallRequest(repo_manager.create_repo,
                                   [id, display_name, description, notes],
                                   resources=resources,
                                   weight=0,
                                   archive=True)
        return execution.execute_sync(self, call_request, expected_response='created')


class RepoResource(JSONController):

    # Scope:   Resource
    # GET:     Repository Retrieval
    # DELETE:  Repository Delete
    # PUT:     Repository Update

    @auth_required(READ)
    def GET(self, id):
        query_manager = manager_factory.repo_query_manager()

        repo = query_manager.find_by_id(id)

        if repo is None:
            raise exceptions.MissingResource(id)

        # Load the importer/distributor information into the repository
        importer_manager = manager_factory.repo_importer_manager()
        distributor_manager = manager_factory.repo_distributor_manager()

        importers = importer_manager.get_importers(id)
        repo['importers'] = importers

        distributors = distributor_manager.get_distributors(id)
        repo['distributors'] = distributors

        # Load the unit count into the repo
        unit_query_manager = manager_factory.repo_unit_association_query_manager()
        criteria = Criteria(unit_fields=[], association_fields=[], remove_duplicates=True)
        units = unit_query_manager.get_units_across_types(id, criteria)
        repo['content_unit_count'] = len(units)

        return self.ok(repo)

    @auth_required(DELETE)
    def DELETE(self, id):
        repo_manager = manager_factory.repo_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {id: dispatch_constants.RESOURCE_DELETE_OPERATION}}
        call_request = CallRequest(repo_manager.delete_repo,
                                   [id],
                                   resources=resources,
                                   archive=True)
        return execution.execute(self, call_request)

    @auth_required(UPDATE)
    def PUT(self, id):
        parameters = self.params()
        delta = parameters.get('delta', None)

        if delta is None:
            _LOG.exception('Missing delta when updating repository [%s]' % id)
            raise exceptions.MissingData('delta')

        repo_manager = manager_factory.repo_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        call_request = CallRequest(repo_manager.update_repo,
                                   [id, delta],
                                   resources=resources,
                                   archive=True)
        return execution.execute(self, call_request)

# -- importer controllers -----------------------------------------------------

class RepoImporters(JSONController):

    # Scope:  Sub-collection
    # GET:    List Importers
    # POST:   Set Importer

    @auth_required(READ)
    def GET(self, repo_id):
        importer_manager = manager_factory.repo_importer_manager()

        importers = importer_manager.get_importers(repo_id)
        # TODO: serialize properly
        return self.ok(importers)

    @auth_required(CREATE)
    def POST(self, repo_id):

        # Params (validation will occur in the manager)
        params = self.params()
        importer_type = params.get('importer_type_id', None)
        importer_config = params.get('importer_config', None)

        if importer_type is None:
            _LOG.exception('Missing importer type adding importer to repository [%s]' % repo_id)
            raise exceptions.MissingData('importer_type')

        # Note: If an importer exists, it's removed, so no need to handle 409s.
        # Note: If the plugin raises an exception during initialization, let it
        #  bubble up and be handled like any other 500.

        importer_manager = manager_factory.repo_importer_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_READ_OPERATION}}
        call_request = CallRequest(importer_manager.set_importer,
                                   [repo_id, importer_type, importer_config],
                                   resources=resources,
                                   archive=True)
        return execution.execute(self, call_request, expected_response='created')


class RepoImporter(JSONController):

    # Scope:  Exclusive Sub-resource
    # GET:    Get Importer
    # DELETE: Remove Importer
    # PUT:    Update Importer Config

    @auth_required(READ)
    def GET(self, repo_id, importer_id):

        importer_manager = manager_factory.repo_importer_manager()

        importer = importer_manager.get_importer(repo_id)
        # TODO: serialize properly
        return self.ok(importer)

    @auth_required(UPDATE)
    def DELETE(self, repo_id, importer_id):

        importer_manager = manager_factory.repo_importer_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE: {importer_id: dispatch_constants.RESOURCE_DELETE_OPERATION}}
        call_request = CallRequest(importer_manager.remove_importer,
                                   [repo_id],
                                   resources=resources,
                                   archive=True)
        return execution.execute(self, call_request)

    @auth_required(UPDATE)
    def PUT(self, repo_id, importer_id):

        # Params (validation will occur in the manager)
        params = self.params()
        importer_config = params.get('importer_config', None)

        if importer_config is None:
            _LOG.exception('Missing configuration updating importer for repository [%s]' % repo_id)
            raise exceptions.MissingData('importer_config')

        importer_manager = manager_factory.repo_importer_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE: {importer_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        call_request = CallRequest(importer_manager.update_importer_config,
                                   [repo_id, importer_config],
                                   resources=resources,
                                   archive=True)
        return execution.execute(self, call_request)

# -- distributor controllers --------------------------------------------------

class RepoDistributors(JSONController):

    # Scope:  Sub-collection
    # GET:    List Distributors
    # POST:   Add Distributor

    @auth_required(READ)
    def GET(self, repo_id):
        distributor_manager = manager_factory.repo_distributor_manager()

        distributor_list = distributor_manager.get_distributors(repo_id)
        # TODO: serialize each distributor before returning
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

        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE: {distributor_id: dispatch_constants.RESOURCE_CREATE_OPERATION}}
        call_request = CallRequest(distributor_manager.add_distributor,
                                   [repo_id, distributor_type, distributor_config, auto_publish, distributor_id],
                                   resources=resources,
                                   archive=True)
        return execution.execute(self, call_request, expected_response='created')


class RepoDistributor(JSONController):

    # Scope:  Exclusive Sub-resource
    # GET:    Get Distributor
    # DELETE: Remove Distributor
    # PUT:    Update Distributor Config

    @auth_required(READ)
    def GET(self, repo_id, distributor_id):
        distributor_manager = manager_factory.repo_distributor_manager()

        distributor = distributor_manager.get_distributor(repo_id, distributor_id)
        # TODO: serialize properly
        return self.ok(distributor)

    @auth_required(UPDATE)
    def DELETE(self, repo_id, distributor_id):
        distributor_manager = manager_factory.repo_distributor_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE: {distributor_id: dispatch_constants.RESOURCE_DELETE_OPERATION}}
        call_request = CallRequest(distributor_manager.remove_distributor,
                                   [repo_id, distributor_id],
                                   resources=resources,
                                   archive=True)
        return execution.execute(self, call_request)

    @auth_required(UPDATE)
    def PUT(self, repo_id, distributor_id):

        # Params (validation will occur in the manager)
        params = self.params()
        distributor_config = params.get('distributor_config', None)

        if distributor_config is None:
            _LOG.exception('Missing configuration when updating distributor [%s] on repository [%s]' % (distributor_id, repo_id))
            raise exceptions.MissingData('distributor_config')

        distributor_manager = manager_factory.repo_distributor_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_READ_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE: {distributor_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        call_request = CallRequest(distributor_manager.update_distributor_config,
                                   [repo_id, distributor_id, distributor_config],
                                   resources=resources,
                                   archive=True)
        return execution.execute(self, call_request)

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
                raise exceptions.InvalidValue(limit[0])

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
                raise exceptions.InvalidValue(limit[0])

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
        call_request = CallRequest(repo_sync_manager.sync,
                                   [repo_id, overrides],
                                   resources=resources,
                                   weight=2, # needs to be configurable!
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
        call_request = CallRequest(repo_publish_manager.publish,
                                   [repo_id, distributor_id, overrides],
                                   resources=resources,
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
            raise exceptions.MissingData('source_repo_id')

        criteria = params.get('criteria', None)
        if criteria is not None:
            try:
                criteria = unit_association_criteria(criteria)
            except:
                _LOG.exception('Error parsing association criteria [%s]' % criteria)
                raise

        # This should probably handle the exceptions and convert them to HTTP
        # status codes, but I'm still unsure of how we're going to handle these
        # in the async world, so for now a 500 is fine.

        association_manager = manager_factory.repo_unit_association_manager()
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {source_repo_id: dispatch_constants.RESOURCE_READ_OPERATION,
                                                                   dest_repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        call_request = CallRequest(association_manager.associate_from_repo,
                                   [source_repo_id, dest_repo_id],
                                   {'criteria': criteria},
                                   resources=resources,
                                   archive=True)
        return execution.execute_async(self, call_request)


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
            serialized = http_error_obj(404)
            return self.not_found(serialized)

        if query is None:
            raise exceptions.MissingData('query')

        try:
            criteria = unit_association_criteria(query)
        except:
            _LOG.exception('Error parsing association criteria [%s]' % query)
            raise

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
    '/([^/]+)/$', 'RepoResource', # resourcce

    '/([^/]+)/importers/$', 'RepoImporters', # sub-collection
    '/([^/]+)/importers/([^/]+)/$', 'RepoImporter', # exclusive sub-resource

    '/([^/]+)/distributors/$', 'RepoDistributors', # sub-collection
    '/([^/]+)/distributors/([^/]+)/$', 'RepoDistributor', # exclusive sub-resource

    '/([^/]+)/history/sync/$', 'RepoSyncHistory', # sub-collection
    '/([^/]+)/history/publish/([^/]+)/$', 'RepoPublishHistory', # sub-collection

    '/([^/]+)/actions/sync/$', 'RepoSync', # resource action
    '/([^/]+)/actions/publish/$', 'RepoPublish', # resource action
    '/([^/]+)/actions/associate/$', 'RepoAssociate', # resource action

    '/([^/]+)/search/units/$', 'RepoUnitAdvancedSearch', # resource search
)

application = web.application(urls, globals())
