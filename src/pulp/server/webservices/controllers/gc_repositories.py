#!/usr/bin/env python
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
from gettext import gettext as _

# 3rd Party
import web

# Pulp
from pulp.server.auth.authorization import CREATE, READ, DELETE, EXECUTE, UPDATE
import pulp.server.managers.factory as manager_factory
from pulp.server.managers.repo.cud import DuplicateRepoId, InvalidRepoId, InvalidRepoMetadata
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
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

        # TODO: clean up serialized repos for return

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

        try:
            repo = repo_manager.create_repo(id, display_name, description, notes)
        except DuplicateRepoId:
            serialized = http_error_obj(409)
            return self.conflict(serialized)
        except (InvalidRepoId, InvalidRepoMetadata):
            serialized = http_error_obj(400)
            return self.bad_request(serialized)

        # TODO: explicitly serialize repo for return

        return self.ok(repo)

class RepoResource(JSONController):

    # Scope:   Resource
    # DELETE:  Repository Delete
    # PUT:     Repository Update

    @auth_required(DELETE)
    def DELETE(self, id):

        # Deletion
        repo_manager = manager_factory.repo_manager()
        repo_manager.delete_repo(id)

        return self.ok(True)

    @auth_required(UPDATE)
    def PUT(self, id):
        pass

# -- importer controllers -----------------------------------------------------

class RepoImporters(JSONController):

    # Scope:  Sub-collection
    # GET:    List Importers
    # POST:   Set Importer

    @auth_required(READ)
    def GET(self, repo_id):
        pass

    @auth_required(CREATE)
    def POST(self, repo_id):

        # Params (validation will occur in the manager)
        params = self.params()
        importer_type = params.get('importer_type_id', None)
        importer_config = params.get('importer_config', None)

        # Update the repo
        importer_manager = manager_factory.repo_importer_manager()
        importer_manager.set_importer(repo_id, importer_type, importer_config)

        return self.ok(True)

class RepoImporter(JSONController):

    # Scope:  Exclusive Sub-resource
    # DELETE: Remove Importer
    # PUT:    Update Importer Config

    @auth_required(UPDATE)
    def DELETE(self, repo_id, importer_id):
        pass

    @auth_required(UPDATE)
    def PUT(self, repo_id, importer_id):
        pass

# -- distributor controllers --------------------------------------------------

class RepoDistributors(JSONController):

    # Scope:  Sub-collection
    # GET:    List Distributors
    # POST:   Add Distributor

    @auth_required(READ)
    def GET(self, repo_id):
        pass
    
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
        distributor_manager.add_distributor(repo_id, distributor_type, distributor_config, auto_publish, distributor_id)

        return self.ok(True)

class RepoDistributor(JSONController):

    # Scope:  Exclusive Sub-resource
    # DELETE: Remove Distributor
    # PUT:    Update Distributor Config

    @auth_required(UPDATE)
    def DELETE(self, repo_id, distributor_id):
        distributor_manager = manager_factory.repo_distributor_manager()
        distributor_manager.remove_distributor(repo_id, distributor_id)

    @auth_required(UPDATE)
    def PUT(self, repo_id, distributor_id):
        pass

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

        # Trigger the sync
        # TODO: Make this run asynchronously
        repo_sync_manager = manager_factory.repo_sync_manager()
        repo_sync_manager.sync(repo_id, overrides)

        return self.ok(True)

class RepoPublish(JSONController):

    # Scope: Action
    # POST:  Trigger a repo publish

    @auth_required(EXECUTE)
    def POST(self, repo_id, distributor_id):

        # TODO: Add timeout support

        # Params
        params = self.params()
        overrides = params.get('override_config', None)

        # Trigger the publish
        # TODO: Make this run asynchronously
        repo_publish_manager = manager_factory.repo_publish_manager()
        repo_publish_manager.publish(repo_id, distributor_id, overrides)
        
        return self.ok(True)

# -- web.py application -------------------------------------------------------

# These are defined under /v2/repositories/ (see application.py to double-check)
urls = (
    '/', 'RepoCollection', # collection
    '/([^/]+)/$', 'RepoResource', # resourcce

    '/([^/]+)/importers/$', 'RepoImporters', # sub-collection
    '/([^/]+)/importers/([^/]+)/$', 'RepoImporter', # exclusive sub-resource

    '/([^/]+)/distributors/$', 'RepoDistributors', # sub-collection
    '/([^/]+)/distributors/([^/]+)/$', 'RepoDistributor', # exclusive sub-resource

    '/([^/]+)/actions/sync/$', 'RepoSync', # sub-resource action
    '/([^/]+)/actions/publish/([^/]+)/$', 'RepoPublish', # sub-resource action
)

application = web.application(urls, globals())
